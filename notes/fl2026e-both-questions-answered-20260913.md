# FL 2026E test: both questions confirmed, one correction to your own read

**Q1 -- one call, both outputs: confirmed correct.** Traced it directly:
`trigger_scraper_session_pipeline` (`scraper_triggered_legbot.py:76`) calls
`run_legbot_pipeline` exactly once, passing `artifact_types` (the 9 types) and
`include_concept_statements=True` as arguments to that same single call --
`run_legbot_pipeline` itself threads `include_concept_statements` through its own
per-bill processing (`session_pipeline_runner.py`, e.g. line 787). One request, both
kinds of output, no second call needed. Your read was right.

**Q2 -- review status: your read needs a correction.** The serializer's own docstring
calls `BILL_ARTIFACT_REQUIRE_REVIEW`/`CONCEPT_STATEMENT_REQUIRE_REVIEW` a "dev-only
kill-switch" (code default is `True`, i.e. require review), which is what led to the
`pending_review`/`pending` assumption. But I checked the actual **live production
container** (`ddpbroker-web-1`, `docker inspect`, not just the `.env` file on disk) and
both are explicitly overridden: `BILL_ARTIFACT_REQUIRE_REVIEW=false`,
`CONCEPT_STATEMENT_REQUIRE_REVIEW=False`. **Confirmed directly with Ramon just now: this
is the deliberate, wanted production setting, not a misconfiguration.**

So the real answer: new rows from this test will land **already approved/published**
(`BillArtifact.review_status=approved`, `ConceptStatementSet.status=published`), visible
immediately, not sitting in a review queue. Worth knowing before firing, since that's a
different operational picture than "generate now, review later" -- these 22 bills' new
artifacts/concept statements go live on the public site the moment the pipeline run
completes, no manual approval step in between.
