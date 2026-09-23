#!/usr/bin/env python3
"""OPEN-304: add 14 missing `lis`-scheme PersonIdentifier rows.

Stop-gap parallel to openstates/people#4094 (open upstream, no DDP control over merge timing --
one comparable PR in this same batch took 36 days, another has been open 58+ days unmerged).
Applies the identical fix directly so it's live now; the upstream PR stays open too and becomes a
no-op confirmation whenever/if it eventually merges. Safe to re-run: skips any person_id that
already has an `lis` identifier, and skips (reporting explicitly) any person_id this database
doesn't have at all rather than failing the whole batch.

Each (person_id, lis) pair is the same value already verified in openstates/people PR #4094 --
taken directly from real Senate.gov roll-call XML (lis_member_id), cross-checked by name+state
against real cast votes. Not re-derived here.

Usage:
    python3 open304-add-lis-identifiers.py [--dry-run]

Connects via DATABASE_URL if set (same convention as backfill-vote-person-resolution.py -- how
the Fargate launcher passes a live-resolved RDS credential), otherwise via the individual
OPENSTATES_DB_* vars for local/manual runs.
"""
import argparse
import os
import uuid

import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")
DB_CONFIG = {
    "host": os.getenv("OPENSTATES_DB_HOST", "localhost"),
    "port": int(os.getenv("OPENSTATES_DB_PORT", "5433")),
    "dbname": os.getenv("OPENSTATES_DB_NAME", "openstates"),
    "user": os.getenv("OPENSTATES_DB_USER", "openstates"),
    "password": os.getenv("OPENSTATES_DB_PASSWORD", "openstates_dev"),
}

FIXES = [
    ("ocd-person/93f7b243-f3e6-4fec-b65a-42f7a19939e3", "S428"),  # Angela Alsobrooks
    ("ocd-person/befb976c-1369-5d86-a53f-4aeebdf486cc", "S429"),  # Jim Banks
    ("ocd-person/0b32bee9-863e-522f-99b8-9ad8e5d8f42e", "S430"),  # Lisa Blunt Rochester
    ("ocd-person/7cc5139d-8e53-560c-9828-926395e1552d", "S431"),  # John Curtis
    ("ocd-person/256da84c-1b8a-5d48-99ba-9c9f7dd2d310", "S432"),  # Ruben Gallego
    ("ocd-person/c7b45762-ba65-46cd-a8db-cddfe0521cba", "S433"),  # Dave McCormick
    ("ocd-person/a9a4d048-36e2-4f72-a764-5c361593a0d3", "S434"),  # Bernie Moreno
    ("ocd-person/db5da3bd-3690-4c44-9c86-1c66752503c9", "S435"),  # Tim Sheehy
    ("ocd-person/e7ebade8-8c17-50e0-ac00-70e0327b9071", "S436"),  # Elissa Slotkin
    ("ocd-person/2f9a1274-1a6a-4a78-b253-01ec02f20eee", "S437"),  # Jim Justice
    ("ocd-person/caec878c-2749-45e6-99a3-9bf077bf07e7", "S438"),  # Jon Husted
    ("ocd-person/cb582ab6-6a5a-4578-9e44-620c9a6a1f4c", "S439"),  # Ashley Moody
    ("ocd-person/976301a9-cf83-476c-98f0-69577e5b9160", "S440"),  # Alan Armstrong
    ("ocd-person/4c0ef839-19db-4ca7-844c-c863ff4963d2", "S441"),  # Darline Graham
]

PERSON_EXISTS_SQL = "SELECT 1 FROM opencivicdata_person WHERE id = %s"
CHECK_SQL = "SELECT 1 FROM opencivicdata_personidentifier WHERE person_id = %s AND scheme = 'lis'"
INSERT_SQL = """
    INSERT INTO opencivicdata_personidentifier (id, person_id, scheme, identifier)
    VALUES (%s, %s, 'lis', %s)
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing")
    args = parser.parse_args()

    conn = psycopg2.connect(DATABASE_URL) if DATABASE_URL else psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False

    inserted = skipped = missing = 0
    with conn.cursor() as cur:
        for person_id, lis_id in FIXES:
            cur.execute(PERSON_EXISTS_SQL, (person_id,))
            if not cur.fetchone():
                print(f"MISSING PERSON  {person_id} does not exist in this database at all -- skipping")
                missing += 1
                continue
            cur.execute(CHECK_SQL, (person_id,))
            if cur.fetchone():
                print(f"SKIP  {person_id} already has an lis identifier")
                skipped += 1
                continue
            if args.dry_run:
                print(f"WOULD ADD  {person_id} -> lis={lis_id}")
            else:
                cur.execute(INSERT_SQL, (str(uuid.uuid4()), person_id, lis_id))
                print(f"ADDED  {person_id} -> lis={lis_id}")
            inserted += 1

    if args.dry_run:
        print(f"Dry run complete. Would add {inserted}, {skipped} already present, {missing} person not found.")
        conn.rollback()
    else:
        conn.commit()
        print(f"Done. Added {inserted}, {skipped} already present, {missing} person not found.")
    conn.close()


if __name__ == "__main__":
    main()
