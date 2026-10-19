# GO from Ramon: OPEN-399 Part 3 (regenerate the 77 affected Virginia changelogs). (Mac side, 2026-10-19 EDT)

Ramon read your Part 2 reply (`reply-open399-va-recompute-part2-done-20261019.md`, commit `811e769`) and said yes to Part 3 of `request-open399-va-recompute-part1-now-commit-HOLD-until-ramon-says-go-20261019.md` (commit `9c343b2`). **Ramon also confirms the changelog prompt wording is final** (the wording freeze that Part 3 required). A HOLD note from Ramon on this branch overrides this one.

## The prompt that is final (so "final" can be checked)

* ddp-agents `main` at **`39d308d2`** (the Mac's production checkout, nothing newer on `origin/main`); `config/legbot_questions.yaml` was last changed on 2026-10-16 in `eea972f5` ("SYNC-117: do not claim the paragraph is shown first"). The `bill_changelog` prompt text is **4,512 characters**, sha256 prefix **`830c8fa29b`**.
* The Mac's CAMS server (pid 72087) was started 2026-10-19 00:10 EDT, after that change, so it runs this prompt. Ramon's confirmation covers exactly this version. If you ever see Ramon or the Mac side announce a different prompt before you finish, stop and report.
* ddp-agents PR #371 (a filter that drops `of N` lines from the diff the model reads) is live in that checkout. It does nothing now that the stored diffs are clean; it stays in place until the end, and is the Mac side's to revert. Do not touch it.

## What is authorized

Part 3 as written in the request, for **the 77 changelogs in `VA_affected_changelogs_production.csv`** (commit `38cd5fe`; all `complete` + `approved`; 54 bills; including HB 979's two rows and HB 49). Nothing else.

Use the procedure and safety rules in `notes/request-open387-live-bill-changelog-triage-and-per-state-rewrite-directions-20261018.md` on **ddp-sync's `notes/ops-handoff`** ("Rules for every state" and the trigger), the same way you ran the Michigan rewrite:
1. **Before anything:** quiet check; Ramon's side or you confirm `cams status` is idle; the Mac's ddp-sync answers `GET /ddp-sync/v1/health` with `X-DDP-Environment: prod` and your Mac key.
2. **Back up first:** write the 77 rows' review fields (id, status, review_status, reviewed_by, reviewed_at) to a CSV on the host and keep it.
3. **One-row test first, on HB 979:** reject its Finance Substitute row, run a one-bill trigger (`dry_run: true` first, then the real call, `X-DDP-Environment: prod`, `artifact_types: ["bill_changelog"]`, `include_org_research: false`, `include_concept_statements: false`), and confirm the row is rewritten in place (`generated_at` does not change on an in-place rewrite; compare content), is `complete` and `approved`, and **does not say the donor-screening fee was removed**. Also read it against the Finance Substitute's diff.
4. **Then the rest, as one batch:** 54 bills is inside the 50-to-100 batch size, so reject the remaining rows of the list and run them at once (a rejected row is hidden from the site until rewritten; production auto-approves, `BILL_ARTIFACT_REQUIRE_REVIEW=false`). Do not reject more than you are about to run. The trigger is a long synchronous call (about 20 to 45 seconds a summary, so roughly 30 to 60 minutes for the batch); do not restart ddp-sync or run `cams reload` on the Mac while it is in flight.
5. **Do not run it at the same time as another LegBot batch.** In particular NC's first large batch (session `2025`, OPEN-390) must not start while this runs; NC's weekly archive is Thursday 05:00 UTC and Virginia's is **Wednesday 05:00 UTC**. Finish this clear of both (the batch can start now and should end well before Wednesday 04:00 UTC).

## Verify (report all of it)

* Every one of the 77 is `complete` + `approved` again; Virginia's rejected count is back to 0; the broker's Virginia total is still 511 (or what it is now, with the reason for any difference).
* **HB 979:** the new summaries do not claim the donor-screening fee was removed.
* **HB 49** (Commerce Agriculture & Natural Resources Subcommittee Substitute, the one whose diff was only marker lines): the new summary should say there is no substantive change, with empty lists.
* **Read about 10 other regenerated summaries against their diffs** and say what you found (the diff is the stored one, now clean).
* Any row still failed or rejected, any raw `{'...'}` object in a list item, any empty output, any row-count mismatch: **stop, change nothing more, report.**

## Stop conditions

A row count that does not match the list; an artifact id that maps to a different bill or version than the CSV; a regenerated row that is still `failed`; any summary that shows a raw `{'...'}` object or is empty; the one-row test failing (summary still claims the fee removed, row not `complete`/`approved`); anything unexpected. Stop, change nothing more, report. No retry beyond one re-run of a single failed bill, no rollback without authorization (the backed-up review fields and the rejected rows' old text are the way back: a row can be set back to `approved` only on Ramon's say-so).

## Not authorized

Any state but Virginia; any changelog outside the 77; the Optional/Hold tiers of OPEN-387; Massachusetts (`recompute` or regeneration; OPEN-396); starting NC's batch; reverting or touching ddp-agents #371; any flag, schedule, image, task definition, archive, embedding or LegBot run outside this batch; `recompute-diff-order` again.

## Reply on this branch

One `reply-open399-va-changelog-regeneration-...` note: the checks before (quiet, `cams status`, health), the backup file name, the HB 979 one-row test (before and after wording), the batch's start and end time and counts, the verification list above, and anything unexpected. The Mac side then reverts #371.
