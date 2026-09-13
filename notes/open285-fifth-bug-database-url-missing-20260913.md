# OPEN-285: PR #252 deployed, real progress -- but a fifth bug, os-people has no DATABASE_URL in ddp-sync's container

Merged PR #252, pulled to `main`, restarted `ddp-sync`. Confirmed the fix landed and works as
intended:

- The venv fix is real: the traceback now correctly shows `/opt/venv-openstates/bin/os-people`
  and `/opt/venv-openstates/lib/python3.9/...` -- no more "cannot execute" error. Progress.
- The exit-code fix is also real and working exactly as designed: this run took 51.0s (genuine
  per-state work, not an instant crash) and correctly reported `status: "failed"` in
  flow-status this time, instead of the previous silent "completed". Good -- this would now
  correctly reach OPEN-286's alerting too.

**But all 9 states still failed, on a new, fifth root cause**: `os-people` can't reach RDS at
all --

```
psycopg2.OperationalError: connection to server at "localhost" (127.0.0.1), port 5433 failed: Connection refused
```

`os-people` (via Django/openstates-core, same as `os-update`) reads a plain `DATABASE_URL` env
var, defaulting to localhost when unset. `ddp-sync`'s own container environment only has
`RDS_DATABASE_URL` (and the `RDS_HOST`/`RDS_PORT`/`RDS_DBNAME`/`RDS_CREDENTIALS_SECRET_ARN`
quartet) -- no plain `DATABASE_URL` at all. **Same exact naming mismatch already hit twice
today** for other tools in this same family: `cloud_loader.py`'s `os-update` call needed
`DATABASE_URL` explicitly passed when I ran it by hand earlier (for the MA recovery), and
this EC2 host's own `api-v3` container needed the equivalent `RESOLVE_RDS_LIVE`/`RDS_HOST`
wiring (OPEN-279) for the same underlying reason. This is a recurring pattern worth fixing
once, centrally, rather than patching each caller separately.

**Confirmed all 9 states failed identically** (fl/wa/us/va/mi/ma/ut/az/al), same error each
time, ~5-9s per state (a real connection-timeout attempt, not instant).

Not fixing this one myself either -- same reasoning as the venv fix, this touches shared
environment/wiring (either `run-people-refresh.sh` should export `DATABASE_URL` from
`RDS_DATABASE_URL` before invoking `os-people`, or `activate.sh`/the container's own env should
just set `DATABASE_URL` directly so every caller gets it for free). Your call on where the fix
belongs. Legacy cron still in place -- fifth real failure in a row now, but real, visible
progress each time.
