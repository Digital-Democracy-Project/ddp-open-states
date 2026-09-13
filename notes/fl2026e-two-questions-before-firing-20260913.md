# FL 2026E test: two things to confirm before we fire, Ramon wants your direct confirmation

Step 1 (marking the 198 old BillArtifact + 27 old ConceptStatementSet rows as rejected,
attributed to Ramon's own new `ramon.perez` account) is done and verified. Holding on step 2
(the real WireGuard trigger) for these two confirmations:

**1. Double-check: does one call to `POST /trigger/scraper-session-legbot` really produce
BOTH the 9 artifact types AND concept statements together, in the same pipeline run?**

My own read of `triggers.py`'s `trigger_scraper_session_legbot` handler: it calls
`trigger_scraper_session_pipeline(jurisdiction_iso2, session_code,
settings.legbot_scrape_completion_trigger_artifact_types, False,
settings.legbot_scrape_completion_trigger_limit,
include_concept_statements=settings.legbot_scrape_completion_trigger_include_concept_statements,
...)` -- both `artifact_types` and `include_concept_statements=True` passed as separate
arguments to the SAME function call, so my read is: yes, one request, both kinds of output, no
second call needed. Please confirm this is actually correct (or correct me) before we treat it
as settled.

**2. What review/approval status will the new rows land with in `ddp-broker`'s production
Postgres -- `pending_review` or `approved`?**

Checked `bill_artifact_generation.py` on this end -- didn't find an explicit
`review_status`/`status` write in the generation code itself, which would mean it falls
through to `BillArtifact`'s own model default (`pending_review`) and `ConceptStatementSet`'s
own default (`pending`, matching what the old test rows already had before we marked them
rejected) -- but the actual write happens via an API call to `ddp-broker`
(`ddp_broker_api_base`/`ddp_broker_api_token`), and I haven't traced that broker-side endpoint
to confirm it doesn't override the default somewhere. Could you confirm definitively whether
the new rows will land as `pending_review`/`pending` (needing a human review pass before
they're visible on the public site, matching what BROKER-100's own gate requires) or something
else? This matters for what we should expect to see immediately after the test vs. what needs
a manual review step afterward.

Holding at Ramon's direction until both are confirmed.
