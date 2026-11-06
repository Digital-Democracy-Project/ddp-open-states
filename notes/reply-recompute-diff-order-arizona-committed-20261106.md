# Reply: `recompute-diff-order az --commit` done on RDS. Every number matched. **Stopped; waiting for your "verified" line before Utah.** Written 2026-11-06 16:28 UTC.

Run at the user's go ("Yes, run Arizona now if the gates are clean (Recommended)") under your GO note `9568df0c` and after your North Carolina "verified" line `e73e64fb`. Nothing else changed: no other state, no refresh, scrape, archive, schedule, restart. **Arizona's 17 approved summaries on procedural papers were not touched** (not asked).

## Gates and restore point (16:23 UTC, immediately before)
No ECS task; nothing in flight; **no ddp-sync job in the last 12 minutes**; the next ddp-sync run is **2026-11-07 00:30 UTC**; Arizona's own archive day is **Tuesday** (today is Friday). Code: the same throwaway worktree, `HEAD` = **`978fa96c49adc3fb6304fccda8237b24caea0cd5`**. **RDS latest restorable time right before the commit: `2026-11-06T16:17:46Z`** (the rollback point).

## The run (outputs in `notes/recompute-five-20261106/az-part2-*-output.txt`)
1. **Dry run first, 16:23:56 UTC**, exit 0, **exactly your Part 1 lines** (my script compared them and would have stopped on any difference): `az: [DRY RUN] 2190 bills checked | unchanged=8935 corrected=0 nulled=0` and `az: [DRY RUN] is_bill_version: set=8935 changed=0 not_a_version=16`.
2. **`recompute-diff-order az --commit`, 16:24:39 UTC**, exit 0, the same numbers: `az: [COMMITTED] 2190 bills checked | unchanged=8935 corrected=0 nulled=0` and `az: [COMMITTED] is_bill_version: set=8935 changed=0 not_a_version=16`.
3. **`--dry-run` again, 16:25:05 UTC**, exit 0: `az: [DRY RUN] 2190 bills checked | unchanged=8935 corrected=0 nulled=0` and `az: [DRY RUN] is_bill_version: set=0 changed=0 not_a_version=16` (**`corrected=0 nulled=0`, `changed=0`**).
About 69 seconds from the first dry run to the last.

## The G3 query after (16:25 UTC)
| state | docs | flag_null | flag_false | with_diff |
|---|---|---|---|---|
| **Arizona** | 8,935 | **0** (was 8,935) | **16** (was 0) | **4,328 (unchanged)** |
| Alabama, North Carolina (done earlier) | 2,923 / 6,207 | 0 / 0 | 45 / 54 | 918 / 3,557 |
| Utah, Virginia | 9,371 / 25,591 | unchanged (all null) | 0 | unchanged (4,158 / 14,927) |
`ddp_bill_version_document` total **224,167** (unchanged); **flags set in the whole table 31,970** (23,035 + 8,935, exactly Arizona's documents); by state: Alabama 2,923, **Arizona 8,935**, Louisiana 10,468, Massachusetts 44, Nebraska 3,383, North Carolina 6,207, United States 10. **Replication (RDS side only):** the slot `ddp_legbot_subscription` is **streaming, lag 0**; the Mac's side is yours.

## What I did not do
Utah and Virginia: **not run**; I stop here and wait for a **"verified" line for Arizona** on this branch (then the user's go for Utah; Utah's own archive day is Monday). Nothing else was touched.
