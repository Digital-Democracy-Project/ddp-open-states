# REQUEST (each part waits on Ramon's go): scrapers image v67 with OPEN-627 and OPEN-628, then two stored-vote fixes (Arizona results: 44 votes; same-day vote order: 12,851 votes), then BROKER-525. 2026-11-18 (Mac side)

**Not a GO.** Three parts, in this order. Each starts only after a GO note that names it. This note **replaces `094331c`** for OPEN-628 (its steps are repeated here, unchanged, against the new image).

Ramon approved both scorecard gates on 2026-11-18 (/ask-me: OPEN-627 "Approve, go"; OPEN-628 "Approve, go"; ticket comments 21450 and 21451). Both pairs of PRs are merged.

## Part A: image v67 (Ramon builds and pushes it; then it is registered)
**What v67 adds over v66** (`ddp-scrapers:69`, scrapers `4686b774`, core `94082df`):
| Repo | Commit | Ticket | Change | What anyone would notice |
|---|---|---|---|---|
| openstates-scrapers | `78df858a` (#129) | OPEN-628 | Virginia and Arizona votes carry an order key (`house-` / `senate-rollcall-num`): the vote's time of day as HHMMSS. Michigan's and Washington's keys (already written) are pinned by tests | New VA/AZ votes come out in the right order when a chamber votes twice on a bill in one day |
| openstates-scrapers | `7fa39511` (#130) | OPEN-627 | Arizona's vote `result` is azleg's own outcome ("failed to pass" is a fail even with more yeas than nays), and the chamber majority is used only when the text says neither | New Arizona failed readings are stored as failed, not passed |

* **Expected:** scrapers **`7fa395112`**, core **`94082df4`** (unchanged from v66), built from ddp-open-states main **`1de8fc5`** or later (it carries the two fix-up tools, #420 and #421).
* **No core change, so no migration and no api-v3 rebuild.** `check-core-pin-drift.py` still reports the known gap with api-v3 at `46cc5759`; that is expected.
* **Register only when no scrape task is running** (ECS check), as for v66.
* **Check:** the next task reports the new revision (70 if nothing else is registered first) and image v67. Report the first wa, mi, va and az runs on it, with their status and failed count.
* **Why this comes first:** a re-import on the old image would write "pass" back onto Arizona's fixed votes. New votes from the old image also lack the order key.

## Part B: the two stored-vote fixes (after Part A, each on its own GO)
**Gates for both:**
* No scrape or import task for wa, mi, va or az is running (ECS check). One running during the write is harmless, but it can make the counts disagree.
* `/opt/ddp-open-states` is at or after **`1de8fc5`**.

### B1. Arizona results (OPEN-627): 44 votes
* **List:** `notes/open627-az-vote-result-dry-run-20261118.csv`, on ddp-open-states **main** (merged with #421), 44 rows, md5 `d7c88dbf0cf293b4b56c3d2bd59fa9bb`. Each row is a "failed to pass" vote stored as "pass", going to "fail". A `-checked` copy has each vote's azleg link.
1. **Read-only cross-check on RDS:** `python3 backfill-motion-classification.py --result --dry-run --list <lasting path>/open627-rds-dry-run.csv`. It needs no cache, because the stored motion text is azleg's answer.
   * Expect **44**, the same 44 vote ids as the list.
   * A different count means rows changed since the list was made: stop and report.
2. **Apply:** `python3 backfill-motion-classification.py --apply-list notes/open627-az-vote-result-dry-run-20261118.csv --expect 44 --list <lasting path>/open627-committed.csv`. It is all-or-nothing: a row that no longer matches aborts the run with nothing written. Do not retry with a different `--expect`.
3. **Check:** re-run step 1's dry run and expect **0**.
4. **Rollback, only if Ramon asks:** `--undo <lasting path>/open627-committed.csv --list <lasting path>/open627-undone.csv`.
* **Effect:** no vote starts or stops counting; eligibility never reads `result`. It fixes what pages and scorecards show.

### B2. Same-day vote order (OPEN-628): 12,851 votes
* **List:** `notes/open628-vote-rollcall-num-list-20261118.csv`, on this branch, md5 `ce2344aa401b9f6ac531feee3ff148e7`. 12,851 rows: AZ 3,411, MI 937, VA 6,201, WA 2,302. It was built on the Mac, where the Arizona cache and the Virginia LIS answers are; the prod host has neither, so apply the list as given and do not rebuild it.
1. **Read-only cross-check on RDS:** `python3 backfill-vote-rollcall-num.py --dry-run`, with no `--az-cache` or `--va-votes`.
   * Without those it can read only MI and WA. Expect **mi 937** and **wa 2,302** across the house and senate keys; AZ and VA show as "not readable", as intended.
   * A small surplus is new votes since the list; report it and continue. A shortfall means rows changed: stop and report.
2. **Apply:** `python3 backfill-vote-rollcall-num.py --apply-list notes/open628-vote-rollcall-num-list-20261118.csv --expect 12851 --list <lasting path>/open628-committed.csv`. It is all-or-nothing, never changes a stored number, and never touches `updated_at`. If it aborts, report the counts and the first mismatched row.
3. **Check:** a second apply of the same list is refused, or reports 0 to write.
4. **Rollback, only if Ramon asks:** `--undo <lasting path>/open628-committed.csv --expect 12851 --list <lasting path>/open628-undone.csv`.
* B1 and B2 are independent (different columns, different tools) and may go in either order.

## Part C: after B2 (read only, then a broker release on its own GO)
1. The broker's next scheduled sync of each of wa, mi, va and az stores `Motion.rollcall_num`. Report the first one for each.
2. **Then BROKER-525** (ddp-broker-py #759) may be merged and released through `/broker-deploy` (Ramon: "Merge after the vote-time fix"). After its deploy: the scorecard chain, then `validate_scorecards` and `reconcile_scorecards` for the four states. **Michigan HB 4079's House entry must show roll call #47 and a bill score of 54.55.**

## Not authorized
* OPEN-625's 24-vote Arizona relabel: not part of this request; it needs its own request and go.
* Any `os-text-extract relabel`.
* Changing or rebuilding either list on the prod host.
* Extra scrapes, any manifest, ddp-sync or api-v3 change.
* The ddp-sync rebuild (SYNC-180): a separate request.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
