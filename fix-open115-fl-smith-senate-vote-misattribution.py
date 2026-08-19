#!/usr/bin/env python3
"""
Fix Florida Senate votes misattributed from Carlos Smith to Dave Smith.

OPEN-115, found by OPEN-111's cross-jurisdiction audit for the OPEN-110/OPEN-112
misattribution shape. This is the mirror image of OPEN-110's own fix
(fix-open110-fl-smith-vote-misattribution.py), on the other chamber: that
ticket's backfill only touched Florida House ("lower") rows wrongly attributed
to Carlos Smith; this ticket covers Florida Senate ("upper") rows carrying
voter_name="Smith" with voter_id pointing to Dave Smith
(ocd-person/e4bf077a-8468-49a6-a75c-24ee5076352e), a Florida House member --
his own real Senate votes, currently credited to Dave. The real voter is
Carlos Smith (ocd-person/df1d6ab6-b2cd-4a6f-b7cc-aa5a63d8011f), Florida Senate
since 2024-11-05.

Confirmed via a live call to the current (OPEN-112-fixed) resolve_person()
against this exact data that it resolves "Smith" to Carlos (the Senate
member), not Dave, for these jurisdiction/chamber/session parameters. This
confirms the OPEN-112 cache-bleed bug corrupted this exact pair's data in
BOTH directions: whichever chamber's lookup happened to run first in a given
import run poisoned the other (House in the batch OPEN-110 addressed, Senate
in this one).

Establishing that Dave Smith never held any upper-chamber membership at all
only proves the current attribution is wrong; it doesn't by itself prove
Carlos is right for every specific row. So this script also positively
verifies, per row and at write time, that Carlos actually held an 'upper'
membership in Florida on that row's own vote date (see ELIGIBILITY_SQL below)
-- the same date-anchored standard used in OPEN-116's blank-voter_id backfill
in this same batch. Any row that doesn't verify is left alone and reported
separately, never repointed on the strength of "Dave couldn't have done it"
alone.

Confirmed no row-level conflicts as of this investigation pass: none of the
affected vote_events already have a row for Carlos Smith, which would make
re-pointing create a duplicate voter on one roll call. The script re-checks
this itself immediately before writing rather than relying solely on this
investigation, in case the replica has changed since.

Safe to re-run: the WHERE clause matches only rows still pointing at Dave, so
already-fixed rows are excluded on a second run. The UPDATE also re-checks
voter_id at write time (not just id), and the script aborts without
committing if the number of rows actually updated doesn't match the number
expected to be updated -- both guard against a row changing underneath this
script between validation and the write.

NOT YET RUN FOR REAL as of this PR -- dry-run only, pending review (OPEN-115).

Usage:
    python3 fix-open115-fl-smith-senate-vote-misattribution.py [--dry-run]
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

FL_JURISDICTION_ID = "ocd-jurisdiction/country:us/state:fl/government"
WRONG_PERSON_ID = "ocd-person/e4bf077a-8468-49a6-a75c-24ee5076352e"  # Dave Smith (House)
CORRECT_PERSON_ID = "ocd-person/df1d6ab6-b2cd-4a6f-b7cc-aa5a63d8011f"  # Carlos Smith (Senate)

FETCH_SQL = """
    SELECT pv.id, ve.id, ve.start_date::date
    FROM opencivicdata_personvote pv
    JOIN opencivicdata_voteevent ve ON ve.id = pv.vote_event_id
    JOIN opencivicdata_organization o ON o.id = ve.organization_id
    JOIN opencivicdata_legislativesession ls ON ls.id = ve.legislative_session_id
    WHERE ls.jurisdiction_id = %s
      AND o.classification = 'upper'
      AND pv.voter_name = 'Smith'
      AND pv.voter_id = %s
"""

# Date-anchored: did Carlos Smith actually hold an 'upper' membership in
# Florida on this exact vote date? (Not "currently" -- on that date.)
ELIGIBILITY_SQL = """
    SELECT 1
    FROM opencivicdata_membership m
    JOIN opencivicdata_organization o ON o.id = m.organization_id
    WHERE m.person_id = %s
      AND o.classification = 'upper'
      AND o.jurisdiction_id = %s
      AND (m.start_date = '' OR m.start_date <= %s)
      AND (m.end_date = '' OR m.end_date >= %s)
"""

DUPLICATE_CHECK_SQL = """
    SELECT 1 FROM opencivicdata_personvote other
    WHERE other.vote_event_id = %s AND other.voter_id = %s
"""

UPDATE_SQL = "UPDATE opencivicdata_personvote SET voter_id = %s WHERE id = %s AND voter_id = %s"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing")
    args = parser.parse_args()

    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False

    with conn.cursor() as cur:
        cur.execute(FETCH_SQL, (FL_JURISDICTION_ID, WRONG_PERSON_ID))
        rows = cur.fetchall()
        print(f"Found {len(rows):,} Florida Senate vote records currently "
              f"misattributed to Dave Smith ({WRONG_PERSON_ID}).")

        fillable, not_eligible, duplicate = [], [], []
        for pv_id, ve_id, vote_date in rows:
            cur.execute(
                ELIGIBILITY_SQL,
                (CORRECT_PERSON_ID, FL_JURISDICTION_ID, str(vote_date), str(vote_date)),
            )
            if not cur.fetchone():
                not_eligible.append(pv_id)
                continue
            cur.execute(DUPLICATE_CHECK_SQL, (ve_id, CORRECT_PERSON_ID))
            if cur.fetchone():
                duplicate.append(pv_id)
                continue
            fillable.append(pv_id)

        if not_eligible:
            print(f"Leaving {len(not_eligible)} row(s) alone -- Carlos Smith did not hold "
                  f"an 'upper' seat on that row's own vote date: {not_eligible}")
        if duplicate:
            print(f"Leaving {len(duplicate)} row(s) alone -- would create a duplicate "
                  f"voter on their vote_event: {duplicate}")

        if args.dry_run:
            print(f"Dry run complete. Would re-point {len(fillable):,} of {len(rows):,} "
                  f"records to Carlos Smith ({CORRECT_PERSON_ID}).")
        else:
            update_cur = conn.cursor()
            updated = 0
            for row_id in fillable:
                update_cur.execute(UPDATE_SQL, (CORRECT_PERSON_ID, row_id, WRONG_PERSON_ID))
                updated += update_cur.rowcount
            if updated != len(fillable):
                conn.rollback()
                raise SystemExit(
                    f"Aborting without committing: expected to update {len(fillable)} "
                    f"rows but only {updated} matched at write time -- a row likely "
                    f"changed underneath this script. Investigate before re-running."
                )
            conn.commit()
            print(f"Done. Re-pointed {updated:,} of {len(rows):,} records to Carlos Smith "
                  f"({CORRECT_PERSON_ID}).")

    conn.close()


if __name__ == "__main__":
    main()
