#!/usr/bin/env python3
"""
Fix Washington Senate votes misattributed to the wrong same-surname House member.

OPEN-113, found by OPEN-111's cross-jurisdiction audit for the OPEN-110/OPEN-112
misattribution shape. Two unrelated Washington same-surname pairs, both Senate
("upper") roll calls:

- 1,101 opencivicdata_personvote rows carry voter_name="Cortes" but voter_id
  pointing to Julio Cortes (ocd-person/0805e7bc-f274-4f20-81b4-e8e86951eaba),
  a WA House member -- Julio has never held any upper-chamber ("upper")
  membership at all, so no Senate vote can legitimately be his. The real voter
  is Adrian Cortes (ocd-person/3f71f11c-c231-4661-af2a-629d2eb32580), WA
  Senate since 2025-01-13.
- 1,101 rows carry voter_name="Valdez" but voter_id pointing to Michelle Valdez
  (ocd-person/fdd79a57-f6f9-4435-84f6-92708c65b716), a WA House member since
  2015 who has likewise never held an upper-chamber membership. The real voter
  is Javier Valdez (ocd-person/aba2c522-236c-4553-bda2-c02d72e79981), WA
  Senate since 2017.

Both groups share an identical row count (1,101) and date range (2025-02-05 to
2026-03-12) -- strong evidence both trace to the same underlying incident
(very likely one or a few WA Senate bulk-import runs where the OPEN-112
cache-bleed bug fired for both surname collisions in the same run), not two
independent problems. Confirmed via a live call to the current (OPEN-112-fixed)
resolve_person() against this exact data that it resolves each surname to the
Senate member, not the House member, for these jurisdiction/chamber/session
parameters.

Establishing that the WRONG person (Julio, Michelle) never held an
upper-chamber membership only proves the current attribution is wrong; it
doesn't by itself prove the proposed correct person is right for every
specific row. So this script also positively verifies, per row and at write
time (not just once during investigation), that the correct person actually
held an 'upper' membership in this jurisdiction on that row's own vote date
(see verify_correct_person_eligible below) -- the same date-anchored standard
used in OPEN-116's blank-voter_id backfill in this same batch. Any row that
doesn't verify is left alone and reported separately, never repointed on
the strength of "the wrong person couldn't have done it" alone.

Confirmed no row-level conflicts as of this investigation pass: none of the
affected vote_events already have a row for the correct (Senate) person, which
would make re-pointing create a duplicate voter on one roll call. The script
re-checks this itself immediately before writing rather than relying solely on
this investigation, in case the replica has changed since.

Both pairs are fully validated (fetched, eligibility-checked, duplicate-
checked) before either is written -- a failure partway through validating the
second pair aborts before any write happens for either, rather than leaving
one pair committed and the other not.

Safe to re-run: each WHERE clause matches only rows still pointing at the wrong
person, so already-fixed rows are excluded on a second run. The UPDATE also
re-checks voter_id at write time (not just id), and the script aborts without
committing if the number of rows actually updated doesn't match the number
expected to be updated -- both guard against a row changing underneath this
script between validation and the write.

NOT YET RUN FOR REAL as of this PR -- dry-run only, pending review (OPEN-113).

Usage:
    python3 fix-open113-wa-cortes-valdez-vote-misattribution.py [--dry-run]
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

WA_JURISDICTION_ID = "ocd-jurisdiction/country:us/state:wa/government"

# Each pair: (surname as recorded in voter_name, wrong House-member id, correct
# Senate-member id, human label for logging).
PAIRS = [
    (
        "Cortes",
        "ocd-person/0805e7bc-f274-4f20-81b4-e8e86951eaba",  # Julio Cortes (House)
        "ocd-person/3f71f11c-c231-4661-af2a-629d2eb32580",  # Adrian Cortes (Senate)
        "Julio Cortes -> Adrian Cortes",
    ),
    (
        "Valdez",
        "ocd-person/fdd79a57-f6f9-4435-84f6-92708c65b716",  # Michelle Valdez (House)
        "ocd-person/aba2c522-236c-4553-bda2-c02d72e79981",  # Javier Valdez (Senate)
        "Michelle Valdez -> Javier Valdez",
    ),
]

FETCH_SQL = """
    SELECT pv.id, ve.id, ve.start_date::date
    FROM opencivicdata_personvote pv
    JOIN opencivicdata_voteevent ve ON ve.id = pv.vote_event_id
    JOIN opencivicdata_organization o ON o.id = ve.organization_id
    JOIN opencivicdata_legislativesession ls ON ls.id = ve.legislative_session_id
    WHERE ls.jurisdiction_id = %s
      AND o.classification = 'upper'
      AND pv.voter_name = %s
      AND pv.voter_id = %s
"""

# Date-anchored: did the correct person actually hold an 'upper' membership in
# this jurisdiction on this exact vote date? (Not "currently" -- on that date.)
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

# A row here would mean re-pointing the wrong person's row to the correct person
# would create a second voter for that person on the same roll call -- abort
# rather than risk that, even though the investigation found none of these as
# of its last pass.
DUPLICATE_CHECK_SQL = """
    SELECT 1 FROM opencivicdata_personvote other
    WHERE other.vote_event_id = %s AND other.voter_id = %s
"""

UPDATE_SQL = "UPDATE opencivicdata_personvote SET voter_id = %s WHERE id = %s AND voter_id = %s"


def validate_pair(cur, surname, wrong_id, correct_id, label):
    """Fetch + eligibility-check + duplicate-check one pair. Returns
    (fillable, not_eligible, duplicate) -- no writes."""
    cur.execute(FETCH_SQL, (WA_JURISDICTION_ID, surname, wrong_id))
    rows = cur.fetchall()
    print(f"[{label}] Found {len(rows):,} Washington Senate vote records "
          f"currently misattributed to {wrong_id}.")

    fillable, not_eligible, duplicate = [], [], []
    for pv_id, ve_id, vote_date in rows:
        cur.execute(
            ELIGIBILITY_SQL, (correct_id, WA_JURISDICTION_ID, str(vote_date), str(vote_date))
        )
        if not cur.fetchone():
            not_eligible.append(pv_id)
            continue
        cur.execute(DUPLICATE_CHECK_SQL, (ve_id, correct_id))
        if cur.fetchone():
            duplicate.append(pv_id)
            continue
        fillable.append(pv_id)

    if not_eligible:
        print(f"[{label}] Leaving {len(not_eligible)} row(s) alone -- {correct_id} did not "
              f"hold an 'upper' seat on that row's own vote date: {not_eligible}")
    if duplicate:
        print(f"[{label}] Leaving {len(duplicate)} row(s) alone -- would create a duplicate "
              f"voter on their vote_event: {duplicate}")
    return fillable


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing")
    args = parser.parse_args()

    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False

    with conn.cursor() as cur:
        # Validate both pairs fully before writing anything, so a problem
        # found while validating the second pair can't leave the first
        # pair's writes committed with the second never attempted.
        validated = [
            (label, correct_id, wrong_id, validate_pair(cur, surname, wrong_id, correct_id, label))
            for surname, wrong_id, correct_id, label in PAIRS
        ]

        if args.dry_run:
            for label, correct_id, _wrong_id, fillable in validated:
                print(f"[{label}] Dry run complete. Would re-point {len(fillable):,} records "
                      f"to {correct_id}.")
        else:
            update_cur = conn.cursor()
            for label, correct_id, wrong_id, fillable in validated:
                updated = 0
                for row_id in fillable:
                    update_cur.execute(UPDATE_SQL, (correct_id, row_id, wrong_id))
                    updated += update_cur.rowcount
                if updated != len(fillable):
                    conn.rollback()
                    raise SystemExit(
                        f"[{label}] Aborting without committing anything: expected to "
                        f"update {len(fillable)} rows but only {updated} matched at write "
                        f"time -- a row likely changed underneath this script. Investigate "
                        f"before re-running."
                    )
                print(f"[{label}] Re-pointed {updated:,} records to {correct_id}.")
            conn.commit()
            print("Done. Committed both pairs.")

    conn.close()


if __name__ == "__main__":
    main()
