# va/wa/us dry-run results — incremental update (3 of 5 landed, 2 still running)

## Landed so far

**va recompute-diff-order --dry-run:** `4380 bills checked | unchanged=9161 corrected=14553
nulled=1827` -- much higher correction rate than any jurisdiction so far (corrected+nulled
exceeds unchanged). Investigated directly rather than treating it as an anomaly: sampled
real docs via `recompute_bill_diff_order()` -- scanning just the first 512 bills already
found 428 with at least one correction (a near-universal hit rate). This matches the
codebase's own documented finding (`text_extract.py`, OPEN-34's investigation): VA's
`BillVersion` walk order is *backward*, already confirmed at 604-row scale by OPEN-33.
Concretely: several "Enrolled"-stage diffs shrink dramatically under the fix (9249->897
chars, 4204->754 chars) -- exactly what you'd expect when a diff was previously computed
against the wrong (backward-ordered) prior version and is now correctly diffed against the
true immediately-preceding version. One nulled sample ("House Amendment") is the
conservative STAGE_UNKNOWN fallback working as designed. **Read as: this is the intended,
large-scale correction for VA's known systemic ordering bug, not a red flag.**

**wa recompute-diff-order --dry-run:** `3411 bills checked | unchanged=7098 corrected=4538
nulled=0`.

**us recompute-diff-order --dry-run:** `37892 bills checked | unchanged=89509 corrected=14
nulled=0` -- very clean, as expected since US federal already has a real date-based
ordering fix (BillVersion.date populated ~99.4% of the time), so this code path barely
touches it.

## Still running

`wa refresh-extraction --dry-run` and `us refresh-extraction --dry-run` -- both confirmed
genuinely `RUNNING` on ECS (not stuck), just longer-running since refresh-extraction
re-fetches/re-extracts from S3 rather than working purely in-DB like recompute-diff-order.
Will report their numbers once they land.

## Recap: fl is done

`fl recompute-diff-order --commit` completed and was independently verified against the
real post-commit DB state (not just the summary line) -- see
`notes/fl-committed-verified-va-wa-us-dryruns-inflight-20260911.md`.

## Not committing anything yet

Waiting for the remaining 2 dry-runs plus explicit user go-ahead before any `--commit` step
on `va`/`wa`/`us`.
