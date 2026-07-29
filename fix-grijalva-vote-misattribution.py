#!/usr/bin/env python3
"""
Fix votes misattributed from Raul Grijalva to his successor Adelita Grijalva.

Found during OPEN-2 backfill verification (2026-07-29, see
OPEN-2-backfill-affected-legislators-20260729.md's "Follow-up" section): 62
opencivicdata_personvote rows carry Raul Grijalva's bioguide id (G000551) in
their `note` column, but voter_id already points to Adelita Grijalva -- his
successor in the same US House seat, who shares his surname. This predates
the OPEN-2 identifier-based fix: the old name-only matching resolved
"Grijalva" to whichever Person record it found first (Adelita, the current
officeholder at scrape time), rather than the person who actually cast the
vote.

Because voter_id was already non-null on these rows, OPEN-2's backfill
(voter_id IS NULL only) correctly never touched them -- filling blanks is
safe by construction (can only ever add information, never remove or change
it), whereas overwriting an existing value is not, so that script
deliberately never does it. This script is the narrower, higher-risk
correction that operation intentionally left out: it re-points these
specific rows to the person their own bioguide id actually identifies.

Confirmed via a full sweep of every US Congress vote record with a note
(2026-07-29, same verification pass): this exact pattern -- a resolved vote
whose voter_id disagrees with what its own note/identifier resolves to --
exists ONLY for bioguide G000551 (62 rows, all pointing to Adelita
Grijalva). No other legislator in the current dataset has this problem, so
this script is intentionally scoped to this one identifier and this one
wrong-person value, rather than a generic "fix every disagreement" sweep --
a generic version would need much more care (e.g. distinguishing "old wrong
name-match" from "a legitimate scheme collision" or "ambiguous, correctly
left unresolved") that hasn't been done here.

Safe to re-run: the WHERE clause matches only rows still pointing at the
wrong person, so already-fixed rows are excluded on a second run.

Usage:
    python3 fix-grijalva-vote-misattribution.py [--dry-run]
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

US_JURISDICTION_ID = "ocd-jurisdiction/country:us/government"
BIOGUIDE = "G000551"
WRONG_PERSON_ID = "ocd-person/e6661e65-1d1e-4c00-9c79-383941edc17a"  # Adelita Grijalva
CORRECT_PERSON_ID = "ocd-person/06cee575-8fbe-5552-9f2b-9fe5aa2a3725"  # Raul M. Grijalva

FETCH_SQL = """
    SELECT pv.id
    FROM opencivicdata_personvote pv
    JOIN opencivicdata_voteevent ve ON ve.id = pv.vote_event_id
    JOIN opencivicdata_legislativesession ls ON ls.id = ve.legislative_session_id
    WHERE ls.jurisdiction_id = %s
      AND pv.note = %s
      AND pv.voter_id = %s
"""

UPDATE_SQL = "UPDATE opencivicdata_personvote SET voter_id = %s WHERE id = %s"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing")
    args = parser.parse_args()

    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False

    with conn.cursor() as cur:
        cur.execute(FETCH_SQL, (US_JURISDICTION_ID, BIOGUIDE, WRONG_PERSON_ID))
        row_ids = [row[0] for row in cur.fetchall()]
        print(f"Found {len(row_ids):,} vote records with note={BIOGUIDE!r} "
              f"currently misattributed to Adelita Grijalva ({WRONG_PERSON_ID}).")

        if args.dry_run:
            print(f"Dry run complete. Would re-point {len(row_ids):,} records "
                  f"to Raul Grijalva ({CORRECT_PERSON_ID}).")
        else:
            update_cur = conn.cursor()
            for row_id in row_ids:
                update_cur.execute(UPDATE_SQL, (CORRECT_PERSON_ID, row_id))
            conn.commit()
            print(f"Done. Re-pointed {len(row_ids):,} records "
                  f"to Raul Grijalva ({CORRECT_PERSON_ID}).")

    conn.close()


if __name__ == "__main__":
    main()
