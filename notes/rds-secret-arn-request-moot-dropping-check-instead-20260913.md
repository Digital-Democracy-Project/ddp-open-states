# Retraction: don't chase the RDS_CREDENTIALS_SECRET_ARN value -- we're dropping the check instead

My earlier request (6146978) asked for the real `RDS_CREDENTIALS_SECRET_ARN` value.
Please don't spend more effort on that -- Ramon made a different call after I traced
what "trust the health check instead" would actually require (OPEN-274's script also
needs its own live RDS credential, never configured, never run against real RDS,
not even scheduled).

**Decision: drop the per-bill RDS content-hash check entirely for now, trust logical
replication's own mechanics (already verified working, OPEN-270-274), revisit both
this check and OPEN-274 properly afterward** (OPEN-274 reopened with the real
remaining scope recorded).

Real, actionable status: `ddp-sync` PR #150 (`fix/OPEN-289-defer-rds-freshness-content-check`)
adds `REPLICA_FRESHNESS_CONTENT_CHECK_ENABLED` (default `true`) to make this
independently toggleable, keeping the existing allowlist gate fully intact. Full
suite green (1244 passed), one round of pm-review triaged and applied. Not merging
it myself (my own PR) -- ready whenever Ramon or another reviewer wants to land it.

Once merged and deployed, I'll set `REPLICA_FRESHNESS_CONTENT_CHECK_ENABLED=false` in
the Mac's `.env` and the FL 2026E test should be unblocked with no RDS credential
needed on the Mac's side at all for this specific check.
