# Ramon: reboot RDS now (explicit go-ahead, real-time)

Ramon just gave explicit, real-time authorization to proceed with the RDS parameter-group
change + reboot -- the one this whole OPEN-269 epic has been blocked on
(`rds.logical_replication` / `wal_level=logical`, per your own `01-inspect.sql` results,
`notes/open271-01-inspect-results-20260911.md`).

This session has no RDS access at all (confirmed again just now: `AccessDenied` on even
`rds:DescribeDBInstances`), so this needs you to actually execute it.

## What's known about timing, from this side

- The `us` `refresh-extraction --commit` retry is **not currently running** -- it failed
  ~56% through and you're holding it pending Ramon's go-ahead on the retry specifically
  (separate from this reboot go-ahead). See `notes/us-refresh-extraction-progress-check-
  20260911.md`.
- I don't have visibility into anything else that might be actively writing to RDS right
  now (no RDS access, and no visibility into OPEN-193's Fargate load schedule) -- please do
  your own live check (CloudWatch + `pg_stat_activity`, same as you've done before other
  risky steps this session) before actually triggering the reboot, exactly as you've been
  doing already. Don't take "nothing known to be running" from this note as a substitute for
  that.

## What to do

Proceed with `ops/postgres-replica/rds/01-inspect.sql` → the parameter-group change/reboot →
re-confirm `wal_level=logical` and `rds.logical_replication=on` afterward, per the runbook in
`ops/postgres-replica/rds/README.md`. Report back here once it's done (or if anything blocks
it) so OPEN-271's actual RDS-side setup (`02-setup.sh`, `03-verify-role-can-read.sh`) can
finally run for real, unblocking OPEN-272/273/274/275/276's real execution too.
