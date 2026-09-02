# OPEN-193/SYNC-51 — per-task flags merged; final .env list for the EC2-broker host

*Replies to `notes/open193-scheduler-collision-question-20260902.md`.*

`ddp-sync` PR #109 (SYNC-51's per-task `.env` enable flags) is merged to `main` as of
2026-09-02 04:16 UTC -- pull fresh before building the Docker image, since it also picked up a
12th flag (`session_pipeline_batch_enabled`) an independent review round caught missing: SYNC-9's
session-targeted BillArtifact batch job had no cross-host overlap lock of its own
(`run_scheduled_session_pipeline()` calls `run_legbot_pipeline()` directly, not through SYNC-48's
overlap-safe wrapper), so it needed the same env-flag protection as everything else here.

Also settles the direction question from your last note: there's no single canonical `ddp-sync`
instance to migrate to. It runs from multiple hosts at once now, each enabled for only its
locally-appropriate tasks -- see Jira SYNC-11 (corrected 2026-09-02) for the full account.

## Final `.env` for this host

All 12 flags default `true` (matching every job that currently runs unconditionally or per the
shared YAML). This host wants **only** the OpenStates scrape trigger, so set every other flag to
`false` explicitly:

```
BILL_SYNC_ENABLED=false
LEGISLATOR_SYNC_ENABLED=false
LEGISLATOR_BIO_SYNC_ENABLED=false
ORGANIZATION_SYNC_ENABLED=false
VOATZ_SYNC_ENABLED=false
WEBFLOW_BATCH_ENABLED=false
VOTEBOT_EVAL_ENABLED=false
API_HEALTH_CHECK_ENABLED=false
SESSION_PIPELINE_BATCH_ENABLED=false
# OPENSTATES_SCRAPE_ENABLED left unset (defaults true) -- this is the one job this host owns
# OPENSTATES_ARCHIVE_ENABLED and MI_COOKIE_PUBLISH_ENABLED -- your call whether this host should
# also own these two; they're OpenStates-domain, not Voatz/Webflow/LegBot, so plausible either way
```

Also still queued from the last round: the Redis logical-DB check (confirm Celery's actual DB
number before wiring `ddp-sync` onto a different one) and the Docker/systemd packaging itself,
matching `ddp-broker-py`'s compose+oneshot-wrapper pattern.
