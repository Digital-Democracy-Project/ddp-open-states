#!/usr/bin/env python3
"""
OPEN-622: move Utah's stored floor vote lines to the chamber that voted.

Utah's scraper stored each action under le.utah.gov's "owner", the office holding the bill next, so "House/ passed 3rd
reading" and "House/ concurs with Senate amendment" sat under the Senate (on the Mac replica, 2026-11-18: 930 of 1,260
passage lines, all 214 concurrence lines, 12 of 26 conference "Final Passage" lines). The scraper now stores a floor
vote line (passage, concurrence or its refusal, a failed vote, a conference report's final passage) under the chamber
its text names (`voting_chamber()` in openstates-scrapers `scrapers/ut/bills.py`; its passage pattern is core's
`ddp_states/ut.py` and the broker's `_read_utah`). This applies that rule to the stored history, so the broker's Utah
chamber correction can go (BROKER-490) and each roll call pairs with its own line. Only the action's organization
changes: never its text, labels, date or order. A bill whose action moves has its `updated_at` moved, as a re-import by
the fixed scraper would, so api-v3's `updated_since` readers see it: run it in Utah's silent window.

Dry run unless --commit. Every write is guarded: an action whose organization or text is no longer the one the change
was planned from (or that belongs to another bill) aborts the whole run with nothing written; a list that names an
organization other than Utah's House and Senate, or a chamber that does not match it, is refused. The list is the audit
record: it takes its name only after the commit, and an existing list is never overwritten.

Usage:
    python3 fix-ut-vote-chamber.py --list PLANNED                          # dry run: the change list
    python3 fix-ut-vote-chamber.py --commit --expect N --list COMMITTED    # write (aborts unless exactly N)
    python3 fix-ut-vote-chamber.py --apply-list REVIEWED --commit --expect N --list COMMITTED
    python3 fix-ut-vote-chamber.py --undo COMMITTED --commit --list UNDONE  # put every action back
"""
import argparse
import csv
import os
import sys

import psycopg2
import psycopg2.extras

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "openstates-scrapers", "scrapers"))

DATABASE_URL = os.getenv("DATABASE_URL")
DB_CONFIG = {
    "host": os.getenv("OPENSTATES_DB_HOST", "localhost"),
    "port": int(os.getenv("OPENSTATES_DB_PORT", "5433")),
    "dbname": os.getenv("OPENSTATES_DB_NAME", "openstates"),
    "user": os.getenv("OPENSTATES_DB_USER", "openstates"),
    "password": os.getenv("OPENSTATES_DB_PASSWORD", "openstates_dev"),
}

UT = "ocd-jurisdiction/country:us/state:ut/government"

FETCH_SQL = """
    SELECT a.id, a.bill_id, b.identifier AS bill, s.identifier AS session, a."order", a.date, a.description,
           a.organization_id, o.classification AS chamber
    FROM opencivicdata_billaction a
    JOIN opencivicdata_bill b ON b.id = a.bill_id
    JOIN opencivicdata_legislativesession s ON s.id = b.legislative_session_id
    JOIN opencivicdata_organization o ON o.id = a.organization_id
    WHERE s.jurisdiction_id = %s
    ORDER BY s.identifier, b.identifier, a."order", a.id
"""

CHAMBERS_SQL = """
    SELECT classification, array_agg(id) FROM opencivicdata_organization
    WHERE jurisdiction_id = %s AND classification IN ('upper', 'lower') GROUP BY classification
"""

# Guarded: matches only while the action still has the bill, organization and text the change was planned from.
UPDATE_SQL = """
    UPDATE opencivicdata_billaction SET organization_id = %s
    WHERE id = %s AND bill_id = %s AND organization_id = %s AND description = %s
"""

TOUCH_SQL = "UPDATE opencivicdata_bill SET updated_at = now() WHERE id = ANY(%s)"

LIST_COLUMNS = [
    "id", "bill_id", "bill", "session", "order", "date", "description", "old_chamber", "new_chamber", "old_org", "new_org",
]


def plan(rows, chamber_orgs):
    """Each stored floor vote line whose organization is not the chamber its text names, as a change-list row."""
    from ut.bills import voting_chamber  # the scraper's own rule (OPEN-622)

    changes = []
    for row in rows:
        voted = voting_chamber(row["description"])
        if voted is None or voted == row["chamber"]:
            continue
        changes.append(dict(
            id=row["id"], bill_id=row["bill_id"], bill=row["bill"], session=row["session"], order=row["order"],
            date=row["date"], description=row["description"], old_chamber=row["chamber"], new_chamber=voted,
            old_org=row["organization_id"], new_org=chamber_orgs[voted],
        ))
    return changes


def chamber_organizations(cur):
    """{"upper": id, "lower": id}: Utah's two chambers; refuses anything but exactly one of each."""
    cur.execute(CHAMBERS_SQL, (UT,))
    found = dict(cur.fetchall())
    if sorted(found) != ["lower", "upper"] or any(len(ids) != 1 for ids in found.values()):
        sys.exit(f"aborted, nothing written: expected one Utah upper and one lower organization, found {found}")
    return {chamber: ids[0] for chamber, ids in found.items()}


def check_list(changes, chamber_orgs):
    """Refuse a list (reviewed, or committed for --undo) that moves an action anywhere but between Utah's two chambers,
    or whose chamber names do not match its organizations."""
    for c in changes:
        for side in ("old", "new"):
            if chamber_orgs.get(c[f"{side}_chamber"]) != c[f"{side}_org"]:
                sys.exit(
                    f"aborted, nothing written: action {c['id']} has {side}_chamber {c[f'{side}_chamber']!r} and "
                    f"{side}_org {c[f'{side}_org']!r}, not one of Utah's chambers {chamber_orgs}"
                )


def read_list(path, undo):
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if set(LIST_COLUMNS) - set(reader.fieldnames or []):
        sys.exit(f"{path} is not a change list of this script; nothing written")
    if undo:
        for r in rows:
            r["old_org"], r["new_org"] = r["new_org"], r["old_org"]
            r["old_chamber"], r["new_chamber"] = r["new_chamber"], r["old_chamber"]
    return rows


def write(conn, changes, list_path):
    """Write every change or none: a guard miss rolls the whole run back."""
    with conn.cursor() as cur:
        updated = 0
        for c in changes:
            cur.execute(UPDATE_SQL, (c["new_org"], c["id"], c["bill_id"], c["old_org"], c["description"]))
            updated += cur.rowcount
        if updated != len(changes):
            conn.rollback()
            sys.exit(
                f"aborted, nothing written: {len(changes)} changes planned, {updated} actions still held the expected "
                "organization and text (an action changed underneath, or the list is stale)"
            )
        cur.execute(TOUCH_SQL, (sorted({c["bill_id"] for c in changes}),))
    if list_path:
        _write_list(f"{list_path}.partial", changes)
    conn.commit()
    if list_path:
        try:
            os.replace(f"{list_path}.partial", list_path)
        except OSError as e:
            sys.exit(
                f"COMMITTED ({len(changes)} actions), but the list could not take its name ({e}); it is complete at "
                f"{list_path}.partial (use it for --undo). Do not run again: the commit is done"
            )


def _write_list(path, rows):
    with open(path, "x", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LIST_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--commit", action="store_true", help="write (without it: a dry run)")
    parser.add_argument("--list", dest="list_path", help="write the changes (planned, or written) to this CSV")
    parser.add_argument("--apply-list", help="write exactly this reviewed list's changes")
    parser.add_argument("--undo", help="write this committed list's changes back")
    parser.add_argument("--expect", type=int, help="abort unless exactly this many actions change")
    args = parser.parse_args(argv)

    if args.apply_list and args.undo:
        parser.error("--apply-list and --undo are separate runs")
    if args.list_path and os.path.exists(args.list_path):
        parser.error(f"{args.list_path} already exists; an earlier list is never overwritten")

    conn = psycopg2.connect(DATABASE_URL) if DATABASE_URL else psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            orgs = chamber_organizations(cur)
        if args.apply_list or args.undo:
            changes = read_list(args.apply_list or args.undo, undo=bool(args.undo))
            check_list(changes, orgs)
            print(f"{len(changes):,} changes read from {args.apply_list or args.undo}" + (" (undo)" if args.undo else ""))
        else:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(FETCH_SQL, (UT,))
                rows = cur.fetchall()
            changes = plan(rows, orgs)
            print(f"{len(rows):,} Utah actions read")
        groups = {}
        for c in changes:
            key = (c["description"], c["old_chamber"], c["new_chamber"])
            groups[key] = groups.get(key, 0) + 1
        for (text, old, new), n in sorted(groups.items()):
            print(f"  {text!r}: {old} -> {new}: {n:,}")
        print(f"  on {len({c['bill_id'] for c in changes}):,} bills")
        if args.expect is not None and len(changes) != args.expect:
            conn.rollback()
            sys.exit(f"aborted, nothing written: {len(changes):,} changes, --expect {args.expect:,}")
        if not args.commit:
            conn.rollback()
            if args.list_path:
                _write_list(args.list_path, changes)
            print(f"Dry run: would move {len(changes):,} actions. Nothing written.")
        else:
            write(conn, changes, args.list_path)
            print(f"Done. Moved {len(changes):,} actions.")
        if args.list_path:
            print(f"  list: {args.list_path} ({len(changes):,} rows)")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
