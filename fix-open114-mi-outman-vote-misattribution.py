#!/usr/bin/env python3
"""
Fix Michigan Senate votes misattributed from Rick Outman to Pat Outman.

OPEN-114, found by OPEN-111's cross-jurisdiction audit for the OPEN-110/OPEN-112
misattribution shape. 430 opencivicdata_personvote rows for Michigan Senate
("upper") roll calls carry voter_name="Outman" but voter_id pointing to Pat
Outman (ocd-person/1a809c60-e0a4-4b43-bdba-43f097021b1f), a Michigan House
member. The real voter is Rick Outman (ocd-person/9c525554-fb85-45f3-87fa-
cf6a3208ce32), who held a Michigan House seat 2011-2016, left, and returned to
the legislature in the Senate continuously since 2019 -- a chamber change, but
no seat succession or relation with Pat Outman, a separate, current House
member; just a shared surname.

Confirmed via a live call to the current (OPEN-112-fixed) resolve_person()
against this exact data that it resolves "Outman" to Rick (the Senate member),
not Pat, for these jurisdiction/chamber/session parameters.

Pat Outman has never held any upper-chamber membership at all (confirmed
directly against opencivicdata_membership -- his two 'lower' membership rows,
split by a redistricting-era post change, are both House), so any Senate vote
attributed to him is categorically wrong, not just wrong-for-a-date -- no date
guard is needed beyond the WHERE clause's own classification='upper' +
voter_id-is-Pat conditions.

Confirmed no row-level conflicts as of this investigation pass: none of the
430 affected vote_events already have a row for Rick Outman, which would make
re-pointing create a duplicate voter on one roll call. The script re-checks
this itself immediately before writing rather than relying solely on this
investigation, in case the replica has changed since.

Safe to re-run: the WHERE clause matches only rows still pointing at Pat, so
already-fixed rows are excluded on a second run. The UPDATE also re-checks
voter_id at write time (not just id), and the script aborts without
committing if the number of rows actually updated doesn't match the number
fetched -- both guard against a row changing underneath this script between
the fetch and the write.

NOT YET RUN FOR REAL as of this PR -- dry-run only, pending review (OPEN-114).

Usage:
    python3 fix-open114-mi-outman-vote-misattribution.py [--dry-run]
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

MI_JURISDICTION_ID = "ocd-jurisdiction/country:us/state:mi/government"
WRONG_PERSON_ID = "ocd-person/1a809c60-e0a4-4b43-bdba-43f097021b1f"  # Pat Outman (House)
CORRECT_PERSON_ID = "ocd-person/9c525554-fb85-45f3-87fa-cf6a3208ce32"  # Rick Outman (Senate)

FETCH_SQL = """
    SELECT pv.id
    FROM opencivicdata_personvote pv
    JOIN opencivicdata_voteevent ve ON ve.id = pv.vote_event_id
    JOIN opencivicdata_organization o ON o.id = ve.organization_id
    JOIN opencivicdata_legislativesession ls ON ls.id = ve.legislative_session_id
    WHERE ls.jurisdiction_id = %s
      AND o.classification = 'upper'
      AND pv.voter_name = 'Outman'
      AND pv.voter_id = %s
"""

DUPLICATE_CHECK_SQL = """
    SELECT pv.id
    FROM opencivicdata_personvote pv
    WHERE pv.id = ANY(%s::uuid[])
      AND EXISTS (
          SELECT 1 FROM opencivicdata_personvote other
          WHERE other.vote_event_id = pv.vote_event_id AND other.voter_id = %s
      )
"""

UPDATE_SQL = "UPDATE opencivicdata_personvote SET voter_id = %s WHERE id = %s AND voter_id = %s"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing")
    args = parser.parse_args()

    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False

    with conn.cursor() as cur:
        cur.execute(FETCH_SQL, (MI_JURISDICTION_ID, WRONG_PERSON_ID))
        row_ids = [row[0] for row in cur.fetchall()]
        print(f"Found {len(row_ids):,} Michigan Senate vote records currently "
              f"misattributed to Pat Outman ({WRONG_PERSON_ID}).")

        cur.execute(DUPLICATE_CHECK_SQL, (row_ids, CORRECT_PERSON_ID))
        duplicate_rows = [row[0] for row in cur.fetchall()]
        if duplicate_rows:
            raise SystemExit(
                f"Aborting: {len(duplicate_rows)} row(s) would create a duplicate "
                f"Rick Outman voter on their vote_event -- investigate before "
                f"re-running: {duplicate_rows}"
            )

        if args.dry_run:
            print(f"Dry run complete. Would re-point {len(row_ids):,} records "
                  f"to Rick Outman ({CORRECT_PERSON_ID}). No duplicate-voter "
                  f"conflicts found.")
        else:
            update_cur = conn.cursor()
            updated = 0
            for row_id in row_ids:
                update_cur.execute(UPDATE_SQL, (CORRECT_PERSON_ID, row_id, WRONG_PERSON_ID))
                updated += update_cur.rowcount
            if updated != len(row_ids):
                conn.rollback()
                raise SystemExit(
                    f"Aborting without committing: expected to update {len(row_ids)} "
                    f"rows but only {updated} matched at write time -- a row likely "
                    f"changed underneath this script. Investigate before re-running."
                )
            conn.commit()
            print(f"Done. Re-pointed {updated:,} records to Rick Outman ({CORRECT_PERSON_ID}).")

    conn.close()


if __name__ == "__main__":
    main()
