# GO: Alabama `refresh-extraction` and `recompute-diff-order` commits (OPEN-529, OPEN-530), 2026-11-11 about 14:45 UTC (Mac side)

**Ramon's words, 2026-11-11:** "Go, save it today (Recommended)", his answer to: should the prod agent save the Alabama text clean-up now (1,004 documents re-read without struck-out words, then 916 comparisons rebuilt).

This is the GO for **Part 2 of `2819ef83`**, exactly as written there, after your Part 1 reply `763b375`. Nothing beyond it.

## What to run
Run it today in your proposed window (after 11:30 UTC and done by 01:30 UTC), with the same code as Part 1: core `main` `a89dd31c` (or later) in a throwaway worktree on `PYTHONPATH`, with PyMuPDF 1.26.5. Record "now" as the rollback point just before the first commit, as you proposed.

Run these steps in order, and check each one before starting the next:
1. Run `os-text-extract refresh-extraction al --dry-run` again. It must print what Part 1 printed (`bills_with_stale_docs=524 stale_docs=1004 diffs_would_change=357 docs_skipped=0 docs_refused=0`). If it doesn't, stop and report.
2. Run `os-text-extract refresh-extraction al --commit`. Then run `--dry-run` again; it must report 0 stale documents.
3. Run `os-text-extract recompute-diff-order al --dry-run`, and report its lines. The numbers will be lower than 916, because step 2 already recomputed some bills' comparisons.
4. Run `os-text-extract recompute-diff-order al --commit` (the full run, **not** `--flags-only`). Then run `--dry-run` again; it must report `corrected=0`.
5. Run G3 again. Expected: `docs` 2923, `flag_null` 0 and `flag_false` 498, all unchanged. `with_diff` is likely to fall. Report the value; I count the comparisons that became empty on the Mac.
6. Reply `reply-alabama-refresh-and-recompute-committed-20261111.md` with the lines from each step, the query rows, the start and end times (UTC), the rollback time, and confirmation that nothing else changed. Then remove the worktree.

## Not authorized
* Any other state; `all`.
* `--flags-only` at commit.
* A search refresh, any scrape, archive, schedule change, restart or LegBot run.
* Any change to ddp-sync, the broker, the manifest or a task definition.
* A retry or an undo by hand if a step fails. Stop and report instead.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
