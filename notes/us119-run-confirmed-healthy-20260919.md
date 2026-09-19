# Answering last night's ask: the US/119 run (redirected to Mac Studio) is confirmed healthy, in progress

Re: `us119-legbot-trigger-candidate-lookup-bug-20260919.md`'s ask #1 -- checked the Mac Studio
`ddp-sync`'s own log directly, since the triggering call never returned a response before that
session closed out.

**It's running, and it's healthy.** `run_id=f563665f-a010-42d9-afc2-2db1df7210be`,
`scraper_triggered_legbot_start jurisdiction_iso2=US session_code=119`, started
2026-09-19 01:43:03 EDT (= 05:43:03 UTC, matches the redirect timestamp exactly).

As of this check (2026-09-19 13:55 EDT, ~12h12m in):

* **1,698 of 18,494 bills complete** (9.2%).
* **Zero fatal errors** -- `error=None` on every `session_pipeline_bill_complete` line so far, no
  `session_pipeline_run_end` yet (still in progress, as expected for a run this size).
* Throughput ~139/hr overall average, ~82/hr in the most recent 30 minutes -- within normal
  variance for this pipeline, not a stall.
* 2,059 warning-level lines logged, all the known-benign shapes (`ddp-broker-py` rejecting
  writes for not-yet-imported bills, `no_version_identity` for unarchived text) -- same pattern
  seen on every prior full-session run, nothing new.

At current pace, the remaining ~16,800 bills would take roughly 5-8 days -- this is the full
18,494-bill US session (much larger than MI's 3,973 or WA's 3,411), so a multi-day run is
expected, not a sign of trouble.

**Given the WA run's own final numbers just came in** (`wa-legbot-backlog-run-complete-
20260918.md` -- 46.1% `bill_opposing_orgs`-only failures, 7.9% OPEN-297 gating-mismatch
failures), worth watching for the same two patterns showing up here once more of this run
completes, since neither has anything jurisdiction-specific about its root cause as currently
understood.

Not fixing `list_current_session_bill_candidates`'s missing RDS override myself -- flagging that
it's still open and unticketed, per the original note's ask #2.