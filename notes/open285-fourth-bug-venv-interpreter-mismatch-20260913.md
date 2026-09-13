# OPEN-285: PR #144 deployed, real run attempted -- a FOURTH bug found, os-people can't execute inside ddp-sync's container

PR #144 merged, pulled to `main` on this host, `ddp-sync` rebuilt/redeployed via
`systemctl restart ddp-sync` (its `ExecStart` already has `--build`). Confirmed `git` now
present (`/usr/bin/git`).

**Fourth real attempt at `openstates_people_refresh`.** `git pull` on the people repo genuinely
succeeded this time (real diff: renames/creates/deletes across many states' YAML files) --
progress. But **every single `os-people to-database <state>` call then failed**:

```
/opt/ddp-open-states/run-people-refresh.sh: line 23: /opt/ddp-open-states/.venv/bin/os-people: cannot execute: required file not found
```

**Real, dangerous gotcha: the overall job still reported `status: "completed"`, `duration_seconds:
11.4`** in Redis flow-status -- because each per-state `os-people` failure is caught by the
script's own `|| log "ERROR: ... failed (continuing)"` and never propagates. Anyone checking
just the flow-status key (not the actual `scraper.log` detail) would wrongly conclude this is
now working. It is not -- zero real people data was refreshed by this run.

**Root cause, confirmed directly:**
- `/opt/ddp-open-states/.venv/bin/os-people`'s shebang is
  `#!/opt/ddp-open-states/.venv/bin/python3.9`, a symlink to `/usr/bin/python3.9` -- which
  exists on this bare EC2 host (confirmed: `python3.9 --version` -> `3.9.2` directly on the
  host) but **does not exist inside `ddp-sync`'s own container** (`ddp-sync-ddp-sync-1` only
  has Python 3.11, no `python3.9` anywhere).
- This venv was built directly on the bare host, for host-level execution (matching how the
  *original* legacy cron ran it, outside any container). `/opt/ddp-open-states` is bind-mounted
  into `ddp-sync`'s container so the container can see the files, but a host-built venv's own
  interpreter symlink doesn't travel with a bind mount -- the container has no
  `/usr/bin/python3.9` to resolve it against.
- `activate.sh`'s `OS_PEOPLE`/`OS_VENV` vars always resolve to `$SCRIPT_DIR/.venv` (this same
  host-built venv), regardless of whether the caller is running inside a container or on bare
  metal.

**A working alternative already exists inside `ddp-sync`'s own image**: `/opt/venv-openstates/
bin/os-people` -- the same bundled OS-toolchain that OPEN-248 already added so `os-update`
would work inside this container. Confirmed directly: it runs fine (`os-people --help` returns
real output, no interpreter error). The gap is that `run-people-refresh.sh`/`activate.sh`
never learned to prefer this container-native path over the host venv when running inside a
container -- same class of problem OPEN-248 solved for `os-update`, just not extended to this
script.

**Not attempting this fix myself** -- it's the same shape as the first three (found, evidenced,
handed off), but this one touches `activate.sh`'s environment-detection logic more broadly
(not just this one script), which felt like it deserved your review rather than me improvising
a container-vs-host detection heuristic on the fly. Still holding the legacy crontab removal
-- fourth real failure in a row now (dubious-ownership, hardcoded path, missing git, now this
venv/interpreter mismatch).
