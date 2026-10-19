# GO from Ramon: OPEN-399 Part 2 ONLY (the Virginia recompute commit). Part 3 stays on HOLD. (Mac side, 2026-10-19 EDT)

Ramon read your Part 1 reply (`reply-open399-va-recompute-preflight-part1-done-20261019.md`, commit `38cd5fe`) and said to go for **Part 2** of `request-open399-va-recompute-part1-now-commit-HOLD-until-ramon-says-go-20261019.md` (commit `9c343b2`). That request's Part 2 text is the procedure; this note only starts it and adds the conditions below. A HOLD note from Ramon on this branch overrides this one.

## What is authorized

**Part 2 as written**, in the G1 worktree you kept (`openstates-core` at exactly `4f023bec60c0d9425472ead0927b7f82234cc936`):
1. **Just before the commit:** run the quiet check again (no scrape, archive, load, text-extract, LegBot relay or backfill in flight, no scheduler job starting inside the next hour), and record a **fresh RDS latest restorable time**.
2. **Dry run again.** It must print **exactly the line you reported in Part 1**: `va: [DRY RUN] 4388 bills checked | unchanged=22767 corrected=2790 nulled=0`. If new data was archived since and it differs, **report the new line and wait**; do not commit on a line you have not reported.
3. **`recompute-diff-order va --commit`** (one state, never `all`), which must print the same three numbers.
4. **A second dry run** that must print `corrected=0 nulled=0`.
5. **The baseline query again** (the `docs_with_marker_line` one): it must now return **0**. (It was 2,736 on RDS.)
6. **HB 979:** read the Finance Substitute's diff from api-v3 and confirm it has no `of 12` / `of N` line, and that the paragraph around the old marker ("...a possible bone marrow" / "donor, if ...") reads as one unbroken sentence.

**Window:** the host is quiet now; use it any time up to about **Wednesday 2026-10-21 04:00 UTC**, which is more than an hour before Virginia's archive at 05:00 UTC. Re-check quiet at the moment you start, not from this morning's reading.

## Stop conditions

If the commit's numbers differ from the dry run, if it errors or stops partway, if the second dry run is not `corrected=0 nulled=0`, if the marker count is not 0, or if the HB 979 check fails: **stop and report. No retry and no rollback without authorization.** (If a rollback is ever needed: check out the previous core commit `53feef5b` and recompute Virginia again; `raw_text` is untouched, so nothing is lost.)

## Still on HOLD

**Part 3 (regenerating the 77 affected changelogs) is NOT authorized by this note.** It needs its own GO from Ramon, and Ramon has not yet confirmed that the changelog prompt wording is final. Do not reject, regenerate or trigger anything for Virginia. Leave ddp-agents PR #371 alone: it stays in place until Part 3 is verified.

## Not authorized

Any state but Virginia; `recompute-diff-order all`; `recompute-diff-order ma --commit` (it would null Massachusetts's 291 legacy cross-media diffs, a separate decision, OPEN-396); the Fargate image or task definition; any flag, schedule, scrape, archive, embedding or LegBot run; changing existing installs; rolling back without authorization.

## Reply on this branch

One `reply-open399-va-recompute-part2-...` note: the quiet check and the restorable time you recorded, the dry-run line before, the commit's three numbers, the second dry run, the marker count, the HB 979 result, and anything unexpected. Then wait for the Part 3 GO.
