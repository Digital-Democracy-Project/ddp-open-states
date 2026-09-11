# Go-ahead: proceed with wa, no need to wait behind ut/us

Ramon's go-ahead to move `wa` forward now. Since Fargate isolates each task, no need to
queue it behind `ut`'s redo or `us`'s still-running dry-run -- run it in parallel, same
reasoning as launching all the original dry-runs in parallel earlier.

## Steps, in order

1. **`refresh-extraction wa --commit`.** Run a fresh `refresh-extraction wa --dry-run`
   immediately before committing, per the established discipline, even though the last one
   already looked clean (`stale_docs=5818 diffs_would_change=4538 docs_refused=0`) -- confirm
   it still matches right before writing, same as every other commit this backfill.

2. **Fresh `recompute-diff-order wa --dry-run`**, only after step 1 actually commits (the
   one you already have, `unchanged=7098 corrected=4538 nulled=0`, was taken before
   refresh-extraction and won't be the real number).

3. **Send a spot-check sample here** -- same shape as mi/fl/va: at least one nulled and a
   handful of corrected documents (bill identifier, full `ocd-bill/...` id, `doc_id`,
   `version_note`, `media_type`, current stored diff length, proposed new diff length). I'll
   verify them against the Mac's copy before recommending a go-ahead -- this step doesn't
   get skipped for `wa` the way it did for `ut`.

4. Once that checks out, I'll post the go-ahead and you can run
   `recompute-diff-order wa --commit`, then verify the actual post-commit DB state directly
   against a couple of the spot-checked samples (same as fl/va), not just the summary line.

Report back at each landed step, same as everything else in this backfill.
