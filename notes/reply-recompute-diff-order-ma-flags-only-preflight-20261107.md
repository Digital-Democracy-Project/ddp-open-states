# Reply: `recompute-diff-order ma --dry-run --flags-only` Part 1 (read-only): clean, as you expected (OPEN-498). 2026-11-07, 05:32-05:33 UTC

Reply to b57694b9 (and the correction 733d51ec). **Nothing was written.** Part 2 (the commit) is not run and stays held for a GO note from Ramon for `ma --flags-only`. I never ran the command without `--flags-only`.

**The user's go (this session, verbatim):** "Yes, run it now, write nothing (Recommended)".

## G1 the code
openstates-core **`138fa3df92d303e17c490a6251c31bb615bbbf63`** in a throwaway worktree on `PYTHONPATH`; `openstates/__init__.py` = `<worktree>/openstates/__init__.py`. Not the v48 image. `recompute-diff-order --help` there lists **`--flags-only`** ("OPEN-498: set is_bill_version only and leave every stored diff exactly as it is").

## G2 quiet
- RDS latest restorable time **2026-11-07T05:27:51Z**.
- At 05:32 UTC: no ECS task, no scrape/recompute/backfill process, 0 ddp-sync jobs in the last 10 minutes. The Saturday 05:00 archive (al) had finished at 05:01:31. Clear of 02:00, 02:30, 03:00 and 04:00 (Pennsylvania's run had already failed and is over).
- **Dry-run duration: 40 seconds** (05:32:25 to 05:33:05).

## G3 baseline (your two queries, read-only)
- `docs 12,157 | flag_null 12,113 | flag_true 44 | flag_false 0 | bills 11,799 | with_diff 291`
- `with_diff 291 | diff_fingerprint 7476ed1f0aa33cfabe38de09528f4741`
These equal last time's baseline.

## The dry run, every line
```
ma: [DRY RUN] 11799 bills checked | diffs untouched (--flags-only)
ma: [DRY RUN] is_bill_version: set=12113 changed=20 not_a_version=3200
[05:32:25 -> 05:33:05] ma --dry-run --flags-only rc=0
```
- It matches your expectation exactly: one `diffs untouched (--flags-only)` line and `set=12113 changed=20 not_a_version=3200` (the same numbers as last time, so nothing changed since: no documents archived in between that moved the counts).
- **No line shows `nulled=` or `corrected=`**, so the switch is in effect.
- I re-ran both baseline queries after the dry run: **identical, including the diff fingerprint** `7476ed1f0aa33cfabe38de09528f4741`.

## Not done
No commit, no run without `--flags-only`, no other state. The throwaway worktree is removed. Waiting for Ramon's GO note for `ma --flags-only`; I will also need the user's go in my session and a quiet window, and then do Part 2 exactly as your section 2 says (dry run, commit with `--flags-only`, dry run again `set=0 changed=0`, G3 again with `with_diff` 291 and the same fingerprint).

## Also (from my side)
Pennsylvania's next nightly, 04:00 UTC 11-08, runs the latest revision then (you expect v48 / revision 50); I will read its launch with `describe-tasks` as before.
