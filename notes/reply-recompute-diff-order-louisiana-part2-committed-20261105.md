# Reply: `recompute-diff-order la --commit` done on RDS. Every number matched. Nebraska was not touched again. Written 2026-11-05 03:35 UTC.

Run at the user's go in this session ("Yes, run it now if the gates are clean (Recommended)", about 03:29 UTC), under your GO note `3ded2c6e` (Louisiana only). Nothing else changed: no other state, no refresh, no scrape, archive, flag, schedule or restart.

## Gates and restore point (03:30 UTC, immediately before)
No ECS task; nothing in flight; no ddp-sync job in the last 10 minutes (the last ran at 03:00 UTC, the people pull and the USA scrape; the next is **05:00 UTC**, so the run finished 88 minutes before it). Code: the same throwaway worktree, `HEAD` = **`978fa96c49adc3fb6304fccda8237b24caea0cd5`** (re-read at 03:30). **RDS latest restorable time read right before the commit: `2026-11-05T03:22:45Z`**, the rollback point for this commit.

## The run, in your order (outputs in `notes/recompute-ne-la-20261105/la-part2-*-output.txt`)
1. **Dry run first, 03:31:01 UTC**, exit 0, **identical to the Part 1 lines** (my script compared them and would have stopped on any difference):
   `la: [DRY RUN] 2599 bills checked | unchanged=6318 corrected=919 nulled=3231`
   `la: [DRY RUN] is_bill_version: set=10468 changed=0 not_a_version=3328`
2. **`recompute-diff-order la --commit`, 03:31:33 UTC**, exit 0, **the same numbers**:
   `la: [COMMITTED] 2599 bills checked | unchanged=6318 corrected=919 nulled=3231`
   `la: [COMMITTED] is_bill_version: set=10468 changed=0 not_a_version=3328`
3. **`--dry-run` again, 03:31:44 UTC**, exit 0:
   `la: [DRY RUN] 2599 bills checked | unchanged=10468 corrected=0 nulled=0`
   `la: [DRY RUN] is_bill_version: set=0 changed=0 not_a_version=3328`
   **`corrected=0 nulled=0`**, as required. About 43 seconds from the first dry run to the last.

## The G3 query after (03:31 UTC)
| state | docs | flag_null | flag_false | with_diff |
|---|---|---|---|---|
| **Louisiana** | 10,468 | **0** (was 10,468) | **3,328** (was 0) | **4,541** (was 7,772: **down 3,231**) |
| Nebraska | 3,382 | 0 | 790 | 745 (unchanged since its commit) |
All as your note expects (Louisiana 3,328 / 0 / 4,541; Nebraska 790 / 745).

## One thing outside this commit that you should know
`ddp_bill_version_document` now has **224,120 rows (it was 224,112), and flags set on 13,858 = Louisiana 10,468 + Nebraska 3,382 + 8 for the United States.** **The 8 United States rows are not from this commit** (it only wrote Louisiana; the dry-run lines say so, and Nebraska's numbers did not move). They are **8 new federal documents saved after my Nebraska reply**: the USA scrape ran at 03:00 UTC (loaded into RDS at 03:02:45) and the scrape-triggered archive saved them, and **they already carry the flag**. My reading (not verified: I did not look at which task-definition revision that archive ran): the archive picked up the new scrapers image you registered this evening, which sets `is_bill_version` on new rows. Nothing was changed for them.

## Replication (RDS side only)
At 03:31 UTC the slot `ddp_legbot_subscription` is **active, streaming, lag 0 bytes**. The Mac's apply worker, its Postgres log and the 3,328 / 0 counts there are yours to check, as you said.

## What I did not do
Any other state, `recompute-diff-order all`, `ma --commit`, a search refresh, anything on ddp-sync or the broker. The throwaway worktree (job scratch `o486/wt`) can be removed now. Rollback was not needed; the restore point is `2026-11-05T03:22:45Z` (a point-in-time restore, not a hand undo).
