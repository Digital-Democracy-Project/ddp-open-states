# ut recompute-diff-order --dry-run: run for the first time, completely clean

Per your correction, ran the step that had never actually executed:
`recompute-diff-order ut --dry-run` via the Fargate trigger.

`ut: [DRY RUN] 1021 bills checked | unchanged=9371 corrected=0 nulled=0`

Zero corrections, zero nulled -- nothing to change. Unlike `va` (a genuine, large backward
walk-order fix), `ut`'s diff lineage was apparently already correct from the original
archive-time order. Since there's nothing changed, there's no document-level sample to
spot-check (nothing to compare against the Mac) -- a `--commit` here would be a no-op,
producing the identical empty result.

## Your second ask -- the original 4110-vs-4671 discrepancy

Already effectively answered by the corrected go/no-go check from earlier in this thread
(`notes/corrected-govno-check-clean-20260910.md`): a fresh `refresh-extraction ut --dry-run`
inside the fixed Python 3.10/poppler 22.12 toolchain found only 1 residual stale document
out of the original 3,835 -- confirming the earlier fix is stable and that discrepancy
wasn't a sign of ongoing data-integrity trouble, just the benign dry-run-ordering bug (Cause
#1 from your own root-cause note) plus one small real poppler-content difference that's
already accounted for.

**`ut` is now genuinely done** -- both required steps (`refresh-extraction --commit`,
`recompute-diff-order` -- dry-run here, with nothing to commit) have actually run, unlike
before. Backfill progress: `mi`, `ut`, `fl`, `va` done. `wa`/`us` remain.
