#!/usr/bin/env python3
"""
Backfill voter_id for existing PersonVote records that failed to resolve.

OPEN-2: VoteBot's "Status & votes" button buckets a large share of legislator
votes into "Unknown/Other" because opencivicdata_personvote.voter_id is null.
The root cause (fixed in openstates-core's resolve_person() and
openstates-scrapers' usa/votes.py) was that vote resolution only matched on
case-insensitive exact name string, never on the bioguide/lis_id identifier
the US Congress scraper already captures into the `note` column -- so House
members disambiguated only by a "(ST)" suffix (e.g. "Garcia (CA)") or a
"Last, First" form never matched their stored name/other_names/family_name.

This script re-resolves already-scraped rows using that same note/identifier
value, without re-scraping. It does not touch rows that already have a
voter_id, and it's a pure identifier lookup against PersonIdentifier -- no
name matching, so it can't introduce a *new* wrong match, only fill in ones
the fixed importer would now get right on the next scrape anyway.

Safe to re-run: rows already resolved (by this script or a subsequent
scrape) are excluded by the `voter_id IS NULL` filter.

Usage:
    python3 backfill-vote-person-resolution.py [--dry-run]
"""
import argparse
import os
import sys
from collections import defaultdict

import psycopg2
import psycopg2.extras

DB_CONFIG = {
    "host": os.getenv("OPENSTATES_DB_HOST", "localhost"),
    "port": int(os.getenv("OPENSTATES_DB_PORT", "5433")),
    "dbname": os.getenv("OPENSTATES_DB_NAME", "openstates"),
    "user": os.getenv("OPENSTATES_DB_USER", "openstates"),
    "password": os.getenv("OPENSTATES_DB_PASSWORD", "openstates_dev"),
}

FETCH_NULL_VOTES_SQL = """
    SELECT id, note
    FROM opencivicdata_personvote
    WHERE voter_id IS NULL AND note IS NOT NULL AND note != ''
"""

FETCH_IDENTIFIERS_SQL = """
    SELECT pi.identifier, p.id AS person_id, p.current_role
    FROM opencivicdata_personidentifier pi
    JOIN opencivicdata_person p ON p.id = pi.person_id
"""

UPDATE_SQL = "UPDATE opencivicdata_personvote SET voter_id = %s WHERE id = %s"


def build_identifier_map(cur):
    """identifier value -> list of (person_id, has_current_role), scheme-agnostic

    Mirrors resolve_person()'s Q(identifiers__identifier=...) lookup: it
    doesn't care which scheme (bioguide, lis, ...) supplied the value, only
    that it uniquely names one person.
    """
    cur.execute(FETCH_IDENTIFIERS_SQL)
    id_map = defaultdict(list)
    for identifier, person_id, current_role in cur.fetchall():
        id_map[identifier].append((person_id, current_role is not None))
    return id_map


def resolve(identifier, id_map):
    """Return a person_id if the identifier uniquely resolves, else None.

    Same tie-break as resolve_person(): if more than one person shares an
    identifier value, only resolve if exactly one of them has a current_role.
    """
    candidates = id_map.get(identifier)
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0][0]
    current = [person_id for person_id, has_role in candidates if has_role]
    if len(current) == 1:
        return current[0]
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing")
    args = parser.parse_args()

    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False

    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        id_map = build_identifier_map(cur)
        print(f"Loaded {len(id_map):,} distinct person identifiers.")

        cur.execute(FETCH_NULL_VOTES_SQL)
        rows = cur.fetchall()
        print(f"Found {len(rows):,} unresolved vote records with a usable note/identifier.")

        resolved = ambiguous_or_missing = 0
        updates = []
        for row in rows:
            person_id = resolve(row["note"], id_map)
            if person_id:
                updates.append((person_id, row["id"]))
                resolved += 1
            else:
                ambiguous_or_missing += 1

        if args.dry_run:
            print(f"Dry run complete. Would resolve {resolved:,} records "
                  f"({ambiguous_or_missing:,} still unresolvable).")
        else:
            update_cur = conn.cursor()
            psycopg2.extras.execute_batch(update_cur, UPDATE_SQL, updates, page_size=1000)
            conn.commit()
            print(f"Done. Resolved {resolved:,} records "
                  f"({ambiguous_or_missing:,} still unresolvable).")

    conn.close()


if __name__ == "__main__":
    main()
