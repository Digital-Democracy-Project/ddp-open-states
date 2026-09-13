# OPEN-285: PR #145 deployed, sixth attempt, sixth bug -- activate.sh overwrites the injected DATABASE_URL

Merged PR #145, pulled to `main`, restarted `ddp-sync` (confirmed clean, in-flight jobs
resumed correctly again). Sixth attempt, same exact error as before:
`psycopg2.OperationalError: connection to server at "localhost" (127.0.0.1), port 5433 failed:
Connection refused`.

**Root cause, precisely traced this time**: `run_people_refresh_job()`'s own code is correct --
confirmed directly it builds `{**os.environ, "DATABASE_URL": rds_url}` and passes that to the
`run-people-refresh.sh` subprocess. But `run-people-refresh.sh` sources `activate.sh` (twice,
before and after the `git pull`), and `activate.sh` has its own line:

```bash
export DATABASE_URL="${DATABASE_URL_OVERRIDE:-postgresql://openstates:openstates_dev@localhost:5433/openstates}"
```

This unconditionally overwrites whatever `DATABASE_URL` was inherited, falling back to the
local-dev default (`localhost:5433`) unless `DATABASE_URL_OVERRIDE` (a *different* variable)
is set. Per `activate.sh`'s own comment, this is deliberate (OPEN-159): "Keyed on
`DATABASE_URL_OVERRIDE` rather than honouring a pre-set `DATABASE_URL`, because [that] would
let any unrelated service's connection string silently become the [target]." So PR #145's fix
is correct at the Python level, but never reaches `os-people` -- `activate.sh`'s own safety
gate (built for a different reason) clobbers it right back out.

**The fix should set `DATABASE_URL_OVERRIDE`, not `DATABASE_URL`**, for this specific caller --
either in `run_people_refresh_job()`'s subprocess env, or in `run-people-refresh.sh` itself
before it sources `activate.sh`. Whichever you prefer; I didn't try either myself, same
reasoning as the last two (env/activation-logic changes, wanted this precisely traced and
handed off rather than patched live).

Confirmed all 9 states failed identically again (same error, real ~5-7s per state). Legacy
cron still in place -- sixth real failure in a row, but each one has been a genuinely
different, real, precisely-diagnosed cause, and progress keeps landing (venv fix and
exit-code fix from PR #252 are both still confirmed working correctly).
