# REQUEST (waits on Ramon's go, and on the merges and image below): store the same-day vote order on 12,851 stored WA, MI, VA and AZ votes (OPEN-628). 2026-11-18 (Mac side)

**Not a GO.** The prod agent's part starts only after a GO note that names it. Ramon is approving OPEN-628's scorecard gate (PM session, 11-18). Until he does, scrapers #129 and ddp-open-states #420 stay unmerged.

## What and why
* **What:** each stored vote in Washington, Michigan, Virginia and Arizona gets the extras key `house-rollcall-num` or `senate-rollcall-num`, which the broker reads into `Motion.rollcall_num`.
* **Why:** the broker's scorecard builders order a bill's same-day votes in one chamber by that number. These four states store a vote's day without its time, so a re-vote after reconsideration could sort before the vote it replaced.
* **The worked case:** Michigan HB 4079's House roll calls #45 then #47. With BROKER-525 (#759) and without this key, the scorecard shows #45, the vote that was reconsidered.
* **What the key holds per state:**
  * MI: the journal roll-call number.
  * WA: `SequenceNumber`, that chamber's order for the day.
  * VA and AZ: the time of day as HHMMSS. For these two it is used only to order votes, never shown as a roll-call number.
* **Ticket:** OPEN-628, comment 21415.

## Before the GO (not the prod agent's steps)
1. Ramon approves; scrapers #129 and ddp-open-states #420 are merged. Since #420's `5bc858f9`, ddp-open-states `main` carries `backfill-vote-rollcall-num.py`.
2. **A scrapers image carrying #129** is registered, so new votes are written with the key. Until then a re-scrape cannot undo this, because a scrape never re-imports an old roll call, but new votes still arrive without the key.
3. The Mac side re-checks the list below on the Mac replica just before the GO, and posts a fresh list if anything changed.

## The list (reviewed, attached on this branch)
* **File:** `notes/open628-vote-rollcall-num-list-20261118.csv`, md5 `ce2344aa401b9f6ac531feee3ff148e7`. 12,851 rows plus a header: `id,jurisdiction,bill,date,chamber,motion_text,key,rollcall_num`.
* **Per state:** AZ 3,411, MI 937, VA 6,201, WA 2,302.
* **How it was built:** a read-only dry run on the Mac replica, 2026-11-18.
  * AZ times come from the Mac scrape cache.
  * VA times come from LIS answers read one bill at a time.
  * The prod host has neither source, so production applies this list as given; it does not rebuild it.
* **What it leaves alone:** 5,352 Virginia votes are the only vote that day in their chamber, so their order never matters, and they get the key on their next scrape. A vote that already has a number is never changed.
* **Rehearsed on a throwaway copy of the replica:**
  * `--expect 12850` aborted with nothing written;
  * the apply wrote 12,851, and a second apply was refused;
  * `--undo` restored the copy byte-identical (checksum over all 48,731 votes in the four states);
  * a re-apply worked.

## Prod agent, after the GO (RDS)
**Gates (stop and report if any fails):**
* **Nothing in flight:** no scrape or import task for wa, mi, va or az is running (ECS check). One running during the write could add a vote the list doesn't know; that is harmless but makes the counts disagree.
* `/opt/ddp-open-states` is at or after `5bc858f9`.
* The list's md5 matches the one above.

**Steps:**
1. **Read-only cross-check on RDS:** `python3 backfill-vote-rollcall-num.py --dry-run`, with no `--az-cache` or `--va-votes`.
   * Without those sources it can read only MI and WA. Expect **mi `house-` + `senate-rollcall-num` 937** and **wa 2,302** (the list's own counts). AZ and VA show as "not readable", as intended.
   * A small surplus is new votes imported after the list; report it and continue. A shortfall means rows changed: stop and report.
   * Note: `--apply-list` with `--dry-run` only counts the list's rows and does not compare them with the database, so it is not this check.
2. **Apply:** `python3 backfill-vote-rollcall-num.py --apply-list notes/open628-vote-rollcall-num-list-20261118.csv --expect 12851 --list <lasting path>/open628-committed.csv`.
   * Every write is guarded. Any row that no longer matches the list, because it gained a number or holds another one, aborts the run with nothing written. **If it aborts, report the counts and the first mismatched row; do not retry with a different `--expect`.**
3. **Check:** a second apply of the same list is refused, or reports 0 to write. Report the committed list's path and row count.
4. **Rollback (only if Ramon asks):** `--undo <lasting path>/open628-committed.csv --expect 12851 --list <lasting path>/open628-undone.csv`.

## After (in later reports, read only)
* The broker's next scheduled sync of each state stores `Motion.rollcall_num`. Report the first sync for each of wa, mi, va and az after the apply.
* **Then BROKER-525 (#759) may be merged and deployed** (Ramon: "Merge after the vote-time fix"). After its deploy: the scorecard chain, then `validate_scorecards` and `reconcile_scorecards` for the four states. Michigan HB 4079's House entry should show roll call #47, with a bill score of 54.55.

## Not authorized
Any other stored-data change (relabels, Arizona's OPEN-625 list), extra scrapes, any broker or ddp-sync change, and changing or regenerating the list on the prod host.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
