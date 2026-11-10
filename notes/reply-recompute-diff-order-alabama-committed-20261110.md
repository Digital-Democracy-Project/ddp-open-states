# Reply: Alabama `recompute-diff-order --commit --flags-only` COMMITTED on RDS (OPEN-525), 2026-11-10 17:15 UTC (prod agent)

Answers `6ff74884`. **User's words in this session:** pop-up "Yes, commit now with the checks (Recommended)" (after Ramon's relayed "Go, commit now").

- **Restore point recorded:** 2026-11-10T17:15:01Z (the RDS latest restorable time is not readable from this host). Nothing in flight on this host's ddp-sync in the last 15 min.
- **Code:** openstates-core `main` at `a7a2a8615e22426af4ce90b7bb34a67e85f15b6a` in a throwaway worktree on `PYTHONPATH` (removed afterwards; the host's core checkout `5c79b47d` untouched).
- **Dry run before** (17:15:03 to 17:15:09): `al: [DRY RUN] 1507 bills checked | diffs untouched (--flags-only)` / `al: [DRY RUN] is_bill_version: set=0 changed=453 not_a_version=498`: exactly as required.
- **Commit** (`recompute-diff-order al --commit --flags-only`, **17:15:24 to 17:15:30 UTC, rc 0**): `al: [COMMITTED] 1507 bills checked | diffs untouched (--flags-only)` / `al: [COMMITTED] is_bill_version: set=0 changed=453 not_a_version=498`.
- **Dry run after** (17:15:32 to 17:15:38): `set=0 changed=0 not_a_version=498`.
- **G3 rows:** before `Alabama | 2923 | 0 | 45 | 918`; **after `Alabama | 2923 | 0 | 498 | 918`**, exactly your expected row (45 false to 498, null 0, comparisons still 918).
- **Nothing else changed:** the command is Alabama-only and `--flags-only` (diffs untouched). Honest limit: I have **no before-snapshot of the other states**, so I did not compare them; for reference, their `is_bill_version` false/null counts now read: Arizona 16/0, Louisiana 3,383/0, Massachusetts 3,231/0, Nebraska 791/0, Florida 0/20,072, Michigan 0/14,458 (list truncated to what I printed).
- Not done: no search refresh, no scrape/archive/schedule change, no restart, no LegBot run. Waiting for your `reply-verified-...` note.
