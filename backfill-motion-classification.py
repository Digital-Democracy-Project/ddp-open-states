#!/usr/bin/env python3
"""
Backfill motion_classification for existing VoteEvent records.

Applies the same YAML-driven classify_motion() logic used by scrapers to all
existing records in the OpenStates DB so that votes scraped before the scraper
patches are also correctly classified.

Run once after the scraper patches are committed. Safe to re-run.

Usage:
    python3 backfill-motion-classification.py [--dry-run]
"""
import argparse
import os
import sys

import psycopg2
import psycopg2.extras

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "openstates-scrapers", "scrapers"))
from classify_motion import classify_motion  # noqa: E402

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
        ve.extras->>'bill_action' AS bill_action,
        j.id AS jurisdiction_id
    FROM opencivicdata_voteevent ve
    JOIN opencivicdata_legislativesession ls ON ls.id = ve.legislative_session_id
    JOIN opencivicdata_jurisdiction j ON j.id = ls.jurisdiction_id
    WHERE j.id = ANY(%s)
    ORDER BY j.id, ve.id
"""

UPDATE_SQL = """
    UPDATE opencivicdata_voteevent
    SET motion_classification = %s
    WHERE id = %s
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing")
    args = parser.parse_args()

    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False

    jurisdiction_ids = list(JURISDICTION_MAP.keys())
    updated = skipped = errors = 0

    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(FETCH_SQL, (jurisdiction_ids,))
        rows = cur.fetchall()
        print(f"Processing {len(rows):,} vote events across {len(jurisdiction_ids)} jurisdictions...")

        update_cur = conn.cursor()
        for row in rows:
            jur_key = JURISDICTION_MAP.get(row["jurisdiction_id"])
            if not jur_key:
                errors += 1
                continue

            try:
                new_classification = classify_motion(
                    jur_key,
                    row["motion_text"],
                    bill_action=row["bill_action"],
                )
            except Exception as e:
                print(f"  ERROR classifying {row['id']}: {e}", file=sys.stderr)
                errors += 1
                continue

            if args.dry_run:
                print(f"  {jur_key} | {row['motion_text']!r:.60} → {new_classification}")
                skipped += 1
            else:
                update_cur.execute(UPDATE_SQL, (new_classification, row["id"]))
                updated += 1

        if not args.dry_run:
            conn.commit()
            print(f"Done. Updated {updated:,} records. Errors: {errors}.")
        else:
            print(f"Dry run complete. Would update {skipped:,} records. Errors: {errors}.")

    conn.close()


if __name__ == "__main__":
    main()
