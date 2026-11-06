# Reply: `recompute-diff-order nc --commit` done on RDS. Every number matched. **Stopped; waiting for your "verified" line before Arizona.** Written 2026-11-06 15:58 UTC.

Run at the user's go ("Yes, run North Carolina now if the gates are clean (Recommended)") under your GO note `9568df0c` and after your Alabama "verified" line `bf64261e`. Nothing else changed: no other state, no refresh, scrape, archive, schedule, restart.

## Gates and restore point (15:53 UTC, immediately before)
No ECS task; nothing in flight; **no ddp-sync job in the last 12 minutes**; the next ddp-sync run is **2026-11-07 00:30 UTC**; North Carolina's own archive day is **Thursday** (today is Friday). Code: the same throwaway worktree, `HEAD` = **`978fa96c49adc3fb6304fccda8237b24caea0cd5`**. **RDS latest restorable time right before the commit: `2026-11-06T15:47:46Z`** (the rollback point; the Alabama one was `15:27:45Z`).

## The run (outputs in `notes/recompute-five-20261106/nc-part2-*-output.txt`)
1. **Dry run first, 15:53:55 UTC**, exit 0, **exactly your Part 1 lines** (my script compared them and would have stopped on any difference): `nc: [DRY RUN] 2343 bills checked | unchanged=6207 corrected=0 nulled=0` and `nc: [DRY RUN] is_bill_version: set=6207 changed=0 not_a_version=54`.
2. **`recompute-diff-order nc --commit`, 15:54:28 UTC**, exit 0, the same numbers: `nc: [COMMITTED] 2343 bills checked | unchanged=6207 corrected=0 nulled=0` and `nc: [COMMITTED] is_bill_version: set=6207 changed=0 not_a_version=54`.
3. **`--dry-run` again, 15:54:50 UTC**, exit 0: `nc: [DRY RUN] 2343 bills checked | unchanged=6207 corrected=0 nulled=0` and `nc: [DRY RUN] is_bill_version: set=0 changed=0 not_a_version=54` (**`corrected=0 nulled=0`, `changed=0`**).
About 55 seconds from the first dry run to the last.

## The G3 query after (15:55 UTC)
| state | docs | flag_null | flag_false | with_diff |
|---|---|---|---|---|
| **North Carolina** | 6,207 | **0** (was 6,207) | **54** (was 0) | **3,557 (unchanged)** |
| Alabama (done earlier) | 2,923 | 0 | 45 | 918 |
| Arizona, Utah, Virginia | 8,935 / 9,371 / 25,591 | unchanged (all null) | 0 | unchanged (4,328 / 4,158 / 14,927) |
`ddp_bill_version_document` total **224,167** (unchanged); **flags set in the whole table 23,035** (16,828 + 6,207, exactly North Carolina's documents); by state: Alabama 2,923, Louisiana 10,468, Massachusetts 44, Nebraska 3,383, **North Carolina 6,207**, United States 10. **Replication (RDS side only):** the slot `ddp_legbot_subscription` is **streaming, lag 0**; the Mac's side is yours.

## What I did not do
Arizona, Utah and Virginia: **not run**; I stop here and wait for a **"verified" line for North Carolina** on this branch (then the user's go for Arizona; Arizona's own archive day is Tuesday). Nothing else was touched.
