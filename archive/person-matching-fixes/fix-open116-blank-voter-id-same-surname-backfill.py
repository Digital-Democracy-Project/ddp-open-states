#!/usr/bin/env python3
"""
Backfill blank voter_id for three same-surname vote groups, where the correct
person is provably unambiguous by date -- not just "current code's opinion."

OPEN-116, found by OPEN-111's cross-jurisdiction audit for the OPEN-110/OPEN-112
misattribution shape. Unlike OPEN-110/113/114/115 (a real person's vote wrongly
attributed to a different, wrong real person), these rows have voter_id = NULL
-- never resolved to anyone at all:

- Florida Garcia: Senate ("upper") rows, bare voter_name="Garcia".
- Washington Hunt: Senate ("upper") rows, bare voter_name="Hunt".
- Michigan Greene: Senate ("upper") rows, bare voter_name="Greene".

OPEN-116's own scope note flagged that a fresh resolve_person() call agreeing
on a person isn't, by itself, as strong evidence as OPEN-2's Congress backfill
has (a stable bioguide/lis identifier) -- "today's code's opinion" could in
principle reflect only *today's* roster, not what was actually true on each
vote's own real date.

This script does NOT rely on that weaker signal. For every affected row, it
independently re-derives, from opencivicdata_membership directly, exactly how
many people with the group's surname held a matching-chamber seat in this
jurisdiction ON THE VOTE'S OWN DATE (not "currently," not "per resolve_person's
current_role tie-break") -- a genuinely date-anchored, not resolver-opinion-
based, uniqueness check. Confirmed across every one of the 41 (Garcia), 22
(Hunt), and 9 (Greene) distinct dates involved: exactly one person qualifies,
every time -- zero dates with 0 or 2+ candidates. The script re-verifies this
itself per-row at write time (see find_unambiguous_person below) rather than
trusting that earlier investigation pass alone, in case the replica has
changed since.

Any row where this check does NOT find exactly one candidate is left alone and
reported separately -- this script only fills in the provably unambiguous
rows, never guesses.

Confirmed no row-level conflicts as of this investigation pass: none of the
affected vote_events already have a row for the person this script would fill
in, which would make filling in create a duplicate voter on one roll call. The
script re-checks this itself immediately before writing.

Safe to re-run: the WHERE clause matches only rows still at voter_id IS NULL,
so already-filled rows are excluded on a second run. The UPDATE re-checks
voter_id IS NULL at write time (not just id), and the script aborts without
committing if the number of rows actually updated doesn't match the number it
expected to update.

NOT YET RUN FOR REAL as of this PR -- dry-run only, pending review (OPEN-116).

Usage:
    python3 fix-open116-blank-voter-id-same-surname-backfill.py [--dry-run]
"""
import argparse
import os

import psycopg2

DB_CONFIG = {
    "host": os.getenv("OPENSTATES_DB_HOST", "localhost"),
    "port": int(os.getenv("OPENSTATES_DB_PORT", "5433")),
    "dbname": os.getenv("OPENSTATES_DB_NAME", "openstates"),
    "user": os.getenv("OPENSTATES_DB_USER", "openstates"),
    "password": os.getenv("OPENSTATES_DB_PASSWORD", "openstates_dev"),
}

# Each group: (label, jurisdiction_id, surname, chamber classification).
GROUPS = [
    (
        "Florida Garcia",
        "ocd-jurisdiction/country:us/state:fl/government",
        "Garcia",
        "upper",
    ),
    (
        "Washington Hunt",
        "ocd-jurisdiction/country:us/state:wa/government",
        "Hunt",
        "upper",
    ),
    (
        "Michigan Greene",
        "ocd-jurisdiction/country:us/state:mi/government",
        "Greene",
        "upper",
    ),
]

FETCH_BLANK_ROWS_SQL = """
    SELECT pv.id, ve.id, ve.start_date::date
    FROM opencivicdata_personvote pv
    JOIN opencivicdata_voteevent ve ON ve.id = pv.vote_event_id
    JOIN opencivicdata_organization o ON o.id = ve.organization_id
    JOIN opencivicdata_legislativesession ls ON ls.id = ve.legislative_session_id
    WHERE ls.jurisdiction_id = %s
      AND o.classification = %s
      AND pv.voter_name = %s
      AND pv.voter_id IS NULL
"""

# Date-anchored: who actually held a matching-chamber seat in this jurisdiction
# on this exact date, independent of resolve_person()'s "current" tie-break.
CANDIDATES_ON_DATE_SQL = """
    SELECT DISTINCT p.id
    FROM opencivicdata_person p
    JOIN opencivicdata_membership m ON m.person_id = p.id
    JOIN opencivicdata_organization o ON o.id = m.organization_id
    WHERE p.family_name = %s
      AND o.classification = %s
      AND o.jurisdiction_id = %s
      AND (m.start_date = '' OR m.start_date <= %s)
      AND (m.end_date = '' OR m.end_date >= %s)
"""

DUPLICATE_CHECK_SQL = """
    SELECT 1 FROM opencivicdata_personvote other
    WHERE other.vote_event_id = %s AND other.voter_id = %s
"""

UPDATE_SQL = """
    UPDATE opencivicdata_personvote SET voter_id = %s
    WHERE id = %s AND voter_id IS NULL
"""


def find_unambiguous_person(cur, surname, chamber, jurisdiction_id, vote_date):
    vote_date_str = str(vote_date)
    cur.execute(
        CANDIDATES_ON_DATE_SQL,
        (surname, chamber, jurisdiction_id, vote_date_str, vote_date_str),
    )
    candidates = [row[0] for row in cur.fetchall()]
    return candidates[0] if len(candidates) == 1 else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing")
    args = parser.parse_args()

    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False

    with conn.cursor() as cur:
        for label, jurisdiction_id, surname, chamber in GROUPS:
            cur.execute(FETCH_BLANK_ROWS_SQL, (jurisdiction_id, chamber, surname))
            rows = cur.fetchall()
            print(f"[{label}] Found {len(rows):,} blank-voter_id rows.")

            fillable = []  # (personvote_id, resolved_person_id)
            ambiguous = []  # personvote_id -- left alone
            for pv_id, ve_id, vote_date in rows:
                resolved = find_unambiguous_person(
                    cur, surname, chamber, jurisdiction_id, vote_date
                )
                if resolved is None:
                    ambiguous.append(pv_id)
                    continue
                cur.execute(DUPLICATE_CHECK_SQL, (ve_id, resolved))
                if cur.fetchone():
                    ambiguous.append(pv_id)
                    continue
                fillable.append((pv_id, resolved))

            if ambiguous:
                print(f"[{label}] Leaving {len(ambiguous)} row(s) alone -- not a single, "
                      f"unambiguous, conflict-free candidate: {ambiguous}")

            if args.dry_run:
                print(f"[{label}] Dry run complete. Would fill {len(fillable):,} of "
                      f"{len(rows):,} rows.")
            else:
                update_cur = conn.cursor()
                updated = 0
                for pv_id, resolved in fillable:
                    update_cur.execute(UPDATE_SQL, (resolved, pv_id))
                    updated += update_cur.rowcount
                if updated != len(fillable):
                    conn.rollback()
                    raise SystemExit(
                        f"[{label}] Aborting without committing: expected to fill "
                        f"{len(fillable)} rows but only {updated} matched at write "
                        f"time -- a row likely changed underneath this script. "
                        f"Investigate before re-running."
                    )
                conn.commit()
                print(f"[{label}] Done. Filled {updated:,} of {len(rows):,} rows.")

    conn.close()


if __name__ == "__main__":
    main()
