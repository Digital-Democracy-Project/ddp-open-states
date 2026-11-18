# REQUEST (waits on Ramon's go): Arizona's 24 stored procedural roll calls stop being labelled passage votes (OPEN-625). 2026-11-18 (Mac side)

**Not a GO.** An addendum to `c7be369`, but **it does not wait for image v67**, because its scraper half is already live. It may run before or after `c7be369`'s parts.

## What and why
* **The problem:** Arizona's old scraper labelled every "failed to pass" roll call a passage vote, including Committee of the Whole motions and motions to reconsider. Since image v65, the scraper (#128, `85df0af5`, live in v65 and v66) labels only Third and Final Reading roll calls, judged from azleg's floor step. The 24 stored ones from before that still carry the old label.
* **The fix:** this run removes `passage` from those 24.
* **Approved:** Ramon, "Approve, go" (OPEN-625, 11-18).
* **The 24:** 21 Committee of the Whole motions to amend, 1 Committee of the Whole vote and 2 reconsider motions (SB 1418, SB 1112).
* **Scorecard effect (OPEN-625's gate, comment 21306):** 0 votes start counting, and 2 stop (the two reconsider motions, neither on a scorecard bill). 0 scorecard entries change.
* **Left alone on purpose:** Arizona's empty 0-0 roll calls (OPEN-433). Ramon, 11-18: "Leave them".

## The list (reviewed, on ddp-open-states main)
* **File:** `notes/open625-az-vote-relabel-dry-run-20261117.csv` (merged with #417). 24 rows plus a header. md5 `4b8981744acb1dc626463b89a553f39b`. Every row is `passage` → nothing.
* **How it was built:** on the Mac, with Arizona's scrape cache (the floor step comes from the cache). The prod host has no cache, so apply the list as given; it cannot be re-planned there.
* **Overlap with the other lists, checked 11-18:**
  * None of these 24 is in OPEN-627's 44-vote results list.
  * All 24 are in OPEN-628's 12,851-vote order list (`c7be369` B2). That list writes a different field (the order key in extras), and each tool's guard checks only its own field, so the two runs don't interfere, in either order.
* **Rehearsed on a throwaway copy of the replica:** the apply wrote 24 and touched only the label. A second dry run found 0; a stale list and a wrong count each aborted with nothing written; `--undo` restored every row.

## Prod agent, after the GO (RDS)
**Gates:**
* No az scrape or import task is running (ECS check).
* `/opt/ddp-open-states` is at or after **`ddc24a72`** (#417); current main `1de8fc5` is fine.
* The list's md5 matches the one above.

**Steps:**
1. **Apply:** `python3 backfill-motion-classification.py --apply-list notes/open625-az-vote-relabel-dry-run-20261117.csv --expect 24 --list <lasting path>/open625-committed.csv`.
   * It is all-or-nothing: a row whose stored label is no longer `passage` aborts the run with nothing written.
   * If it aborts, report the count and the first mismatched row. Do not retry with a different `--expect`.
   * There is no read-only cross-check here: without Arizona's cache the tool cannot re-plan this list on the prod host, so the write's own guard is the check.
2. **Check:** a second apply of the same list aborts or reports 0 to write. Report the committed list's path and row count.
3. **Rollback, only if Ramon asks:** `python3 backfill-motion-classification.py --undo <lasting path>/open625-committed.csv --list <lasting path>/open625-undone.csv`.

## After (read only)
* Report the broker's next Arizona sync.
* Then run the scorecard chain, and `validate_scorecards` and `reconcile_scorecards` for AZ. Expect no scorecard entry to change.

## Not authorized
OPEN-552 (Arizona's action rule, still held behind BROKER-491 and a re-measure), any relabel, extra scrapes, and any other stored-data change.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
