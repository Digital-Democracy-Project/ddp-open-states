#!/usr/bin/env python3
"""
Backfill blank voter_id for Rep. Tonya Myers Phillips's Michigan House votes,
where the Michigan House journal names her differently from the roster.

OPEN-174. The Michigan House journal writes her as "Myers-Phillips". The
`openstates/people` roster records her as "Tonya Phillips" / family_name
"Phillips", having dropped the "Myers" -- so `resolve_person()`, which matches a
bare journal name against name / other_names / family_name, matches nothing and
every vote she casts imports with voter_id = NULL. 680 rows between 2025-01-08
and 2026-07-03, the largest unmatched name in Michigan.

Why the name mapping is evidence and not a guess
------------------------------------------------
Her own roster record contains the correction, in three independent places:

    email: tonyamyersphillips@house.mi.gov
    image: .../Tonya_Myers_Phillips_20241022_115414.png
    sources: ballotpedia.org/Tonya_Myers_Phillips
             en.wikipedia.org/wiki/Tonya_Myers_Phillips
             housedems.com/tonya-myers-phillips

plus an existing `other_names` entry reading "T.M. Phillips" -- the roster
half-knowing the middle name it dropped. The durable fix is upstream
(openstates/people#4036, open at the time of writing). This script repairs the
data that is already stored, which the roster fix cannot reach: voter_id is
resolved at vote-import time, so rows already in the database stay NULL until
they are re-imported, and re-importing them would mean a full ~7-8 hour Michigan
re-scrape (run-scrape.sh's do_scrape() wipes _data/<state> each run, so only the
last run's bills remain on disk).

Once the roster fix lands, a re-import writes the same value this script writes,
so this is a one-off catch-up rather than a recurring chore.

What it will and will not touch
-------------------------------
This script does NOT trust the name mapping alone. For every affected row it
independently re-derives, from opencivicdata_membership directly, who held a
Michigan *lower*-chamber seat under family_name "Phillips" ON THAT VOTE'S OWN
DATE -- the same date-anchored check as OPEN-116's backfill, not a resolver
opinion and not a "currently seated" tie-break. It then requires that the single
person found is exactly the identity this ticket verified
(ocd-person/787d9bda-d4dd-47fe-aaf0-348c505211e4).

Any row where that check does not find exactly one candidate, or finds someone
other than the expected person, is left alone and reported. Measured before
writing: she is the ONLY Michigan legislator in any chamber whose name or family
name contains "Phillips" or "Myers", and all 680 rows are lower-chamber rows
inside her open-ended term starting 2025-01-01 -- so no row is expected to be
ambiguous. The script re-checks anyway, per row, in case the replica changed.

It also refuses to create a duplicate voter on a roll call: if a vote event
already carries a row for her, that row is skipped.

Safe to re-run: the WHERE clause matches only rows still at voter_id IS NULL,
and the UPDATE re-checks voter_id IS NULL at write time. The script aborts
without committing if the number of rows actually updated does not match the
number it expected to update.

Usage:
    python3 fix-open174-mi-myers-phillips-voter-backfill.py --dry-run
    python3 fix-open174-mi-myers-phillips-voter-backfill.py
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

JURISDICTION_ID = "ocd-jurisdiction/country:us/state:mi/government"
CHAMBER = "lower"
JOURNAL_NAME = "Myers-Phillips"
ROSTER_FAMILY_NAME = "Phillips"
EXPECTED_PERSON_ID = "ocd-person/787d9bda-d4dd-47fe-aaf0-348c505211e4"

FETCH_BLANK_ROWS_SQL = """
    SELECT pv.id, pv.vote_event_id, ve.start_date
    FROM opencivicdata_personvote pv
    JOIN opencivicdata_voteevent ve ON ve.id = pv.vote_event_id
    JOIN opencivicdata_organization o ON o.id = ve.organization_id
    JOIN opencivicdata_legislativesession s ON s.id = ve.legislative_session_id
    WHERE s.jurisdiction_id = %s
      AND o.classification = %s
      AND pv.voter_name = %s
      AND pv.voter_id IS NULL
    ORDER BY ve.start_date
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


def find_unambiguous_person(cur, vote_date):
    """The one person holding this seat on this date, or None if not exactly one."""
    vote_date_str = str(vote_date)
    cur.execute(
        CANDIDATES_ON_DATE_SQL,
        (ROSTER_FAMILY_NAME, CHAMBER, JURISDICTION_ID, vote_date_str, vote_date_str),
    )
    candidates = [row[0] for row in cur.fetchall()]
    return candidates[0] if len(candidates) == 1 else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="Print changes without writing"
    )
    args = parser.parse_args()

    print(
        "fix-open174-mi-myers-phillips-voter-backfill -- mode={} db={}@{}:{}/{}".format(
            "DRY RUN" if args.dry_run else "APPLY",
            DB_CONFIG["user"],
            DB_CONFIG["host"],
            DB_CONFIG["port"],
            DB_CONFIG["dbname"],
        )
    )

    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False

    with conn.cursor() as cur:
        cur.execute(FETCH_BLANK_ROWS_SQL, (JURISDICTION_ID, CHAMBER, JOURNAL_NAME))
        rows = cur.fetchall()
        print(
            "Found {:,} blank-voter_id rows named {!r} in MI {}.".format(
                len(rows), JOURNAL_NAME, CHAMBER
            )
        )
        if not rows:
            print("Nothing to do.")
            conn.close()
            return

        fillable = []  # (personvote_id, resolved_person_id)
        ambiguous = []  # personvote_id -- no single candidate on that date
        unexpected = []  # personvote_id -- resolved to someone other than expected
        conflicts = []  # personvote_id -- she would end up on that roll call twice
        dates = set()

        # Two blank rows for the SAME voter on the SAME roll call must not both be
        # filled. Found the hard way on the first production run: three MI vote
        # events dated 2026-07-03 each carried two identical `Myers-Phillips`
        # rows. Both were NULL, so nothing double-counted her -- until this script
        # resolved both, and then each roll call counted her twice.
        #
        # DUPLICATE_CHECK_SQL alone does not catch it: it asks whether a row for
        # this person ALREADY exists, which is false for both members of a
        # blank pair. The batch has to remember what it has already queued.
        queued = set()  # (vote_event_id, person_id) filled earlier in this run

        for pv_id, ve_id, vote_date in rows:
            dates.add(str(vote_date))
            resolved = find_unambiguous_person(cur, vote_date)
            if resolved is None:
                ambiguous.append(pv_id)
                continue
            if resolved != EXPECTED_PERSON_ID:
                unexpected.append((pv_id, resolved))
                continue
            if (ve_id, resolved) in queued:
                conflicts.append(pv_id)
                continue
            cur.execute(DUPLICATE_CHECK_SQL, (ve_id, resolved))
            if cur.fetchone():
                conflicts.append(pv_id)
                continue
            queued.add((ve_id, resolved))
            fillable.append((pv_id, resolved))

        print("Distinct vote dates covered: {:,}".format(len(dates)))
        print(
            "  fillable                 : {:,}\n"
            "  no single candidate       : {:,}\n"
            "  resolved to someone else  : {:,}\n"
            "  would duplicate a voter   : {:,}".format(
                len(fillable), len(ambiguous), len(unexpected), len(conflicts)
            )
        )
        if ambiguous:
            print("  ambiguous rows left alone: {}".format(ambiguous[:20]))
        if unexpected:
            print("  UNEXPECTED person, left alone: {}".format(unexpected[:20]))
        if conflicts:
            print("  conflicting rows left alone: {}".format(conflicts[:20]))

        if args.dry_run:
            print(
                "\nDry run complete. Would fill {:,} of {:,} rows with {}.".format(
                    len(fillable), len(rows), EXPECTED_PERSON_ID
                )
            )
            conn.rollback()
            conn.close()
            return

        update_cur = conn.cursor()
        updated = 0
        for pv_id, resolved in fillable:
            update_cur.execute(UPDATE_SQL, (resolved, pv_id))
            updated += update_cur.rowcount
        if updated != len(fillable):
            conn.rollback()
            raise SystemExit(
                "Aborting without committing: expected to fill {} rows but only {} "
                "matched at write time -- a row likely changed underneath this "
                "script. Investigate before re-running.".format(len(fillable), updated)
            )
        conn.commit()
        print("\nDone. Filled {:,} of {:,} rows.".format(updated, len(rows)))

    conn.close()


if __name__ == "__main__":
    main()
