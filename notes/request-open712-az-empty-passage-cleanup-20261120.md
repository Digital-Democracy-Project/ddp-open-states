# REQUEST: Arizona's 419 empty votes labelled "passage" lose that label (OPEN-712). Ramon's GO: "Yes, run it now", 2026-11-20 (OPEN-712 comment 22032). 2026-11-20 (Mac side)

**What this is.** 419 stored Arizona votes (2026, 57th Legislature 2nd Regular Session) are labelled `passage` but have **no member names and a 0-0 tally**.
* They are procedural voice votes and summary lines (motions to reconsider or return a bill, concurrence lines), stored before July's scraper fix. Today's scraper never emits them, so no re-scrape reaches them.
* This removes the `passage` label only. Nothing is deleted, and no other label changes.
* It must run **before** Arizona's scorecard switch (BROKER-491, broker #789, which has **no** go yet). Ramon approved running it now, on its own.

**Effect on the site:** none expected. On a throwaway broker copy with all 2,188 Arizona bills re-imported, this cleanup under today's rule changed no scorecard position, tally or score; only which merged same-day motion's internal id is shown differs. Votes that keep `passage` include SB 1763's two real roll calls (32-18 and 29-1), which have tallies but no stored names.

## Gates
* `/opt/ddp-open-states` is at or after **`629d26fd`** (ddp-open-states #438, merged: `--az-empty-passage`). `git pull` if behind. No image is involved; this is a host script.
* No Arizona scrape or import task is running (ECS check). A running one is harmless to the write, but it can make the counts disagree.

## Steps
**List:** `notes/open712-az-empty-passage-list-20261120.csv`, on this branch: 419 rows, md5 `5f9032f73dd3bc443bd4206ee937666e`. Every row is `old` = `passage`, `new` = (none), `field` = `motion_classification`. It was built from the Mac replica of RDS with the same command as step 1.

1. **Read-only cross-check on RDS:** `python3 backfill-motion-classification.py --az-empty-passage --dry-run --list <lasting path>/open712-rds-dry-run.csv`
   * Expect **419**, and **exactly the list's ids**: `diff <(cut -d, -f1 notes/open712-az-empty-passage-list-20261120.csv | sort) <(cut -d, -f1 <lasting path>/open712-rds-dry-run.csv | sort)` prints nothing.
   * Any other count, or any id difference, means rows changed since the list was made: **stop and report** (the count, and the differing ids). Do not apply.
2. **Apply:** `python3 backfill-motion-classification.py --apply-list notes/open712-az-empty-passage-list-20261120.csv --expect 419 --list <lasting path>/open712-committed.csv`
   * It is all-or-nothing: a row whose stored label is no longer `passage` aborts the run with nothing written. Do not retry with a different `--expect`.
3. **Check (read only):**
   * Re-run step 1's dry run into a new file and expect **0** to change.
   * Then this query on RDS returns **0** (today on the Mac replica it returns 419). This is the first of the three checks broker #789 needs before Arizona's switch:
     ```sql
     SELECT count(*) FROM opencivicdata_voteevent v JOIN opencivicdata_legislativesession s ON s.id = v.legislative_session_id
      WHERE s.jurisdiction_id = 'ocd-jurisdiction/country:us/state:az/government' AND 'passage' = ANY(v.motion_classification)
        AND NOT EXISTS (SELECT 1 FROM opencivicdata_personvote pv WHERE pv.vote_event_id = v.id)
        AND NOT EXISTS (SELECT 1 FROM opencivicdata_votecount c WHERE c.vote_event_id = v.id
                        AND c.option IN ('yes', 'no') AND c.value > 0);
     ```
4. **Rollback, only if Ramon asks:** `python3 backfill-motion-classification.py --undo <lasting path>/open712-committed.csv --expect 419 --list <lasting path>/open712-undone.csv`. Then the query in step 3 returns 419 again.

**Rehearsed on the Mac** on a throwaway Arizona-only copy of the replica: the dry run gave the same list; `--expect 420` was refused with nothing written; apply wrote 419 and the check read 0; a second apply was refused; a re-plan found 0; undo restored 419.

## Report back
The step 1 count and the id diff (empty), the committed count, the step 3 results (0 and 0), the lasting path of the committed list, and the time (UTC).

## Not authorized
* Arizona's scorecard switch (BROKER-491, broker #789, migration 0107): it waits on its own go, after OPEN-627, OPEN-628 and this cleanup are live and the list is re-measured.
* OPEN-627's and OPEN-628's backfills: they are already requested separately (`c7be369`) and are not part of this note.
* Rebuilding or editing the list on the prod host.
* Any scrape, re-import, manifest, ddp-sync or api-v3 change.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
