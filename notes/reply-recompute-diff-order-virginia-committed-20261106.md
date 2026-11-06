# Reply: `recompute-diff-order va --commit` done on RDS, the last of the five. Every number matched. **All five states are now committed.** Waiting for your "verified" line and your re-scan. Written 2026-11-06 16:46 UTC.

Run at the user's go ("Yes, run Virginia now if the gates are clean (Recommended)") under your GO note `9568df0c` and after your Utah "verified" line `f098e475`. Nothing else changed: no other state, no refresh, scrape, archive, schedule, restart, and **no bill summary was touched** (not asked).

## Gates and restore point (16:37 UTC, immediately before)
No ECS task; nothing in flight; **no ddp-sync job in the last 12 minutes**; the next ddp-sync run is **2026-11-07 00:30 UTC**; Virginia's own archive day is **Wednesday** (today is Friday). Code: the same throwaway worktree, `HEAD` = **`978fa96c49adc3fb6304fccda8237b24caea0cd5`**. **RDS latest restorable time right before the commit: `2026-11-06T16:32:46Z`** (the rollback point).

## The run (outputs in `notes/recompute-five-20261106/va-part2-*-output.txt`)
1. **Dry run first, 16:38:56 UTC**, exit 0, **exactly your Part 1 lines** (my script compared them and would have stopped on any difference): `va: [DRY RUN] 4405 bills checked | unchanged=25591 corrected=0 nulled=0` and `va: [DRY RUN] is_bill_version: set=25591 changed=0 not_a_version=1828`.
2. **`recompute-diff-order va --commit`, 16:40:39 UTC**, exit 0, the same numbers: `va: [COMMITTED] 4405 bills checked | unchanged=25591 corrected=0 nulled=0` and `va: [COMMITTED] is_bill_version: set=25591 changed=0 not_a_version=1828`.
3. **`--dry-run` again, 16:41:31 UTC**, exit 0: `va: [DRY RUN] 4405 bills checked | unchanged=25591 corrected=0 nulled=0` and `va: [DRY RUN] is_bill_version: set=0 changed=0 not_a_version=1828` (**`corrected=0 nulled=0`, `changed=0`**).
About 2 minutes 35 seconds from the first dry run to the last (the commit itself took 1 minute 43 seconds for 25,591 rows).

## The G3 query after (16:42 UTC)
| state | docs | flag_null | flag_false | with_diff |
|---|---|---|---|---|
| **Virginia** | 25,591 | **0** (was 25,591) | **1,828** (was 0) | **14,927 (unchanged)** |
| Alabama | 2,923 | 0 | 45 | 918 |
| Arizona | 8,935 | 0 | 16 | 4,328 |
| North Carolina | 6,207 | 0 | 54 | 3,557 |
| Utah | 9,371 | 0 | 3,170 | 4,158 |
`ddp_bill_version_document` total **224,167** (unchanged); **flags set in the whole table 66,932** (41,341 + 25,591, exactly Virginia's documents); by state: Alabama 2,923, Arizona 8,935, Louisiana 10,468, Massachusetts 44, Nebraska 3,383, North Carolina 6,207, United States 10, Utah 9,371, **Virginia 25,591**. **Replication (RDS side only):** the slot `ddp_legbot_subscription` is **streaming, lag 0** (read after the 25,591-row update); the Mac's side is yours.

## All five, in one place
| state | committed (UTC) | restore point | `flag_false` | `with_diff` | reply |
|---|---|---|---|---|---|
| Alabama | 15:33 | 15:27:45Z | 45 | 918 | `6153a07` |
| North Carolina | 15:54 | 15:47:46Z | 54 | 3,557 | `0f5c482` |
| Arizona | 16:24 | 16:17:46Z | 16 | 4,328 | `709fe0f` |
| Utah | 16:33 | 16:27:46Z | 3,170 | 4,158 | `2b1835a` |
| Virginia | 16:40 | 16:32:46Z | 1,828 | 14,927 | this note |
Together with Nebraska (3,383) and Louisiana (10,468), **every Nebraska, Louisiana, Alabama, North Carolina, Arizona, Utah and Virginia document now carries the mark**; `flag_null` is 0 in all seven.

## What I did not do
Nothing beyond Virginia: no other state, no `recompute-diff-order all`, no `ma --commit`, no summary rejected (Arizona's 17 untouched), no refresh. I wait for your **"verified" line for Virginia** and for your 104-bill re-scan (OPEN-422) and the 22 SYNC-126 bills. The throwaway worktree (job scratch `o486/wt`) can be removed after you have verified.
