#!/usr/bin/env python3
"""
Backfill the roll-call number (`house-rollcall-num` / `senate-rollcall-num`, or `legislature-rollcall-num` for
Nebraska, in a vote event's extras) on stored Washington, Michigan, Virginia and Arizona votes (OPEN-628), and
Nebraska, Louisiana and New Mexico votes (OPEN-685).

The broker reads that key into Motion.rollcall_num, and its scorecard builders order a bill's votes in one chamber by
date, then roll-call number. These four states store a vote's day without a time, so two votes on one day (a re-vote
after reconsideration) need the number to come out in the order they were taken. The scrapers write it on every new
vote; stored votes from before that carry nothing, and a scrape does not re-import an old roll call. This writes the
same value the scraper would, from data already stored:

    wa  the roll call's SequenceNumber (the chamber's roll-call order for that day), kept in the motion text as "(#N)"
    mi  the journal's roll-call number, kept in the motion text as "Roll Call #N"
    va  the time of day (HHMMSS) of the vote's VoteDate. A stored vote does not keep the time, so it is read from
        saved LIS getvotebyidasync answers (--va-votes: a directory of their JSON, one per bill), matched on the
        VoteID the vote's dedupe key "<VoteID>-<bill>" holds. LIS's VoteID itself is not in vote order.
    az  the time of day (HHMMSS) of the roll call's ReportDate; Arizona prints no roll-call number, and a stored vote
        does not keep the time, so it is read from the scrape cache's BillStatusFloorAction answers (--az-cache),
        matched on the vote's billStatusActionId and ReferralNumber.
    ne  the vote's KeyID on nebraskalegislature.gov, kept as its dedupe key; it rises in the order the votes were
        taken (LB 48, 2025-05-30: 12956, then 12957). Key `legislature-rollcall-num`.
    la  the roll call's number, kept in the motion text as "(#N)" (SB 487's House, 2026-05-19: #1393, then #1400).
    nm  the roll call's RCS number, printed on its PDF. A stored vote keeps only the PDF's address (its dedupe key),
        so it is read from the PDFs' text saved under --nm-votes (one file per vote: the address, URL-quoted with
        no safe characters, plus ".txt", holding `pdftotext -layout` of that PDF).
    Without its directory, Virginia, Arizona or New Mexico is left as it is.

Every write needs --expect N. Only a vote with no roll-call key at all is written; a stored number is never
changed. A vote whose number cannot be read is left as it is and counted.

A reviewed list is applied where the scrape cache does not exist (production): --list writes the changes (dry run or
write), --apply-list writes exactly a list's changes, --undo takes a list's keys off again. Every write is guarded: a
row that no longer matches the list (it gained a number, or holds another one) aborts the run with nothing written.

Usage:
    python3 backfill-vote-rollcall-num.py --dry-run [--jurisdiction wa] [--az-cache DIR] [--va-votes DIR] [--nm-votes DIR]
        --list FILE
    python3 backfill-vote-rollcall-num.py --apply-list FILE --expect N --list COMMITTED
    python3 backfill-vote-rollcall-num.py --undo COMMITTED --expect N --list UNDONE
"""
import argparse
import csv
import importlib.util
import json
import os
import re
import sys

import psycopg2
import psycopg2.extras

from qa_primitives import ocd_jurisdiction_id

# The OCD jurisdiction map and the DB settings come from the classification backfill (OPEN-625), not a third copy.
_spec = importlib.util.spec_from_file_location(
    "backfill_motion_classification",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "backfill-motion-classification.py"),
)
_bmc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_bmc)

STATES = ("wa", "mi", "va", "az", "ne", "la", "nm")
# OPEN-685: the ids come from the manifest itself (qa_primitives), as backfill-motion-classification.py's map does, but
# without its "has motion rules" filter: New Mexico has no motion rules and still needs its numbers.
JURISDICTIONS = {ocd_jurisdiction_id(key): key for key in STATES}
KEYS = ("house-rollcall-num", "senate-rollcall-num", "legislature-rollcall-num")
CHAMBER_KEYS = {"lower": "house-rollcall-num", "upper": "senate-rollcall-num", "legislature": "legislature-rollcall-num"}

FETCH_SQL = """
    SELECT
        ve.id,
        ve.motion_text,
        ve.dedupe_key,
        ve.extras,
        j.id AS jurisdiction_id,
        b.identifier AS bill,
        ve.start_date,
        o.classification AS chamber
    FROM opencivicdata_voteevent ve
    JOIN opencivicdata_legislativesession ls ON ls.id = ve.legislative_session_id
    JOIN opencivicdata_jurisdiction j ON j.id = ls.jurisdiction_id
    LEFT JOIN opencivicdata_bill b ON b.id = ve.bill_id
    JOIN opencivicdata_organization o ON o.id = ve.organization_id
    WHERE j.id = ANY(%s)
    ORDER BY j.id, ve.id
"""

# Guarded: adds the key only while the row still has neither roll-call key.
APPLY_SQL = """
    UPDATE opencivicdata_voteevent
    SET extras = extras || jsonb_build_object(%s::text, %s::text)
    WHERE id = %s AND NOT (extras ?| array['house-rollcall-num', 'senate-rollcall-num', 'legislature-rollcall-num'])
"""

# Guarded: takes the key off only while it still holds the value this backfill wrote.
UNDO_SQL = """
    UPDATE opencivicdata_voteevent
    SET extras = extras - %s::text
    WHERE id = %s AND extras->>%s::text = %s
"""

LIST_COLUMNS = ["id", "jurisdiction", "bill", "date", "chamber", "motion_text", "key", "rollcall_num"]

# The scrapers' own formats: mi/bills.py reads "Roll Call #44" (House) and "ROLL CALL # 1" (Senate);
# wa/bills.py writes the motion text as "{Motion} (#{SequenceNumber})".
_MI_ROLL_CALL = re.compile(r"Roll Call #\s*(\d+)", re.IGNORECASE)
_WA_SEQUENCE = re.compile(r"\(#(\d+)\)\s*$")
_VA_VOTE_ID = re.compile(r"^(\d+)-")
_AZ_DEDUPE = re.compile(r"billStatusId=(\d+)&billStatusActionId=(\d+)&includeVotes=true(\d+)$")
_AZ_CACHE_NAME = re.compile(r"billStatusId=(\d+)&billStatusActionId=(\d+)&includeVotes=true")
_NE_KEY_ID = re.compile(r"^\d+$")
_NM_RCS = re.compile(r"RCS#\s*(\d+)")  # the scraper's own read (nm/votes.py rollcall_number)


def az_report_times(cache_dir):
    """{(billStatusId, billStatusActionId, ReferralNumber): "HHMMSS"} from every cached BillStatusFloorAction answer."""
    times = {}
    for name in os.listdir(cache_dir):
        if not name.startswith("apps.azleg.gov,api,BillStatusFloorAction,"):
            continue
        found = _AZ_CACHE_NAME.search(name)
        if not found:
            continue
        with open(os.path.join(cache_dir, name), "rb") as f:
            raw = f.read()
        start = raw.find(b"[")  # the cache file is the response's headers, then its body
        if start < 0:
            continue
        for action in json.loads(raw[start:]):
            if action.get("ReportDate"):
                # the scraper's own parse: "2026-02-17T11:54:33.000" -> 115433
                clock = action["ReportDate"].split(".")[0].split("T")[1]
                times[(found.group(1), found.group(2), str(action.get("ReferralNumber")))] = clock.replace(":", "")
    return times


def va_vote_times(votes_dir):
    """{VoteID: "HHMMSS"} from every saved LIS getvotebyidasync answer (JSON with a "Votes" list) in a directory."""
    times = {}
    for name in os.listdir(votes_dir):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(votes_dir, name)) as f:
            answer = json.load(f)
        for vote in answer.get("Votes") or []:
            if vote.get("VoteID") and vote.get("VoteDate"):
                # the scraper's own value: "2026-02-12T08:49:55" -> 084955
                clock = vote["VoteDate"].split(".")[0].split("T")[1]
                times[str(vote["VoteID"])] = clock.replace(":", "")
    return times


def nm_vote_rcs(votes_dir):
    """{PDF address: RCS number} from saved PDF text: one file per vote, named by its URL-quoted address + ".txt"."""
    from urllib.parse import unquote

    numbers = {}
    for name in os.listdir(votes_dir):
        if not name.endswith(".txt"):
            continue
        with open(os.path.join(votes_dir, name), errors="replace") as f:
            found = _NM_RCS.search(f.read())
        if found:
            numbers[unquote(name[: -len(".txt")])] = found.group(1)
    return numbers


def rollcall_num(state, row, az_times, va_times=None, nm_rcs=None):
    """The value the state's scraper writes today, read from the stored row; None when it cannot be read."""
    if state == "mi":
        found = _MI_ROLL_CALL.search(row["motion_text"] or "")
    elif state in ("wa", "la"):
        # Louisiana's link text ends "(#N)" too: "FINAL PASSAGE (#1400)".
        found = _WA_SEQUENCE.search(row["motion_text"] or "")
    elif state == "ne":
        found = _NE_KEY_ID.match(row["dedupe_key"] or "")
        return found.group(0) if found else None
    elif state == "nm":
        return (nm_rcs or {}).get(row["dedupe_key"] or "")
    elif state == "va":
        found = _VA_VOTE_ID.search(row["dedupe_key"] or "")
        if not found or va_times is None:
            return None
        return va_times.get(found.group(1))
    else:
        found = _AZ_DEDUPE.search(row["dedupe_key"] or "")
        if not found or az_times is None:
            return None
        return az_times.get(found.groups())
    return found.group(1) if found else None


def plan(rows, az_times, va_times=None, nm_rcs=None):
    """(changes, counts): one change per vote that has no roll-call key and whose number can be read."""
    changes, counts = [], {"already": 0, "unread": 0}
    for row in rows:
        if any(key in (row["extras"] or {}) for key in KEYS):
            counts["already"] += 1
            continue
        state = JURISDICTIONS[row["jurisdiction_id"]]
        value = rollcall_num(state, row, az_times, va_times, nm_rcs)
        # "legislature" is Nebraska's one chamber; in any other state it is not a chamber this writes for.
        if value is None or row["chamber"] not in CHAMBER_KEYS or (row["chamber"] == "legislature") != (state == "ne"):
            counts["unread"] += 1
            continue
        changes.append(dict(
            id=row["id"], jurisdiction=state, bill=row["bill"], date=row["start_date"], chamber=row["chamber"],
            motion_text=row["motion_text"], key=CHAMBER_KEYS[row["chamber"]], rollcall_num=value,
        ))
    return changes, counts


def check_list(changes):
    """A list is written only if every row names a roll-call key and a number, each vote once (pm-review)."""
    bad = [
        c.get("id") for c in changes
        if c.get("key") not in KEYS or not re.fullmatch(r"[0-9]+", str(c.get("rollcall_num", "")))
    ]
    ids = [c.get("id") for c in changes]
    if bad or not all(ids) or len(set(ids)) != len(ids):
        sys.exit(f"aborted, nothing written: the list has rows without a roll-call key and number ({bad[:5]}), "
                 "an empty id, or a vote twice")


def write(conn, changes, undo, list_path):
    """Write every change or none: a guard miss rolls the whole run back."""
    check_list(changes)
    with conn.cursor() as cur:
        updated = 0
        for c in changes:
            if undo:
                cur.execute(UNDO_SQL, (c["key"], c["id"], c["key"], c["rollcall_num"]))
            else:
                cur.execute(APPLY_SQL, (c["key"], c["rollcall_num"], c["id"]))
            updated += cur.rowcount
    if updated != len(changes):
        conn.rollback()
        sys.exit(
            f"aborted, nothing written: {len(changes)} changes planned, {updated} rows still matched the list "
            "(a row changed underneath, or the list is stale)"
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


def read_list(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _write_list(path, rows):
    with open(path, "x", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LIST_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing")
    parser.add_argument("--jurisdiction", choices=STATES, help="only this state")
    parser.add_argument("--az-cache", help="scrapelib cache with Arizona's BillStatusFloorAction answers")
    parser.add_argument("--va-votes", help="directory of saved LIS getvotebyidasync answers (JSON)")
    parser.add_argument("--nm-votes", help="directory of New Mexico roll-call PDF text (URL-quoted address + .txt)")
    parser.add_argument("--list", dest="list_path", help="write the changes (planned, or written) to this CSV")
    parser.add_argument("--apply-list", help="write exactly this list's changes (no reading)")
    parser.add_argument("--undo", help="take this list's keys off again")
    parser.add_argument("--expect", type=int, help="abort unless exactly this many rows change")
    args = parser.parse_args(argv)

    if args.apply_list and args.undo:
        parser.error("--apply-list and --undo are separate runs")
    if not args.dry_run and args.expect is None:
        parser.error("a write needs --expect N (the count a dry run or the list gave)")
    if args.list_path and os.path.exists(args.list_path):
        parser.error(f"{args.list_path} already exists; an earlier list is never overwritten")

    conn = psycopg2.connect(_bmc.DATABASE_URL) if _bmc.DATABASE_URL else psycopg2.connect(**_bmc.DB_CONFIG)
    conn.autocommit = False
    try:
        if args.apply_list or args.undo:
            changes = read_list(args.apply_list or args.undo)
            print(f"{len(changes):,} changes read from {args.apply_list or args.undo}" + (" (undo)" if args.undo else ""))
        else:
            ids = [ocd for ocd, key in JURISDICTIONS.items() if not args.jurisdiction or key == args.jurisdiction]
            az_times = az_report_times(args.az_cache) if args.az_cache else None
            va_times = va_vote_times(args.va_votes) if args.va_votes else None
            nm_rcs = nm_vote_rcs(args.nm_votes) if args.nm_votes else None
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(FETCH_SQL, (ids,))
                rows = cur.fetchall()
            changes, counts = plan(rows, az_times, va_times, nm_rcs)
            print(f"Processing {len(rows):,} vote events across {len(ids)} jurisdictions...")
            print(f"  already numbered: {counts['already']:,}; number not readable, left as they are: "
                  f"{counts['unread']:,} (Arizona/Virginia/New Mexico: no --az-cache/--va-votes/--nm-votes, or not in it)")
        per_state = {}
        for c in changes:
            per_state[(c["jurisdiction"], c["key"])] = per_state.get((c["jurisdiction"], c["key"]), 0) + 1
        for (state, key), n in sorted(per_state.items()):
            print(f"  {state} {key}: {n:,}")
        if args.expect is not None and len(changes) != args.expect:
            conn.rollback()
            sys.exit(f"aborted, nothing written: {len(changes):,} changes, --expect {args.expect:,}")
        if args.dry_run:
            conn.rollback()
            if args.list_path:
                _write_list(args.list_path, changes)
            print(f"Dry run complete. Would update {len(changes):,} records.")
        else:
            write(conn, changes, bool(args.undo), args.list_path)
            print(f"Done. Updated {len(changes):,} records.")
        if args.list_path:
            print(f"  list: {args.list_path} ({len(changes):,} rows)")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
