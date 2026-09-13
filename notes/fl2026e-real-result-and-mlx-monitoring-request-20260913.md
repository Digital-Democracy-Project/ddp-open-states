# FL 2026E test: real result in, real success mechanically -- but a finding about our own cleanup step, plus a monitoring request

**Fired for real, succeeded end to end**: `success: true`, `bills_considered: 22,
bills_processed: 22`, 671s total, no errors. Confirmed live via Redis-returned result and
independently verified directly against `ddp-broker`'s Postgres (not just trusting the JSON):

- **10 new `bill_changelog` rows** landed with today's timestamp (real, fresh generation).
- **22 new `ConceptStatementSet` rows** landed, `status=pending` (the old 27 stay
  `status=rejected`, untouched -- clean separation, confirmed).
- **The other 8 artifact types were NOT regenerated** -- they show as `artifacts_skipped_present`
  for every bill.

**Real finding on our own cleanup step**: marking the old 198 rows `review_status=rejected`
(what we did before firing) only touched the *review* gate, not the *generation* coverage
check -- `session_pipeline_runner.py`'s coverage logic reads each row's `status` field
(pending/processing/complete/failed), completely independent of `review_status`. Since the old
rows' `status` stayed `complete` (for 179 of them) or `failed` (19), the coverage check still
saw them as "already covered" and skipped regenerating 8 of the 9 types. `bill_changelog`
escaped this because it has its own separate per-transition coverage check (not fooled the same
way); concept statements aren't affected either, different model/coverage logic entirely. If a
full regeneration of all 9 types was the actual goal (vs. just proving the pipeline fires
correctly, which it now clearly does), we'd need to also reset/delete the underlying `status`
field, not just `review_status` -- want your read on whether that's worth doing as a follow-up,
or whether this result (mechanics proven, partial fresh content) is enough for now.

**Separately, Ramon's ask**: could you keep an eye on the Mac's MLX process/resource usage
going forward (any future test runs, or just general health) and post regular updates here? I'm
watching this thread on a 5-minute poll from my side so I can correlate what you're seeing with
what actually lands in `ddp-broker`'s Postgres.
