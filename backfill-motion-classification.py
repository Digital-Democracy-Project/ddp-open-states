#!/usr/bin/env python3
"""
Backfill motion_classification for existing VoteEvent records.

Applies the same YAML-driven classify_motion() logic used by scrapers to all
existing records in the OpenStates DB so that votes scraped before the scraper
patches are also correctly classified.

Run once after the scraper patches are committed. Safe to re-run. Only rows whose
classification changes are written.

Arizona (OPEN-625): a roll call's motion text ("Passed", "failed to pass") does not say
which vote it was; the floor step it is filed under does (the az scraper's
vote_classification()). Stored votes do not keep that step, so Arizona is classified only
with --az-cache, the scrape cache holding Arizona's Bill pages (their FloorHeaders), and is
otherwise left as it is: re-applying the text rules alone would turn its Committee of the
Whole, amendment and reconsider roll calls back into passage votes. Arizona's empty 0-0 roll
calls (no voters, OPEN-433) are left as they are too (see classify_row).

A reviewed list is applied where that cache does not exist (production): --list writes the
changes (dry run or write), --apply-list writes exactly a list's changes, --undo writes a
list's changes back. Every write is guarded: a row whose stored classification is no longer
the list's "old" aborts the run with nothing written.

Usage:
    python3 backfill-motion-classification.py [--dry-run]
    python3 backfill-motion-classification.py --jurisdiction az --az-cache DIR --dry-run --list FILE
    python3 backfill-motion-classification.py --apply-list FILE --expect N --list COMMITTED
    python3 backfill-motion-classification.py --undo COMMITTED --list UNDONE
"""
import argparse
import csv
import json
import os
import re
import sys

import psycopg2
import psycopg2.extras

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "openstates-scrapers", "scrapers"))
from classify_motion import classify_motion  # noqa: E402

DATABASE_URL = os.getenv("DATABASE_URL")
DB_CONFIG = {
    "host": os.getenv("OPENSTATES_DB_HOST", "localhost"),
    "port": int(os.getenv("OPENSTATES_DB_PORT", "5433")),
    "dbname": os.getenv("OPENSTATES_DB_NAME", "openstates"),
    "user": os.getenv("OPENSTATES_DB_USER", "openstates"),
    "password": os.getenv("OPENSTATES_DB_PASSWORD", "openstates_dev"),
}

# Map OpenStates jurisdiction IDs to the short keys used by classify_motion.
# ocd-jurisdiction/country:us/government → us
# ocd-jurisdiction/country:us/state:az/government → az
JURISDICTION_MAP = {
    "ocd-jurisdiction/country:us/government": "us",
    "ocd-jurisdiction/country:us/state:az/government": "az",
    "ocd-jurisdiction/country:us/state:ut/government": "ut",
    "ocd-jurisdiction/country:us/state:fl/government": "fl",
    "ocd-jurisdiction/country:us/state:mi/government": "mi",
    "ocd-jurisdiction/country:us/state:ma/government": "ma",
    "ocd-jurisdiction/country:us/state:wa/government": "wa",
    "ocd-jurisdiction/country:us/state:va/government": "va",
}

FETCH_SQL = """
    SELECT
        ve.id,
        ve.motion_text,
        ve.motion_classification,
        ve.extras->>'bill_action' AS bill_action,
        j.id AS jurisdiction_id,
        b.identifier AS bill,
        ve.start_date,
        o.classification AS chamber,
        (SELECT min(url) FROM opencivicdata_votesource vs WHERE vs.vote_event_id = ve.id) AS source,
        (SELECT count(*) FROM opencivicdata_personvote pv WHERE pv.vote_event_id = ve.id) AS voters
    FROM opencivicdata_voteevent ve
    JOIN opencivicdata_legislativesession ls ON ls.id = ve.legislative_session_id
    JOIN opencivicdata_jurisdiction j ON j.id = ls.jurisdiction_id
    LEFT JOIN opencivicdata_bill b ON b.id = ve.bill_id
    JOIN opencivicdata_organization o ON o.id = ve.organization_id
    WHERE j.id = ANY(%s)
    ORDER BY j.id, ve.id
"""

# Guarded: matches only while the row still holds the classification the change was planned from.
UPDATE_SQL = """
    UPDATE opencivicdata_voteevent
    SET motion_classification = %s
    WHERE id = %s AND motion_classification = %s
"""

LIST_COLUMNS = ["id", "jurisdiction", "bill", "date", "chamber", "motion_text", "floor_step", "voters", "old", "new"]

_AZ_ACTION_ID = re.compile(r"billStatusActionId=(\d+)")


def az_floor_steps(cache_dir):
    """{BillStatusActionId: CommitteeShortName} from every Arizona Bill page in a scrapelib cache."""
    steps = {}
    for name in os.listdir(cache_dir):
        if not name.startswith("apps.azleg.gov,api,Bill,"):
            continue
        with open(os.path.join(cache_dir, name), "rb") as f:
            raw = f.read()
        start = raw.find(b"{")  # the cache file is the response's headers, then its body
        if start < 0:
            continue
        for header in json.loads(raw[start:]).get("FloorHeaders") or []:
            steps[header["BillStatusActionId"]] = header.get("CommitteeShortName")
    return steps


def classify_row(jur_key, row, az_steps):
    """(new classification, floor step); None when the row cannot be classified here."""
    if jur_key == "az":
        if az_steps is None:
            return None, None
        from az.bills import vote_classification  # the scraper's own rule (OPEN-625)

        if not row["voters"]:
            # An empty 0-0 roll call (OPEN-433; the scraper no longer emits them) is left as it is. The broker keeps
            # one Motion for same-day votes with the same text, so relabelling an empty "Passed" next to a real
            # third reading would take the real vote off scorecards (measured on 2026-11-17: 7 scorecard bills).
            return None, None
        found = _AZ_ACTION_ID.search(row["source"] or "")
        if not found or int(found.group(1)) not in az_steps:
            return None, None
        step = az_steps[int(found.group(1))]
        return vote_classification(step, row["motion_text"]), step
    return classify_motion(jur_key, row["motion_text"], bill_action=row["bill_action"]), ""


def plan(rows, az_steps):
    changes, unclassified = [], 0
    for row in rows:
        jur_key = JURISDICTION_MAP[row["jurisdiction_id"]]
        new, step = classify_row(jur_key, row, az_steps)
        if new is None:
            unclassified += 1
            continue
        old = list(row["motion_classification"] or [])
        if new != old:
            changes.append(dict(
                id=row["id"], jurisdiction=jur_key, bill=row["bill"], date=row["start_date"], chamber=row["chamber"],
                motion_text=row["motion_text"], floor_step=step, voters=row["voters"],
                old=",".join(old), new=",".join(new),
            ))
    return changes, unclassified


def read_list(path, undo):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    if undo:
        for r in rows:
            r["old"], r["new"] = r["new"], r["old"]
    return rows


def _labels(text):
    return [x for x in text.split(",") if x]


def write(conn, changes, list_path):
    """Write every change or none: a guard miss rolls the whole run back."""
    with conn.cursor() as cur:
        updated = 0
        for c in changes:
            cur.execute(UPDATE_SQL, (_labels(c["new"]), c["id"], _labels(c["old"])))
            updated += cur.rowcount
    if updated != len(changes):
        conn.rollback()
        sys.exit(
            f"aborted, nothing written: {len(changes)} changes planned, {updated} rows still held the expected "
            "classification (a row changed underneath, or the list is stale)"
        )
    if list_path:
        _write_list(f"{list_path}.partial", changes)
    conn.commit()
    if list_path:
        try:
            os.replace(f"{list_path}.partial", list_path)
        except OSError as e:
            sys.exit(
                f"COMMITTED ({len(changes)} rows), but the list could not take its name ({e}); it is complete at "
                f"{list_path}.partial (use it for --undo). Do not run again: the commit is done"
            )


def _write_list(path, rows):
    with open(path, "x", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LIST_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing")
    parser.add_argument("--jurisdiction", help="only this short key (az, us, ut, ...)")
    parser.add_argument("--az-cache", help="scrapelib cache with Arizona's Bill pages (classifies Arizona)")
    parser.add_argument("--list", dest="list_path", help="write the changes (planned, or written) to this CSV")
    parser.add_argument("--apply-list", help="write exactly this list's changes (no classifying)")
    parser.add_argument("--undo", help="write this list's changes back (new -> old)")
    parser.add_argument("--expect", type=int, help="abort unless exactly this many rows change")
    args = parser.parse_args(argv)

    if args.apply_list and args.undo:
        parser.error("--apply-list and --undo are separate runs")
    if args.jurisdiction and args.jurisdiction not in JURISDICTION_MAP.values():
        parser.error(f"unknown jurisdiction {args.jurisdiction!r}")
    if args.list_path and os.path.exists(args.list_path):
        parser.error(f"{args.list_path} already exists; an earlier list is never overwritten")

    conn = psycopg2.connect(DATABASE_URL) if DATABASE_URL else psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    try:
        if args.apply_list or args.undo:
            changes = read_list(args.apply_list or args.undo, undo=bool(args.undo))
            print(f"{len(changes):,} changes read from {args.apply_list or args.undo}" + (" (undo)" if args.undo else ""))
        else:
            ids = [j for j, k in JURISDICTION_MAP.items() if not args.jurisdiction or k == args.jurisdiction]
            az_steps = az_floor_steps(args.az_cache) if args.az_cache else None
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(FETCH_SQL, (ids,))
                rows = cur.fetchall()
            changes, unclassified = plan(rows, az_steps)
            print(f"Processing {len(rows):,} vote events across {len(ids)} jurisdictions...")
            if unclassified:
                print(f"  left as they are: {unclassified:,} (Arizona: no --az-cache, no voters, or no Bill page)")
        groups = {}
        for c in changes:
            key = (c["jurisdiction"], c["floor_step"], c["motion_text"], c["old"], c["new"])
            groups[key] = groups.get(key, 0) + 1
        for (jur, step, text, old, new), n in sorted(groups.items()):
            print(f"  {jur} {step or '-'} | {text!r:.40} | {old or '(none)'} -> {new or '(none)'}: {n:,}")
        if args.expect is not None and len(changes) != args.expect:
            conn.rollback()
            sys.exit(f"aborted, nothing written: {len(changes):,} changes, --expect {args.expect:,}")
        if args.dry_run:
            conn.rollback()
            if args.list_path:
                _write_list(args.list_path, changes)
            print(f"Dry run complete. Would update {len(changes):,} records.")
        else:
            write(conn, changes, args.list_path)
            print(f"Done. Updated {len(changes):,} records.")
        if args.list_path:
            print(f"  list: {args.list_path} ({len(changes):,} rows)")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
