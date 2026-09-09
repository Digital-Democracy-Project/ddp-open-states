# RDS backfill Step 3 -- real baseline for UT/WA/US, poppler-utils fix confirmed everywhere

*Follows up on `notes/ut-refused-docs-root-cause-missing-pdftotext-20260909.md`.* With
`poppler-utils` installed on this host and `openstates-core` main (`5c79b47d`) pulled in, re-ran
`refresh-extraction {ut,wa,us} --dry-run` against RDS one more time. `docs_refused=0` across the
board now — the missing binary really was masking the whole picture.

## Real numbers

- `ut: bills_with_stale_docs=1021 stale_docs=3835 diffs_would_change=4671 docs_skipped=0
  docs_refused=0`
- `wa: bills_with_stale_docs=3411 stale_docs=6230 diffs_would_change=4538 docs_skipped=1
  docs_refused=0`
- `us: bills_with_stale_docs=37672 stale_docs=73510 diffs_would_change=10799 docs_skipped=6
  docs_refused=0` — the 6 skipped are "no archive_location on row," a separate, minor
  data-completeness gap, not blocking.

Worth noting: `stale_docs` and `diffs_would_change` went *up* from the earlier
missing-`pdftotext` runs in both UT and WA (UT: 3,100→3,835 stale, 2,079→4,671 diffs; WA:
5,818→6,230 stale, 2,270→4,538 diffs) — extraction can now actually succeed on documents that
were previously silently refused, surfacing real diffs that were invisible before.

This is Step 3 done for all three jurisdictions — clean enough to move to `--commit` whenever
that's approved, per `PLAN-rds-data-quality-backfill.md` §4. Not running `--commit` myself
without an explicit go-ahead, same as the rest of this thread.

## Also: US's earlier run completed successfully despite the harness reporting exit code -1

Worth a footnote in case it comes up: the first post-poppler-utils US run's process detached
during an unrelated session transition on my end, and the harness reported the exit code as
unknown/-1 — but the actual output shows the job ran to completion and wrote its full summary
line before that happened, so the numbers above are real, not a partial/killed run's garbage.
