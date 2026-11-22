#!/usr/bin/env python3
"""
Fill voter_id on stored state roll-call votes that were imported before the person they name was in the database,
only where exactly one legislator could have cast them (OPEN-611).

Why: a vote row whose voter could not be matched at import is stored with voter_id NULL, and an incremental scrape
never re-imports an old roll call, so the row stays blank after the people data is fixed (an `other_names` entry, a
term) even though a new import would link it. Such a vote drops out of the legislator's page and scorecard.

How (copied from archive/person-matching-fixes/fix-open116-blank-voter-id-same-surname-backfill.py, as PRIMITIVES.md
says to): for every blank row of a case, the people who match the roll call's name -- by name, other name or family
name, case-insensitive, as core's resolve_person() matches -- AND held a seat in that chamber of that state ON THE
VOTE'S OWN DATE are read straight from the membership table. The row is filled only if there is exactly one such
person and that person is not already a voter on the same roll call. Anything else is left blank and reported. It
never touches a row that has a voter, never deletes, and never guesses from who holds the seat now.

Cases (OPEN-611, read on the production replica 2026-11-17):
  wa lower "Hunt"            673  Victoria Hunt; her House term reached the database (2026-10-25) after the votes
  ma lower "Garcia"            8  Judith García; her "Garcia" other name loaded after the votes (2026-08-23)
  mi lower "Myers-Phillips"   11  Tonya Phillips; the "Myers-Phillips" other name (2026-08-26) loaded after the votes
  fl lower "Garcia"          469  Alina García; needs people #27 ("Garcia" other name) loaded first, else 0 fill
  nc lower "Helfrich"        807  Beth Gardner Helfrich (House since 2025-01-01; 2025: 802, 2025E1: 5); needs people #22
                                  (OPEN-233, "Helfrich" other name) loaded first, else 0 fill. Added 2026-11-17 (Ramon:
                                  "Fold into OPEN-611")
  nc upper "Tillett"           5  Jerry Tillett (Senate since 2026-09-03; the 2026-11-17 votes of session 2025). No
                                  people change: his family name matches. The import skipped him because session
                                  2025's stored end date (2026-07-01) is before his start; the source fix is that
                                  date (OPEN-765). Commit only after OPEN-765 is live: a re-import under the old date
                                  blanks them again. Added 2026-11-22 (Ramon: "Yes, build it", "Yes, fix the end date")
US Congress votes are not here: they carry the member's id, and backfill-vote-person-resolution.py fills them.

Scorecards: a filled row starts counting on that legislator's scorecard. Each state's commit needs the scorecard gate
(PLAN-state-specific-handling section 8): this script's --list for that state, validate_scorecards and
reconcile_scorecards before and after, a sample checked against the legislature's journal, and Ramon's go.

Usage:
    python3 relink-blank-voters.py [--state wa] [--list FILE] [--commit]
Without --commit it is a dry run and writes nothing. Connects via DATABASE_URL if set, otherwise the OPENSTATES_DB_*
variables (defaults: the Mac's local Postgres on :5433).
"""
import argparse
import csv
import os
import sys

import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")
DB_CONFIG = {
    "host": os.getenv("OPENSTATES_DB_HOST", "localhost"),
    "port": int(os.getenv("OPENSTATES_DB_PORT", "5433")),
    "dbname": os.getenv("OPENSTATES_DB_NAME", "openstates"),
    "user": os.getenv("OPENSTATES_DB_USER", "openstates"),
    "password": os.getenv("OPENSTATES_DB_PASSWORD", "openstates_dev"),
}

# (state, chamber classification, the name the roll call stores in voter_name)
CASES = [
    ("wa", "lower", "Hunt"),
    ("ma", "lower", "Garcia"),
    ("mi", "lower", "Myers-Phillips"),
    ("fl", "lower", "Garcia"),
    ("nc", "lower", "Helfrich"),
    ("nc", "upper", "Tillett"),
]


def jurisdiction_id(state):
    return f"ocd-jurisdiction/country:us/state:{state}/government"


FETCH_BLANK_ROWS_SQL = """
    SELECT pv.id, ve.id, ve.start_date::date, left(ve.motion_text, 120), coalesce(b.identifier, ''),
           ls.identifier, pv.option
    FROM opencivicdata_personvote pv
    JOIN opencivicdata_voteevent ve ON ve.id = pv.vote_event_id
    JOIN opencivicdata_organization o ON o.id = ve.organization_id
    JOIN opencivicdata_legislativesession ls ON ls.id = ve.legislative_session_id
    LEFT JOIN opencivicdata_bill b ON b.id = ve.bill_id
    WHERE ls.jurisdiction_id = %s
      AND o.classification = %s
      AND pv.voter_name = %s
      AND pv.voter_id IS NULL
    ORDER BY ve.start_date, pv.id
"""

# Who matches the name (as resolve_person() matches it) and held a seat in this chamber ON THIS DATE.
CANDIDATES_ON_DATE_SQL = """
    SELECT DISTINCT p.id, p.name
    FROM opencivicdata_person p
    JOIN opencivicdata_membership m ON m.person_id = p.id
    JOIN opencivicdata_organization o ON o.id = m.organization_id
    WHERE (lower(p.name) = lower(%(name)s)
           OR lower(p.family_name) = lower(%(name)s)
           OR EXISTS (SELECT 1 FROM opencivicdata_personname n
                      WHERE n.person_id = p.id AND lower(n.name) = lower(%(name)s)))
      AND o.classification = %(chamber)s
      AND o.jurisdiction_id = %(jid)s
      AND (m.start_date = '' OR m.start_date <= %(day)s)
      AND (m.end_date = '' OR m.end_date >= %(day)s)
"""

DUPLICATE_CHECK_SQL = """
    SELECT 1 FROM opencivicdata_personvote other
    WHERE other.vote_event_id = %s AND other.voter_id = %s
"""

UPDATE_SQL = """
    UPDATE opencivicdata_personvote SET voter_id = %s
    WHERE id = %s AND voter_id IS NULL
"""

LIST_COLUMNS = [
    "state", "session", "vote_event", "bill", "date", "motion", "option", "voter_name", "person_id", "person_name"
]


def plan_case(cur, state, chamber, name):
    """(fillable rows as list-file dicts with the personvote id, rows left blank with the reason)."""
    jid = jurisdiction_id(state)
    cur.execute(FETCH_BLANK_ROWS_SQL, (jid, chamber, name))
    fill, left = [], []
    for pv_id, ve_id, day, motion, bill, session, option in cur.fetchall():
        cur.execute(CANDIDATES_ON_DATE_SQL, dict(name=name, chamber=chamber, jid=jid, day=str(day)))
        candidates = cur.fetchall()
        if len(candidates) != 1:
            left.append((pv_id, f"{len(candidates)} people of that name held a seat on {day}"))
            continue
        person_id, person_name = candidates[0]
        cur.execute(DUPLICATE_CHECK_SQL, (ve_id, person_id))
        if cur.fetchone():
            left.append((pv_id, f"{person_name} is already a voter on that roll call"))
            continue
        fill.append(
            dict(
                pv_id=pv_id,
                state=state,
                session=session,
                vote_event=ve_id,
                motion=motion,
                bill=bill,
                date=str(day),
                option=option,
                voter_name=name,
                person_id=person_id,
                person_name=person_name,
            )
        )
    return fill, left


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--state", help="only this state's case (wa, ma, mi, fl, nc)")
    parser.add_argument("--list", dest="list_path", help="write one CSV row per vote that is (or would be) filled")
    parser.add_argument("--commit", action="store_true", help="write; without it this is a dry run")
    args = parser.parse_args(argv)

    cases = [c for c in CASES if not args.state or c[0] == args.state.lower()]
    if not cases:
        parser.error(f"no case for state {args.state!r}")
    if args.commit and not args.list_path:
        parser.error("--commit needs --list FILE: that file is the record of what changed")
    if args.list_path and (os.path.exists(args.list_path) or os.path.exists(f"{args.list_path}.partial")):
        parser.error(f"{args.list_path} (or its .partial) already exists; an earlier record is never overwritten")

    conn = psycopg2.connect(DATABASE_URL) if DATABASE_URL else psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    mode = "COMMITTED" if args.commit else "DRY RUN"
    all_fill = []
    try:
        with conn.cursor() as cur:
            for state, chamber, name in cases:
                fill, left = plan_case(cur, state, chamber, name)
                all_fill.extend(fill)
                print(f"{state} {chamber} {name!r}: [{mode}] fill={len(fill)} left_blank={len(left)}")
                reasons = {}
                for _, why in left:
                    reasons[why] = reasons.get(why, 0) + 1
                for why, n in sorted(reasons.items(), key=lambda kv: -kv[1]):
                    print(f"  left blank: {n} ({why})")
            if args.commit:
                updated = 0
                for row in all_fill:
                    cur.execute(UPDATE_SQL, (row["person_id"], row["pv_id"]))
                    updated += cur.rowcount
                if updated != len(all_fill):
                    conn.rollback()
                    sys.exit(
                        f"aborted, nothing written: expected to fill {len(all_fill)} rows, {updated} matched at write "
                        "time (a row changed underneath); investigate before running again"
                    )
                # As core's relabel: the list is written aside and takes its name only after the database commit,
                # so a failed or rolled-back run leaves no list that reads as done.
                _write_list(f"{args.list_path}.partial", all_fill)
                try:
                    conn.commit()
                except Exception as e:
                    # A failed commit may still have reached the database, so the list is kept. A second run is safe:
                    # it only fills rows that are still blank, and a dry run without --list shows what is left.
                    sys.exit(
                        f"commit raised ({e!r}); the outcome is unknown. The planned changes are in "
                        f"{args.list_path}.partial (keep it). To see which rows are still blank, run this script again "
                        "without --commit and without --list"
                    )
                try:
                    os.replace(f"{args.list_path}.partial", args.list_path)
                except OSError as e:
                    sys.exit(
                        f"COMMITTED ({len(all_fill)} rows filled), but the list could not take its name ({e}); it is "
                        f"complete at {args.list_path}.partial. Do not run again: the commit is done"
                    )
            else:
                conn.rollback()
                if args.list_path:
                    _write_list(args.list_path, all_fill)
    finally:
        conn.close()
    if args.list_path:
        print(f"  list: {args.list_path} ({len(all_fill)} rows)")


def _write_list(path, rows):
    with open(path, "x", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LIST_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
