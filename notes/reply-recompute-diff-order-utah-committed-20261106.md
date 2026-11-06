# Reply: `recompute-diff-order ut --commit` done on RDS. Every number matched. **Stopped; waiting for your "verified" line before Virginia.** Written 2026-11-06 16:37 UTC.

Run at the user's go ("Yes, run Utah now if the gates are clean (Recommended)") under your GO note `9568df0c` and after your Arizona "verified" line `b83e2477`. Nothing else changed: no other state, no refresh, scrape, archive, schedule, restart.

## Gates and restore point (16:32 UTC, immediately before)
No ECS task; nothing in flight; **no ddp-sync job in the last 12 minutes**; the next ddp-sync run is **2026-11-07 00:30 UTC**; Utah's own archive day is **Monday** (today is Friday). Code: the same throwaway worktree, `HEAD` = **`978fa96c49adc3fb6304fccda8237b24caea0cd5`**. **RDS latest restorable time right before the commit: `2026-11-06T16:27:46Z`** (the rollback point).

## The run (outputs in `notes/recompute-five-20261106/ut-part2-*-output.txt`)
1. **Dry run first, 16:32:35 UTC**, exit 0, **exactly your Part 1 lines** (my script compared them and would have stopped on any difference): `ut: [DRY RUN] 1021 bills checked | unchanged=9371 corrected=0 nulled=0` and `ut: [DRY RUN] is_bill_version: set=9371 changed=0 not_a_version=3170`.
2. **`recompute-diff-order ut --commit`, 16:33:07 UTC**, exit 0, the same numbers: `ut: [COMMITTED] 1021 bills checked | unchanged=9371 corrected=0 nulled=0` and `ut: [COMMITTED] is_bill_version: set=9371 changed=0 not_a_version=3170`.
3. **`--dry-run` again, 16:33:19 UTC**, exit 0: `ut: [DRY RUN] 1021 bills checked | unchanged=9371 corrected=0 nulled=0` and `ut: [DRY RUN] is_bill_version: set=0 changed=0 not_a_version=3170` (**`corrected=0 nulled=0`, `changed=0`**).
About 44 seconds from the first dry run to the last.

## The G3 query after (16:33 UTC)
| state | docs | flag_null | flag_false | with_diff |
|---|---|---|---|---|
| **Utah** | 9,371 | **0** (was 9,371) | **3,170** (was 0) | **4,158 (unchanged)** |
| Alabama, Arizona, North Carolina (done earlier) | 2,923 / 8,935 / 6,207 | 0 / 0 / 0 | 45 / 16 / 54 | 918 / 4,328 / 3,557 |
| Virginia | 25,591 | unchanged (all null) | 0 | unchanged (14,927) |
`ddp_bill_version_document` total **224,167** (unchanged); **flags set in the whole table 41,341** (31,970 + 9,371, exactly Utah's documents); by state: Alabama 2,923, Arizona 8,935, Louisiana 10,468, Massachusetts 44, Nebraska 3,383, North Carolina 6,207, United States 10, **Utah 9,371**. **Replication (RDS side only):** the slot `ddp_legbot_subscription` is **streaming, lag 0**; the Mac's side is yours.

## What I did not do
Virginia: **not run**; I stop here and wait for a **"verified" line for Utah** on this branch (then the user's go for Virginia, the last of the five; Virginia's own archive day is **Wednesday**; at 25,591 rows it is the biggest, about 2.7 times Utah). Nothing else was touched.
