# wa: what I need for a real spot-check

The `refresh-extraction wa --commit` summary you posted (`bills_with_stale_docs=3411
stale_docs=5818 diffs_corrected=4538 docs_skipped=0 docs_refused=0`) is aggregate counts only
-- there's nothing in it I can independently verify. Per the sequence Ramon spelled out in
`wa-proceed-instructions-20260911.md`, the next two steps are still outstanding:

1. **A fresh `recompute-diff-order wa --dry-run`** -- the one you already have
   (`unchanged=7098 corrected=4538 nulled=0`) was taken *before* this refresh-extraction
   commit, so it doesn't reflect the real post-refresh numbers. Run it again now.

2. **Send an actual spot-check sample**, same shape as mi/fl/va, not just the summary line:
   - At least one `nulled` document and a handful of `corrected` documents.
   - For each: the bill's identifier (full `ocd-bill/...` id), the `doc_id`, `version_note`,
     `media_type`, the diff's current stored length (chars), and the proposed new length.
   - If a document went from having a diff to `nulled` (or vice versa), say so explicitly --
     that's the case most worth checking by hand.

I'll verify these against the Mac's own copy before recommending a go-ahead for
`recompute-diff-order wa --commit`, same as every other jurisdiction in this backfill --
this step doesn't get skipped for `wa`.
