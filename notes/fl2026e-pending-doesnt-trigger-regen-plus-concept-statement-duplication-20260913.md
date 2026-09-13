# FL 2026E: `status=pending` reset did NOT trigger regeneration -- and found a real ConceptStatementSet duplication bug

Reset the 198 old rows' `status` to `pending` exactly as instructed, confirmed the write
landed (Django's own `.update()` returned 198), re-fired the same `2026E` dispatch. Result:
**zero new BillArtifact rows generated, all 9 types (including bill_changelog this time) came
back `artifacts_skipped_present` for every one of the 22 bills.**

Verified directly against the DB afterward (not just trusting the JSON): all 198 rows are
still sitting at `status=pending` right now, and none were touched in the run's own time
window. So the coverage check really did see `pending` and skip -- confirmed against
`session_pipeline_runner.py`'s own coverage logic, which reads:

```
elif status is not None:
    ...
    # complete, pending, or processing -- has a row, don't retry.
    result["artifacts_skipped_present"].append(artifact_type)
```

`pending` is grouped with `complete`/`processing` as "has a row, don't retry" -- **not** a
signal that means "needs work." Only a genuinely *missing* row (`status is None`, i.e. no row
exists at all) or a `failed` row combined with `retry_failed=True` triggers real dispatch --
and this specific WireGuard/automated endpoint (`trigger_scraper_session_legbot`) doesn't
accept or pass `retry_failed` at all, hardcoded to the function's own default (`False`). So the
"reset status to pending" fix, followed exactly as given, doesn't actually achieve full
regeneration through this path -- the only way to force it here is deleting the rows outright,
which is exactly what we deliberately chose not to do earlier for comparison purposes.

**Separately, found while checking: `ConceptStatementSet` does NOT update in place.** Before
this run: 49 total (27 rejected + 22 pending from the first run). After this second run: **71
total (27 rejected + 44 pending)** -- a completely new batch of 22 was created on top of the
first batch, not overwritten. Several bills now have two pending `ConceptStatementSet` rows
instead of one. This looks like a real, separate bug (or at least an undocumented behavior
difference from `BillArtifact`'s intended update_or_create-on-natural-key pattern) -- worth
knowing about regardless of what we decide for the BillArtifact regeneration question, since it
means every repeat dispatch through this path silently accumulates duplicate concept-statement
rows.

**Not taking further action until we hear back.** Options as I see them, not prescribing one:
1. Actually delete the 198 rows now, accepting the loss of "keep for comparison," since that's
   the only way this specific endpoint will regenerate them for real.
2. A code change to let this automated path pass `retry_failed=True` (or some other explicit
   "force regeneration" signal) for a deliberate test like this one, without touching the
   default behavior for real scheduled/automated callers.
3. Treat the first run's result (10 genuine new changelogs + real concept statements, proving
   the archiver-triggered pipeline fires and writes correctly end to end) as sufficient
   confirmation on its own, and not chase full-9-type regeneration further for this test.

Also flagging the ConceptStatementSet duplication as its own thing to look at, independent of
whichever option we pick above.
