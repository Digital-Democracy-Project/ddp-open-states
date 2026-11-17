#!/usr/bin/env python3
"""
Fix Florida House votes misattributed from Dave Smith to Carlos Smith.

OPEN-110. Same disease as the Grijalva vote-misattribution fix
(GRIJALVA-vote-misattribution-fix-20260729.md / fix-grijalva-vote-misattribution.py),
found independently in a different chamber: 423 opencivicdata_personvote rows for
Florida House ("lower") roll calls carry voter_name="Smith" but voter_id pointing to
Carlos Smith (ocd-person/df1d6ab6-b2cd-4a6f-b7cc-aa5a63d8011f) -- the current Florida
Senate ("upper") member, who represented a *different* House district (49) until
2022-11-08. Dave Smith (ocd-person/e4bf077a-8468-49a6-a75c-24ee5076352e) has held his
own House seat (district 38) continuously since 2022-11-08 and is the person these
votes actually belong to -- there is no seat succession between them, just a shared
surname.

Confirmed all 423 rows are dated on or after 2022-11-08 (Carlos's last real day in
the House) -- none predate his departure, so none are his own legitimate House votes.
Confirmed via a live call to the current importer's own resolve_person() against this
exact data -- same jurisdiction, same "lower" classification, and every one of the four
legislative sessions the 423 rows actually span (2025B, 2026, 2026E, 2026F) -- that the
CURRENT matching code already resolves a bare "Smith" to Dave in every one of them, not
Carlos. So this is stale data written by an older import (pre-dating some earlier fix
to resolve_person, the same shape as the Grijalva case predating OPEN-2's
identifier-based matching), not a bug in the code running today. No source change
needed; this script is the correction that legacy data needs.

Confirmed no row-level conflicts as of the last investigation pass: none of the 423
vote_events already have a separate Dave Smith row (which would make re-pointing create
a duplicate voter on one roll call) -- every one of these vote_events currently has
exactly one "Smith" entry, and it's simply attributed to the wrong person. The script
re-checks this itself immediately before writing (see check_for_duplicate_voters
below) rather than relying solely on that earlier investigation, in case the replica
has changed since.

Safe to re-run: the WHERE clause matches only rows still pointing at Carlos, so
already-fixed rows are excluded on a second run. The UPDATE also re-checks voter_id at
write time (not just id), and the script aborts loudly if the number of rows actually
updated doesn't match the number fetched -- both guard against acting on a row that
changed underneath this script between the fetch and the write.

Usage:
    python3 fix-open110-fl-smith-vote-misattribution.py [--dry-run]
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
WRONG_PERSON_ID = "ocd-person/df1d6ab6-b2cd-4a6f-b7cc-aa5a63d8011f"  # Carlos Smith
CORRECT_PERSON_ID = "ocd-person/e4bf077a-8468-49a6-a75c-24ee5076352e"  # Dave Smith
# Carlos's real, last day in the Florida House -- Dave has held the seat since. Any
# row dated before this would be a legitimate Carlos vote and must not be touched;
# confirmed none exist, but the guard stays in the WHERE clause regardless.
CARLOS_HOUSE_DEPARTURE = "2022-11-08"

FETCH_SQL = """
    SELECT pv.id
    FROM opencivicdata_personvote pv
    JOIN opencivicdata_voteevent ve ON ve.id = pv.vote_event_id
    JOIN opencivicdata_organization o ON o.id = ve.organization_id
    JOIN opencivicdata_legislativesession ls ON ls.id = ve.legislative_session_id
    WHERE ls.jurisdiction_id = %s
      AND o.classification = 'lower'
      AND pv.voter_name = 'Smith'
      AND pv.voter_id = %s
      AND ve.start_date >= %s
"""

# A row here would mean re-pointing Carlos's row to Dave on that vote_event would
# create a second "Dave Smith" voter on the same roll call -- abort rather than risk
# that, even though the investigation found none of these as of its last pass.
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
        cur.execute(
            FETCH_SQL, (FL_JURISDICTION_ID, WRONG_PERSON_ID, CARLOS_HOUSE_DEPARTURE)
        )
        row_ids = [row[0] for row in cur.fetchall()]
        print(f"Found {len(row_ids):,} Florida House vote records currently "
              f"misattributed to Carlos Smith ({WRONG_PERSON_ID}).")

        cur.execute(DUPLICATE_CHECK_SQL, (row_ids, CORRECT_PERSON_ID))
        duplicate_rows = [row[0] for row in cur.fetchall()]
        if duplicate_rows:
            raise SystemExit(
                f"Aborting: {len(duplicate_rows)} row(s) would create a duplicate "
                f"Dave Smith voter on their vote_event -- investigate before "
                f"re-running: {duplicate_rows}"
            )

        if args.dry_run:
            print(f"Dry run complete. Would re-point {len(row_ids):,} records "
                  f"to Dave Smith ({CORRECT_PERSON_ID}). No duplicate-voter "
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
            print(f"Done. Re-pointed {updated:,} records to Dave Smith ({CORRECT_PERSON_ID}).")

    conn.close()


if __name__ == "__main__":
    main()
