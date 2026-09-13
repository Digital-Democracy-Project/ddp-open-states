# MA's 2026-09-06 run: collection succeeded, load step failed -- real data is safely staged, not lost

Dug into the MA freshness gap flagged in `notes/open193-ac6-freshness-measurement-20260913.md`.
Root-caused as far as the available evidence allows.

**What actually happened, in order:**

1. MA's weekly Fargate collection ran fine, start-to-finish: `run_id=ma-cabb8f2478b7`,
   `status: "ok"`, `found: 11963` objects, `duration_s: 28660` (~7h58m) -- confirmed directly
   from the task's own CloudWatch log
   (`scraper/scraper/45f3ccabc39847c0b3c8c587e429d595`), ending ~09:57 UTC.
2. Real data landed in S3 exactly where expected:
   `s3://ddp-openstates-scraper-memory/working-tier/ma/ma-cabb8f2478b7/` -- manifest written
   10:04:33 UTC, individual bill/vote_event/organization/jurisdiction JSON objects all present.
   **This data is not lost.**
3. ~21 minutes later (10:25:31 UTC), `ddp-sync` recorded the overall run as failed:
   `{"success": false, "failure_reason": "nonzero_exit_other"}` in
   `ddp:flow_history:openstates_secondary_scrapes:ma`. Since collection itself reported success,
   this failure has to be in the **load step** (S3 -> RDS, runs inside `ddp-sync` on the EC2
   host, not as its own Fargate task) or in `ddp-sync`'s own orchestration around it.

**Could not find the underlying exception/traceback** -- `classify_failure_reason()`
(`openstates_scrape.py`) only stores a coarse bucket (`waf_block`/`timeout`/`network_error`/
`nonzero_exit_other`), not the real error text, in the persisted flow-history record. The
richer detail (subprocess stderr tail) only ever lived in `ddp-sync-ddp-sync-1`'s own stdout,
which has since rotated past 2026-09-06 (container restarted at least once since, confirmed via
`docker logs` only reaching back to 2026-09-11). No Sentry or other durable error store is
configured for `ddp-sync` (checked its `.env` -- no `SENTRY_DSN`, unlike `ddp-broker-py`). So
the *what broke* is genuinely unrecoverable at this point without a repro -- flagging that gap
too: **this failure mode has no persisted detail beyond a coarse classification, which made
this investigation slower than it should have been.**

**Recovery is the known, already-used mechanism from OPEN-193's own precedent** (the FL
orphaned-manifest incident from earlier this epic): `cloud_loader.py ma ma-cabb8f2478b7` loads
directly from this exact manifest, by run_id, without re-scraping. Have NOT run this myself --
it's a real production RDS write, holding for explicit go-ahead same as every other real write
this session.

**Recommend:** (1) someone with the right access runs the by-run-id load recovery for
`ma-cabb8f2478b7` so this real, already-collected data actually reaches RDS rather than waiting
for next Sunday's run to re-collect it from scratch; (2) consider whether load-step failures
should persist more than a coarse classification string -- a stderr tail or exception summary
written alongside the flow-history entry (or to S3 next to the manifest) would make this kind
of investigation possible without racing the container's own log rotation.
