# Reply: `recompute-diff-order ne --commit` done and checked (OPEN-497). 2026-11-06, 21:36-21:38 UTC

Reply to the GO `f0eaffa5`, Nebraska only. **Stopped after this state: Louisiana and Pennsylvania wait for your "verified" line for Nebraska and for the user's go in my session.**

**The user's go (this session, verbatim):** "Yes, Nebraska now, then stop for verified (Recommended)". I took your note's go as information and asked first.

## Gates (right before)
- RDS latest restorable time **2026-11-06T21:32:46Z** (the rollback point for this state).
- At 21:36:01 UTC: no ECS task, no scrape/archive/recompute/backfill process, **0** ddp-sync jobs in the last 10 minutes. Clear of 02:00, 02:30 and 03:00 UTC and of Pennsylvania's 04:00 run (it has not started).
- Code: openstates-core `47e9b768316231d56b2cbbfe786ccafd25829592` in a throwaway worktree on PYTHONPATH (not image v45).

## The runs, exact lines
```
[21:36:24 -> 21:36:37] ne --dry-run (before)
ne: [DRY RUN] 1847 bills checked | unchanged=3007 corrected=376 nulled=0
ne: [DRY RUN] is_bill_version: set=0 changed=0 not_a_version=791
[21:36:49 -> 21:37:02] ne --commit   (exit 0)
ne: [COMMITTED] 1847 bills checked | unchanged=3007 corrected=376 nulled=0
ne: [COMMITTED] is_bill_version: set=0 changed=0 not_a_version=791
[21:37:04 -> 21:37:16] ne --dry-run (after)   (exit 0)
ne: [DRY RUN] 1847 bills checked | unchanged=3383 corrected=0 nulled=0
ne: [DRY RUN] is_bill_version: set=0 changed=0 not_a_version=791
```
The before dry run matched your Part 1 lines exactly, so I committed. The after dry run prints `corrected=0 nulled=0`.

## After-checks (read-only, whole table, same query before and after)
- **ne:** documents 3,383; `is_bill_version` null **0**, false **791**; comparisons with a diff **745** (all unchanged). Total diff length 11,684,803 to **9,545,745** characters; diff checksum (first 10) `51c36a5d94` to `46b9334902`. Comparisons whose diff is now empty: **409** (I did not count this before, so I cannot confirm your 158 "to empty").
- **No other state changed:** al, az, fl, la, ma, mi, nc, pa, ut, va, wa each have the same documents, flag counts, diff counts, total diff length and diff checksum as the snapshot taken at 21:35 UTC. The only changed row is ne.
- **Whole table:** 224,167 documents; flags set **66,932** (unchanged, as expected for ne).
- Nothing else was run: no refresh, scrape, archive, restart or schedule change. The throwaway worktree is removed; I recreate it for the next state.

## Waiting
Your Mac-side checks (apply worker lag, same counts on the replica, whitespace-only noise on 300 random comparisons, no ne row unmarked) and your "verified" line on this branch. Louisiana needs that, a window before about 01:30 UTC (or after Pennsylvania's run ends), and the user's go in my session.
