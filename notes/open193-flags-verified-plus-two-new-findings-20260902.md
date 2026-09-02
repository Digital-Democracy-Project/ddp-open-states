# OPEN-193 — PR #110 confirmed fixed, but re-verifying surfaced two more real issues before this host could safely run

*Replies to `notes/open193-pr110-merged-please-reverify-20260902.md`.*

## PR #110: confirmed fixed

Pulled latest, rebuilt, restarted. With all 9 explicit flags set `false`:
`Scheduler started with 0 jobs` in the container logs, and `GET /ddp-sync/v1/schedule` returned
`"jobs": []`. The override layer works exactly as intended, regardless of `config_source` being
`secrets_manager`. Confirmed on the exact host that surfaced the bug, as asked.

## Finding 1: `OPENSTATES_SCRAPE_ENABLED` unset/true is much bigger than "the one job this host owns"

The original flag list said to leave this one unset (defaults `true`) since it's "the one job
this host owns." Left unset, restarting registered **six recurring scheduled jobs**:
`openstates_patch_refresh`, `openstates_fl_scrape` (weekly), `openstates_wa_scrape` (weekly),
`openstates_usa_scrape` (weekly), `openstates_secondary_scrapes` (`va, mi, ma, ut, az, nc`,
weekly -- MI included), `openstates_people_refresh` (weekly). Left running, this would
independently re-scrape those same jurisdictions on its own schedule, with zero coordination
with whatever already runs them elsewhere -- not a cosmetic risk, a real duplicate-scrape one
(worse for MI specifically, given how WAF-sensitive it already is).

Stopped the container before any of the six could fire (all had future cron/weekly next-runs,
none had elapsed in the ~20s window). Checked whether this also affects OPEN-193's actual need
-- it doesn't: `POST /trigger/openstates-scrape/{target}` (`api/routes/triggers.py:825`) never
reads `settings.openstates_scrape_enabled` at all; it's a separate, always-on code path that
just reads the sync-config dict directly and runs on demand. So set
`OPENSTATES_SCRAPE_ENABLED=false` here too (not left unset) -- disables all six scheduled jobs,
changes nothing about the manual FL trigger OPEN-193 actually needs. Re-verified:
`Scheduler started with 0 jobs` with this change in place.

## Finding 2: separately, also caught a packaging gap of my own -- fixed, not a code bug

`config/sync_schedule.yaml` (everything this whole OPEN-193 thread verified -- cluster,
subnets, security group, etc.) was never reaching the container at all --
`infrastructure/Dockerfile` only `COPY`s `pyproject.toml` + `src/`, so `scheduler.py`'s
`_load_sync_config()` silently fell back to its own built-in defaults ("Sync config not found
... using defaults"). This wasn't a code bug, just a gap in what I built -- fixed by mounting
`../config:/app/config:ro` in `docker-compose.prod.yml` (read-only, no rebuild needed for a
future config change, matching how this file has always been edited via PR). Confirmed fixed:
logs now show `Loaded sync config from /app/config/sync_schedule.yaml`.

## Finding 3: same root-cause bug as PR #110 fixed, but for `redis_url` -- not yet fixed

`REDIS_URL=redis://redis:6379/3` is correctly set at the container's OS environment level
(confirmed via `docker exec ... env`), but the app still tries `localhost:6379` and falls back
to in-memory state. Same class of bug PR #110 just fixed for the 12 task flags: the
`ddp-sync/credentials` secret has its own `redis_url` key (`redis://localhost:6379/0`, its
stored default), and since `config_source` is `secrets_manager` here, that value wins over the
real environment -- `redis_url` isn't one of the 12 flags the override pass covers. Not blocking
for OPEN-193 specifically (the manual trigger's Redis use -- `ddp:flow:openstates_*` status
writes -- degrades to in-memory rather than failing outright), but it's the identical pattern,
and it means this host's flow-status writes currently go nowhere any other process could see
them. Flagging rather than fixing -- `redis_url` is host-specific in the exact same way the 12
flags are (different hosts need different Redis targets), so the fix is probably "extend the
same override mechanism to `redis_url`," but that's a call for whoever owns `config.py`, not
something to patch unilaterally given it's shared across every `ddp-sync` host.

## Current state

`ddp-sync` running on this host: 0 scheduled jobs, real `sync_schedule.yaml` values loaded and
reachable, health check passing. Redis still not connected (Finding 3). Have **not** called
`POST /trigger/openstates-scrape/fl` or touched `cloud_path.enabled` -- everything past "the
service runs correctly, scoped to nothing but the canary capability" still needs an explicit
go-ahead.
