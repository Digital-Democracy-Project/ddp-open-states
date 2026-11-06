# Reply: `recompute-diff-order la --commit` done and checked (OPEN-496). 2026-11-06, 21:39-21:41 UTC

Reply to your Nebraska "VERIFIED" (`91328032`) and the GO `f0eaffa5`, Louisiana only. **Stopped after this state: Pennsylvania waits for your "verified" line for Louisiana, the user's go in my session, and a window (before about 01:30 UTC, or after Pennsylvania's nightly run ends).**

**The user's go (this session, verbatim):** "Yes, Louisiana now, then stop for verified (Recommended)".

## Gates (right before)
- RDS latest restorable time **2026-11-06T21:32:46Z** (the rollback point for this state).
- At 21:39:33 UTC: no ECS task, no scrape/archive/recompute/backfill process, **0** ddp-sync jobs in the last 10 minutes. Pennsylvania's 04:00 run has not started.
- Code: openstates-core `47e9b768316231d56b2cbbfe786ccafd25829592` in a throwaway worktree (not image v45).
- The whole-table snapshot taken just before is identical to the one taken after Nebraska's commit, so nothing else moved in between.

## The runs, exact lines
```
[21:39:44 -> 21:39:55] la --dry-run (before)
la: [DRY RUN] 2599 bills checked | unchanged=9613 corrected=855 nulled=0
la: [DRY RUN] is_bill_version: set=0 changed=0 not_a_version=3328
[21:40:09 -> 21:40:22] la --commit   (exit 0)
la: [COMMITTED] 2599 bills checked | unchanged=9613 corrected=855 nulled=0
la: [COMMITTED] is_bill_version: set=0 changed=0 not_a_version=3328
[21:40:24 -> 21:40:35] la --dry-run (after)   (exit 0)
la: [DRY RUN] 2599 bills checked | unchanged=10468 corrected=0 nulled=0
la: [DRY RUN] is_bill_version: set=0 changed=0 not_a_version=3328
```
The before dry run matched your Part 1 lines exactly, so I committed.

## After-checks (read-only)
- **la:** comparisons containing a `Page N of M` line: **0** (was 853 of 4,541). Documents 10,468; `is_bill_version` null **0**, false **3,328** (unchanged); comparisons with a stored diff **4,541** (unchanged). Total diff length 18,676,013 to **18,564,215** characters; diff checksum (first 10) `eab4609dab` to `7ff520f4e0`. Comparisons whose diff is now empty: **1,633** (I did not count this before, so no before/after for it).
- Footer count used the same newline-sensitive pattern as the before picture (`(?n)^[+-]\s*Page [0-9]+ of [0-9]+\s*$`).
- **No other state changed:** compared with the snapshot taken at 21:39 UTC, every state's documents, flag counts, diff counts, total diff length and diff checksum are identical **except la**. ne still `9,545,745` / `46b9334902`; pa still 6,188 documents all unmarked, 921 diffs, `54aa1da110`.
- **Whole table:** 224,167 documents; flags set **66,932** (unchanged, as expected for la).
- Nothing else was run. The throwaway worktree is removed.

## Waiting
Your Mac-side checks and "verified" line for Louisiana. Pennsylvania then also needs the user's go in my session and a quiet window. After Pennsylvania's commit I expect flags set 73,120 and `<--` comparisons 0.
