# wa's post-commit recompute-diff-order dry-run: zero corrections, and here's why

Ran the fresh `recompute-diff-order wa --dry-run` you asked for (post `refresh-extraction
--commit`):

`wa: [DRY RUN] 3411 bills checked | unchanged=11636 corrected=0 nulled=0`

Zero corrections, zero nulled -- a big change from the pre-refresh-extraction number
(`corrected=4538`). Before reporting this as either good or concerning, traced the actual
code rather than assuming:

`refresh_extraction()`'s **commit** path (`text_extract.py:2706`) already calls
`recompute_bill_diff_order(bill)` internally for every bill whose `raw_text` it just
updated -- the diff-order fix is folded into the refresh-extraction commit itself, not a
separate step. The function's own docstring confirms this is intentional: "Dry run reports
how many documents are stale. It deliberately does NOT predict the diff recompute, because
`recompute_bill_diff_order` reads `raw_text` from the database -- with nothing committed it
would be recomputing against the stale text."

So `wa`'s `refresh-extraction --commit` already applied everything a separate
`recompute-diff-order --commit` would have done. This fresh dry-run's `corrected=0` is the
expected confirmation nothing's left to fix -- not a discrepancy, not `ut`-style scope
confusion (unlike `ut`, `wa` DID have `refresh-extraction` in its plan scope from the start,
so this genuinely is the completion of both required steps via one commit).

**No document-level sample exists to send** -- there's nothing changed to spot-check
against the Mac's copy. If you want independent confirmation `wa` is genuinely done, the
closest equivalent check would be re-running `recompute_bill_diff_order()` on a handful of
real `wa` bills against the Mac's own copy and confirming it also reports zero changes
there (same shape as your earlier `va` check, but expecting `changed=[]` rather than a
match on proposed values) -- happy to pull specific bill IDs for that if useful, otherwise
treating `wa` as done here.

**Backfill status: `mi`, `ut`, `fl`, `va`, `wa` all done. Only `us` remains** --
`refresh-extraction us --commit` still running (started 12:30:59, ~3.5h in as of this note,
tracking the dry-run's ~4h precedent). Will report once it lands and, per the same logic
above, likely won't need a separate `recompute-diff-order us --commit` either -- worth
confirming with a fresh dry-run once the commit lands, but probably a formality at that
point.
