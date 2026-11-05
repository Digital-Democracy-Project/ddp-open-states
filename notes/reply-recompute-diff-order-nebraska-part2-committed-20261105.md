# Reply: `recompute-diff-order ne --commit` done on RDS. Every number matched. Louisiana was not touched. Written 2026-11-05 02:20 UTC.

Run at the user's go in this session ("Yes, run it now if the gates are clean (Recommended)", about 02:15 UTC), under your GO note `5c43ad8` (Nebraska only). Nothing else changed: no other state, no Louisiana, no refresh, no scrape, archive, flag, schedule or restart.

## Gates and restore point (02:16 UTC, immediately before)
No ECS task; nothing in flight (empty in-flight key); no ddp-sync job in the last 10 minutes; the scheduler's next run is 02:30 UTC, so the whole run finished **13 minutes before it**. Code: the same throwaway worktree, `HEAD` = **`978fa96c49adc3fb6304fccda8237b24caea0cd5`** (re-read at 02:16). **RDS latest restorable time read right before the commit: `2026-11-05T02:12:48Z`** (the Part 1 reading was `00:57:45Z`; the new one is the rollback point for this commit).

## The run, in your order (outputs in `notes/recompute-ne-la-20261105/ne-part2-*-output.txt`)
1. **Dry run first, 02:16:34 UTC**, exit 0, **identical to the Part 1 lines** (my script compared them and would have stopped on any difference):
   `ne: [DRY RUN] 1847 bills checked | unchanged=1955 corrected=637 nulled=790`
   `ne: [DRY RUN] is_bill_version: set=3382 changed=0 not_a_version=790`
2. **`recompute-diff-order ne --commit`, 02:16:52 UTC**, exit 0, **the same numbers**:
   `ne: [COMMITTED] 1847 bills checked | unchanged=1955 corrected=637 nulled=790`
   `ne: [COMMITTED] is_bill_version: set=3382 changed=0 not_a_version=790`
3. **`--dry-run` again, 02:17:01 UTC**, exit 0:
   `ne: [DRY RUN] 1847 bills checked | unchanged=3382 corrected=0 nulled=0`
   `ne: [DRY RUN] is_bill_version: set=0 changed=0 not_a_version=790`
   **`corrected=0 nulled=0`**, as required (every document now unchanged; no flag left to set).
Total about 27 seconds from the first dry run to the last.

## The G3 query after (02:17 UTC), against the Part 1 baseline
| state | docs | flag_null | flag_false | with_diff |
|---|---|---|---|---|
| **Nebraska** | 3,382 | **0** (was 3,382) | **790** (was 0) | **745** (was 1,535: **down 790**) |
| Louisiana | 10,468 | 10,468 | 0 | 7,772 (unchanged) |
`ddp_bill_version_document` total **224,112** (unchanged). **Flags set anywhere in the table: 3,382, all Nebraska** (the query by state lists only Nebraska), so no other state and not Louisiana was touched.

## Replication (RDS side only)
At 02:17 UTC the slot `ddp_legbot_subscription` is **active, streaming, lag 0 bytes**. The Mac's apply worker, its Postgres log and the 790 / 0 counts on the replica are yours to check, as you said.

## What I did not do
Louisiana (needs its own GO note), any other state, `recompute-diff-order all`, `ma --commit`, a search refresh, anything on ddp-sync or the broker. The throwaway worktree (job scratch `o486/wt`) is still there for Louisiana's Part 2; it can be removed afterwards. Rollback was not needed; the restore point is `2026-11-05T02:12:48Z` (a point-in-time restore, not a hand undo, as your note says).
