# Reply: `recompute-diff-order al --commit` done on RDS. Every number matched. **Stopped; waiting for your "verified" line before North Carolina.** Written 2026-11-06 15:36 UTC.

Run at the user's go ("Yes, run Alabama now if the gates are clean (Recommended)") under your GO note `9568df0c` (the user's answer came about nine hours after my question at 06:45 UTC, so the run is at **15:33 UTC**, not the early-morning time I had in mind). Nothing else changed: no other state, no refresh, scrape, archive, schedule, restart.

## Gates and restore point (15:32 UTC, immediately before)
No ECS task; nothing in flight; **no ddp-sync job in the last 12 minutes**; the next ddp-sync run is **2026-11-07 00:30 UTC**; Alabama's own archive is **Saturday 05:00 UTC** (tomorrow), so today is the right side of it. Code: the same throwaway worktree, `HEAD` = **`978fa96c49adc3fb6304fccda8237b24caea0cd5`**. **RDS latest restorable time right before the commit: `2026-11-06T15:27:45Z`** (the rollback point for this commit; the Part 1 reading was `06:02:53Z`).

## The run (outputs in `notes/recompute-five-20261106/al-part2-*-output.txt`)
1. **Dry run first, 15:32:55 UTC**, exit 0, **exactly your Part 1 lines** (my script compared them and would have stopped on any difference): `al: [DRY RUN] 1507 bills checked | unchanged=2923 corrected=0 nulled=0` and `al: [DRY RUN] is_bill_version: set=2923 changed=0 not_a_version=45`.
2. **`recompute-diff-order al --commit`, 15:33:06 UTC**, exit 0, the same numbers: `al: [COMMITTED] 1507 bills checked | unchanged=2923 corrected=0 nulled=0` and `al: [COMMITTED] is_bill_version: set=2923 changed=0 not_a_version=45`.
3. **`--dry-run` again, 15:33:12 UTC**, exit 0: `al: [DRY RUN] 1507 bills checked | unchanged=2923 corrected=0 nulled=0` and `al: [DRY RUN] is_bill_version: set=0 changed=0 not_a_version=45` (**`corrected=0 nulled=0`, `changed=0`**).
About 17 seconds from the first dry run to the last.

## The G3 query after (15:33 UTC)
| state | docs | flag_null | flag_false | with_diff |
|---|---|---|---|---|
| **Alabama** | 2,923 | **0** (was 2,923) | **45** (was 0) | **918 (unchanged)** |
| Arizona, North Carolina, Utah, Virginia | 8,935 / 6,207 / 9,371 / 25,591 | unchanged (all null) | 0 | unchanged (4,328 / 3,557 / 4,158 / 14,927) |
`ddp_bill_version_document` total **224,167** (unchanged); **flags set in the whole table 16,828** (13,905 before + 2,923, exactly Alabama's documents); by state: Alabama 2,923, Louisiana 10,468, Nebraska 3,383, Massachusetts 44 and United States 10 (the last two are documents archived on v43). **Replication (RDS side only):** the slot `ddp_legbot_subscription` is **streaming, lag 0**; the Mac's side is yours.

## What I did not do
North Carolina, Arizona, Utah and Virginia: **not run**; I stop here as your note says and wait for a **"verified" line for Alabama** on this branch (and then the user's go for North Carolina). Nothing else was touched.
