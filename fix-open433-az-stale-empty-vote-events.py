#!/usr/bin/env python3
r"""
Delete the stale, empty Arizona vote events that the current scraper no longer
produces, so they stop passing for floor votes.

OPEN-433. Before 2026-07-11 the Arizona scraper turned every action in azleg's
BillStatusFloorAction feed into a VoteEvent, including procedural motions that
carry no recorded vote: "Motion Passed" on a motion to calendar a bill for an
additional Committee of the Whole, a motion to reconsider, a concurrence motion,
a committee-of-the-whole "do pass". Each came out with 0 yes / 0 no, no voters,
and -- because the action text says "Passed" -- the `passage` classification and
result `pass`. Upstream fixed that on 2026-07-11 (openstates-scrapers 497c9ea35,
"don't emit VoteEvents for actions with no recorded vote") and the fork carries
it, so no new empty event is written. The ones already stored stay: the importer
only drops a bill's stored vote events when that bill is scraped again, and an
Arizona session that has adjourned is never scraped again by an incremental run.

Measured on the 2026 session (57th-2nd-regular, 2,190 bills, 3,443 vote events):
1,779 events across 900 bills are such empty events. Every one has the azleg
BillStatusFloorAction source URL, and none has voters. 424 of them are tagged
`passage`, and 393 of those 424 sit in a bill+chamber that also has a real
recorded passage vote -- 255 of them dated AFTER it, which is what the broker's
"latest eligible motion" rule picks. In a live pull of 600 random bills, 504 of
the 508 actions the scraper skips are procedural motions (azleg headers COW,
ADDCOW, CONCUR, MISC, RECON_3RD, RECON_FNL, MOTIONRETURN). The other 4 sit under a
THIRD (third-reading) header: "Passed", UnanimouslyAdopted = true, no roll call --
resolutions adopted by voice (HCR 2053 in both chambers, HR 2008, SCR 1055). Those
are real adoptions with no recorded vote; the scraper drops them like the rest, so a
rescrape would delete their stored rows too, and so does this script (see below).

What this deletes -- exactly the importer's rule, applied once
---------------------------------------------------------------
A vote event of an Arizona session with
  * no vote count other than 0 (or no counts at all), and
  * no voter rows, and
  * no event-related-entity rows, and
  * a BillStatusFloorAction ...includeVotes=true source.
That is the scraper's own skip rule (no Votes[], Ayes == 0, Nays == 0), read off
the stored row. Anything with a single voter or a single non-zero count is left
alone and cannot match.

What it does NOT fix
--------------------
Chambers whose only record of a passage is an empty event lose it: 9 of 392
chambers (2.3%) whose bill actions say PASSED in the 600-bill sample -- 4 voice
adoptions (above) and 5 where azleg's feed has no third-reading vote at all. Nothing
replaces the empty event, and no member-level data is lost (it had none).

A bill whose stored votes are ALL empty events is left with no vote event at all
after this. ddp-broker-py retires a stale Motion only while the bill still
produces some vote candidate ("an empty candidate set means this run learned
nothing"), so for those bills the broker keeps the old Motion rows. The dry run
prints that count; the check after a real run (below) shows whether the broker
caught up. That is a separate broker ticket, not this script's job.

Why the bills' updated_at is bumped
-----------------------------------
The broker's incremental sync selects bills by `updated_since` /
`vote_updated_since`. A deleted vote event can no longer match the second, and
nothing else touches the bill, so without a bump the broker would never look at
these bills again. A rescrape would bump it as a side effect of saving the bill.

Safe to re-run: the predicate is the whole state, so a second run finds nothing.
The script aborts without committing if any DELETE or UPDATE touches a different
number of rows than the SELECT found.

Usage (read the dry run, agree its numbers, then run for real with them):
    python3 fix-open433-az-stale-empty-vote-events.py --dry-run
    python3 fix-open433-az-stale-empty-vote-events.py --session 57th-2nd-regular \
        --expect-events <the dry run's count> --save-dir <dir>

--session names the session(s) to clean (repeatable; required for a real run, so
nothing outside the validated session is touched; the dry run lists every Arizona
session it finds). --expect-events aborts before any write if a fresh count differs
from the dry run you agreed. --save-dir receives, before anything is deleted, the
deleted rows and each touched bill's original updated_at as CSV, so the revert is a
paste. To put everything back, parents first:

    \copy opencivicdata_voteevent from '<dir>/voteevent.csv' csv header
    \copy opencivicdata_votecount from '<dir>/votecount.csv' csv header
    \copy opencivicdata_votesource from '<dir>/votesource.csv' csv header
    create temp table old_ts (id text, updated_at timestamptz);
    \copy old_ts from '<dir>/bill_updated_at.csv' csv header
    update opencivicdata_bill b set updated_at = o.updated_at from old_ts o where b.id = o.id;

Dependent tables (checked against the replica's constraints): only eventrelatedentity,
personvote, votecount and votesource reference a vote event, none with ON DELETE
CASCADE. The predicate excludes events with the first two, and the script deletes the
last two explicitly, so nothing is removed that is not in the saved CSVs.

Before a real run: confirm the host/database it prints is the one api-v3 and the
broker read (the dry run prints it); run the dry run fresh; keep <dir>.
Check after (broker database): Arizona Motion rows with eligible_for_scorecard =
true and no Vote rows, which should fall after the broker's next Arizona sync (what
stays belongs to the bills BROKER-308 describes); on api-v3, the session's vote
event count falls by the number deleted.
"""
import argparse
import collections
import os

import psycopg2

DB_CONFIG = {
    "host": os.getenv("OPENSTATES_DB_HOST", "localhost"),
    "port": int(os.getenv("OPENSTATES_DB_PORT", "5433")),
    "dbname": os.getenv("OPENSTATES_DB_NAME", "openstates"),
    "user": os.getenv("OPENSTATES_DB_USER", "openstates"),
    "password": os.getenv("OPENSTATES_DB_PASSWORD", "openstates_dev"),
}

JURISDICTION_ID = "ocd-jurisdiction/country:us/state:az/government"
FLOOR_ACTION_SOURCE = "https://apps.azleg.gov/api/BillStatusFloorAction?%includeVotes=true%"

STALE_SQL = """
    SELECT ve.id, ve.bill_id, ve.motion_classification, ve.start_date, o.classification,
           s.identifier,
           CASE WHEN EXISTS (SELECT 1 FROM opencivicdata_votecount c WHERE c.vote_event_id = ve.id)
                THEN 'all-zero counts' ELSE 'no count rows' END
    FROM opencivicdata_voteevent ve
    JOIN opencivicdata_legislativesession s ON s.id = ve.legislative_session_id
    JOIN opencivicdata_organization o ON o.id = ve.organization_id
    WHERE s.jurisdiction_id = %(jurisdiction)s
      AND (%(sessions)s::text[] IS NULL OR s.identifier = ANY(%(sessions)s))
      AND NOT EXISTS (
          SELECT 1 FROM opencivicdata_votecount vc
          WHERE vc.vote_event_id = ve.id AND vc.value <> 0)
      AND NOT EXISTS (
          SELECT 1 FROM opencivicdata_personvote pv WHERE pv.vote_event_id = ve.id)
      AND NOT EXISTS (
          SELECT 1 FROM opencivicdata_eventrelatedentity e WHERE e.vote_event_id = ve.id)
      AND EXISTS (
          SELECT 1 FROM opencivicdata_votesource src
          WHERE src.vote_event_id = ve.id AND src.url LIKE %(source)s)
"""

# Per bill and chamber, the dates of the votes that have a real recorded tally,
# for the dry-run breakdown only (never used to decide what to delete).
REAL_PASSAGE_SQL = """
    SELECT ve.bill_id, o.classification, ve.start_date
    FROM opencivicdata_voteevent ve
    JOIN opencivicdata_legislativesession s ON s.id = ve.legislative_session_id
    JOIN opencivicdata_organization o ON o.id = ve.organization_id
    WHERE s.jurisdiction_id = %(jurisdiction)s
      AND 'passage' = ANY(ve.motion_classification)
      AND EXISTS (
          SELECT 1 FROM opencivicdata_votecount vc
          WHERE vc.vote_event_id = ve.id AND vc.value <> 0)
"""

ALL_BILL_VOTES_SQL = """
    SELECT ve.bill_id, ve.id
    FROM opencivicdata_voteevent ve
    WHERE ve.bill_id = ANY(%(bills)s)
"""

COPY_TABLES = (
    ("bill_updated_at", "SELECT id, updated_at FROM opencivicdata_bill WHERE id = ANY(%(bills)s)"),
    ("voteevent", "SELECT * FROM opencivicdata_voteevent WHERE id = ANY(%(ids)s)"),
    ("votecount", "SELECT * FROM opencivicdata_votecount WHERE vote_event_id = ANY(%(ids)s)"),
    ("votesource", "SELECT * FROM opencivicdata_votesource WHERE vote_event_id = ANY(%(ids)s)"),
)

DELETE_COUNTS_SQL = "DELETE FROM opencivicdata_votecount WHERE vote_event_id = ANY(%(ids)s)"
DELETE_SOURCES_SQL = "DELETE FROM opencivicdata_votesource WHERE vote_event_id = ANY(%(ids)s)"
DELETE_EVENTS_SQL = "DELETE FROM opencivicdata_voteevent WHERE id = ANY(%(ids)s)"
BUMP_BILLS_SQL = "UPDATE opencivicdata_bill SET updated_at = now() WHERE id = ANY(%(bills)s)"


def breakdown(stale, real_passage_dates, bill_vote_counts):
    """Counts for the dry run, from rows already fetched.

    :param stale: [(vote_id, bill_id, motion_classification, start_date, chamber, session, count_shape)]
    :param real_passage_dates: {(bill_id, chamber): [start_date, ...]} of real passage votes
    :param bill_vote_counts: {bill_id: number of vote events the bill has now}
    :returns: dict of counters
    """
    out = collections.Counter()
    stale_per_bill = collections.Counter(row[1] for row in stale)
    for _vid, bill_id, classification, start_date, chamber, _session, _shape in stale:
        classification = classification or []
        if "passage" in classification:
            out["passage-tagged"] += 1
            real = real_passage_dates.get((bill_id, chamber), [])
            if not real:
                out["  passage-tagged, no real passage vote in that chamber"] += 1
            elif any(d < start_date for d in real):
                out["  passage-tagged, dated after a real passage vote"] += 1
            else:
                out["  passage-tagged, same day or before a real passage vote"] += 1
        elif "committee-passage" in classification:
            out["committee-passage-tagged"] += 1
        else:
            out["untagged"] += 1
    for row in stale:
        out["session " + row[5]] += 1
        out["count rows: " + row[6]] += 1
    out["bills touched"] = len(stale_per_bill)
    out["bills left with no vote event at all"] = sum(
        1 for b, n in stale_per_bill.items() if bill_vote_counts.get(b, 0) == n
    )
    return out


def save_rows(cur, save_dir, ids, bills):
    os.makedirs(save_dir, exist_ok=True)
    for name, sql in COPY_TABLES:
        path = os.path.join(save_dir, name + ".csv")
        with open(path, "w", encoding="utf-8") as fh:
            cur.copy_expert(
                "COPY ({}) TO STDOUT WITH CSV HEADER".format(cur.mogrify(sql, {"ids": ids, "bills": bills}).decode()),
                fh,
            )
        print("  saved {}".format(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="Print what would change without writing")
    parser.add_argument("--save-dir", help="Directory for the CSV copy of the deleted rows (required unless --dry-run)")
    parser.add_argument(
        "--session", action="append",
        help="Session identifier to clean, e.g. 57th-2nd-regular (repeatable; required unless --dry-run)",
    )
    parser.add_argument(
        "--expect-events", type=int,
        help="Abort before writing if the count found is not this (the dry run's count)",
    )
    args = parser.parse_args()
    if not args.dry_run and not (args.save_dir and args.session and args.expect_events is not None):
        parser.error("a real run needs --save-dir, --session and --expect-events")

    print(
        "fix-open433-az-stale-empty-vote-events -- mode={} db={}@{}:{}/{}".format(
            "DRY RUN" if args.dry_run else "APPLY",
            DB_CONFIG["user"], DB_CONFIG["host"], DB_CONFIG["port"], DB_CONFIG["dbname"],
        )
    )
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    params = {"jurisdiction": JURISDICTION_ID, "source": FLOOR_ACTION_SOURCE, "sessions": args.session}

    with conn.cursor() as cur:
        cur.execute(STALE_SQL, params)
        stale = cur.fetchall()
        print("Found {:,} empty Arizona vote events.".format(len(stale)))
        if not stale:
            print("Nothing to do.")
            conn.close()
            return

        ids = [row[0] for row in stale]
        bills = sorted({row[1] for row in stale})
        if args.expect_events is not None and len(ids) != args.expect_events:
            conn.rollback()
            raise SystemExit(
                "Aborting before any write: found {} events but --expect-events is {}. Re-run the dry run, "
                "read the difference, and agree the new number before going on.".format(len(ids), args.expect_events)
            )

        cur.execute(REAL_PASSAGE_SQL, params)
        real = collections.defaultdict(list)
        for bill_id, chamber, start_date in cur.fetchall():
            real[(bill_id, chamber)].append(start_date)
        cur.execute(ALL_BILL_VOTES_SQL, {"bills": bills})
        per_bill = collections.Counter(bill_id for bill_id, _ in cur.fetchall())

        for label, n in breakdown(stale, real, per_bill).items():
            print("  {:<62}{:>7,}".format(label, n))

        if args.dry_run:
            print("\nDry run complete. Would delete {:,} vote events and touch {:,} bills.".format(len(ids), len(bills)))
            conn.rollback()
            conn.close()
            return

        print("Saving the rows to be deleted:")
        save_rows(cur, args.save_dir, ids, bills)

        cur.execute(DELETE_COUNTS_SQL, {"ids": ids})
        cur.execute(DELETE_SOURCES_SQL, {"ids": ids})
        cur.execute(DELETE_EVENTS_SQL, {"ids": ids})
        deleted = cur.rowcount
        cur.execute(BUMP_BILLS_SQL, {"bills": bills})
        bumped = cur.rowcount
        if deleted != len(ids) or bumped != len(bills):
            conn.rollback()
            raise SystemExit(
                "Aborting without committing: expected to delete {} vote events and touch {} bills but "
                "deleted {} and touched {} -- a row likely changed underneath this script. "
                "Investigate before re-running.".format(len(ids), len(bills), deleted, bumped)
            )
        conn.commit()
        print("\nDone. Deleted {:,} vote events; bumped updated_at on {:,} bills.".format(deleted, bumped))

    conn.close()


if __name__ == "__main__":
    main()
