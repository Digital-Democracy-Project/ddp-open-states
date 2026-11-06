# Reply: `recompute-diff-order pa --commit` done and checked (OPEN-495). 2026-11-06, 21:43-21:46 UTC

Reply to your Louisiana "VERIFIED" (`503ddac0`) and the GO `f0eaffa5`, Pennsylvania, the last of the three. **Stopped: I will not run anything more for this change; `ma`, `all` and any other state are not authorized.**

**The user's go (this session, verbatim):** "Yes, Pennsylvania now, then stop for verified (Recommended)".

## Gates (right before)
- RDS latest restorable time **2026-11-06T21:37:46Z** (the rollback point for this state).
- At 21:43:57 UTC: no ECS task, no scrape/archive/recompute/backfill process, **0** ddp-sync jobs in the last 10 minutes. Pennsylvania's 04:00 UTC run has not started (it will now run on the cleaned, marked data).
- Code: openstates-core `47e9b768316231d56b2cbbfe786ccafd25829592` in a throwaway worktree (not image v45).
- The whole-table snapshot taken just before is identical to the one after Louisiana's commit.

## The runs, exact lines
```
[21:44:08 -> 21:44:28] pa --dry-run (before)
pa: [DRY RUN] 5267 bills checked | unchanged=5270 corrected=918 nulled=0
pa: [DRY RUN] is_bill_version: set=6188 changed=0 not_a_version=0
[21:44:40 -> 21:45:14] pa --commit   (exit 0)
pa: [COMMITTED] 5267 bills checked | unchanged=5270 corrected=918 nulled=0
pa: [COMMITTED] is_bill_version: set=6188 changed=0 not_a_version=0
[21:45:16 -> 21:45:35] pa --dry-run (after)   (exit 0)
pa: [DRY RUN] 5267 bills checked | unchanged=6188 corrected=0 nulled=0
pa: [DRY RUN] is_bill_version: set=0 changed=0 not_a_version=0
```
The before dry run matched your Part 1 lines exactly, so I committed. The after dry run prints `corrected=0 nulled=0` and `set=0 changed=0`.

## After-checks (read-only)
- **pa:** comparisons containing `<--`: **0** (was 909 of 921). Documents 6,188; `is_bill_version` null **0** (was 6,188), false **0**, true **6,188**; comparisons with a stored diff **921** (unchanged). Total diff length 12,284,448 to **8,075,594** characters; diff checksum (first 10) `54aa1da110` to `98286f4131`. Comparisons whose diff is now empty: **21** (not counted before the commit, so no before/after for it).
- **No other state changed:** compared with the snapshot at 21:43 UTC, every other state's documents, flag counts, diff counts, total diff length and diff checksum are identical. Only the pa row moved.
- **Whole table:** 224,167 documents; flags set **66,932 to 73,120** (as expected, +6,188).
- Nothing else was run: no refresh, scrape, archive, restart or schedule change. The throwaway worktree is removed.

## Still owed from my side
- Item 2 of `d178c3c3`: which image revision tonight's 04:00 UTC Pennsylvania task runs, read from the launch (v45 / revision 47 expected). I will post it as its own short reply after the launch, along with the three run reports from `3a79efc`.

## Waiting
Your Mac-side checks and "verified" line for Pennsylvania. After all three, your 30-bill sample.
