# GO: Alabama `recompute-diff-order --commit --flags-only` (OPEN-525, OPEN-523). 2026-11-10 about 17:20 UTC (Mac side)

**Ramon's words, 2026-11-10 (pop-up answer to the dry-run result):** "Go, commit now (Recommended)".

This GO covers **Part 2 of `51c0015` for Alabama only**, exactly as written there. It follows your Part 1 reply `dc99210`: both dry runs matched, `changed=453 not_a_version=498`, `corrected=0 nulled=0`.

## Do
1. Record "now" (UTC) as the restore point, since the RDS latest restorable time is not readable from your host. Confirm nothing is in flight.
2. Use the same code as Part 1: openstates-core `main` at `a7a2a861` or later, in a throwaway worktree on `PYTHONPATH`.
3. `os-text-extract recompute-diff-order al --dry-run --flags-only`. It must print exactly `set=0 changed=453 not_a_version=498`. If not, stop and report.
4. `os-text-extract recompute-diff-order al --commit --flags-only`.
5. `os-text-extract recompute-diff-order al --dry-run --flags-only` again. It must print `changed=0`.
6. The G3 query again. **Expected:** `Alabama | 2923 | 0 | 498 | 918`.

## Reply
`reply-recompute-diff-order-alabama-committed-20261110.md`, with:
* the lines and start/end times (UTC);
* the G3 rows before and after;
* that nothing else changed.

Then wait for my `reply-verified-…` note.

## Not authorized
* Everything on `51c0015`'s list: any other state, `all`, a commit without `--flags-only`, a search refresh, scrape, archive, schedule change, restart or LegBot run.
* Any ddp-sync, broker, manifest or task-definition change.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
