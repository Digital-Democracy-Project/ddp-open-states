# RDS reboot complete -- rds.logical_replication is on, OPEN-271's hard blocker cleared

Ramon authorized this and I executed it, with a granted IAM policy expansion
(`rds:Describe*` + parameter-group/reboot actions scoped to the `ddp-openstates` instance).

## What happened

- `ddp-openstates` was on `default.postgres16` -- the AWS-managed default group, which
  **cannot be modified in place** (confirmed by a real `CopyDBParameterGroup` failure: its
  dot-separated name fails general identifier validation as a copy source). Worked around by
  creating a fresh custom group from scratch instead (`aws rds create-db-parameter-group
  --db-parameter-group-family postgres16`), which starts from the same engine defaults.
- Created `ddp-openstates-logrep`, set `rds.logical_replication=1` on it
  (`ApplyMethod=pending-reboot`, since it's a static parameter), associated it with the
  instance (`modify-db-instance --apply-immediately`), confirmed the association reached
  `in-sync` before rebooting.
- **Confirmed RDS was genuinely quiet immediately before rebooting**: `pg_stat_activity`
  showed only RDS's own background connections (no app connections at all), and
  `ecs list-tasks --cluster ddp-scrapers` returned zero running tasks. Next scheduled
  ddp-sync job wasn't until 01:00 UTC, hours away.
- Rebooted (`aws rds reboot-db-instance`), waited for `DBInstanceStatus` back to
  `available` and the parameter group back to `in-sync`.

## Verified directly afterward (not just trusted the API response)

```
wal_level = logical
rds.logical_replication = on
```

Both correct. **OPEN-271's hard blocker is cleared** -- `02-setup.sh` and
`03-verify-role-can-read.sh` can now run for real against production RDS, unblocking
OPEN-272 through OPEN-276's actual execution too.

## Not done yet

Haven't run `00-generate-role-secret.sh`/`02-setup.sh`/`03-verify-role-can-read.sh`
themselves -- that's the next ask, whenever you want me to proceed. Also still holding on
retrying `refresh-extraction us --commit` (the ~56%-done backfill retry) pending explicit
go-ahead, unrelated to this reboot but worth remembering it's still open.
