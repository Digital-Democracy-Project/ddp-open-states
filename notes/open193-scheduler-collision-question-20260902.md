# OPEN-193 — ddp-sync built and runs, but its scheduler starts unconditionally; risk of colliding with wherever else it already runs

*Replies to `notes/open193-rds-password-rotated-restart-api-v3-20260902.md`.*

## Time-sensitive item first: api-v3 restart -- done and verified

`deploy/.env`'s `DATABASE_URL` re-rendered from the rotated secret (142 chars, never printed).
Container recreated scoped to `api` only (`--no-deps`, `ddp-openstates-redis-1`'s start time
confirmed unchanged before/after, same safety pattern `refresh-api-v3.sh` already uses). Healthy
within ~15s, and confirmed with a real query, not just process-up: `GET /bills?jurisdiction=
Florida&per_page=1` returned real data (FL HB 519) through the recreated container. Running
clean on the new credential.

## ddp-sync: built, and it runs -- but found something before going further

Built per the decided shape: `infrastructure/Dockerfile` (python:3.11-slim-bookworm, non-root
user, `pip install .` from `pyproject.toml` directly -- no lock file to manage), 
`infrastructure/docker-compose.prod.yml` (joins `ddp-broker-py_default` externally, Redis DB 3 --
confirmed 0/1/2 are Celery broker+result/Django cache/celery_once respectively, in
`ddpbroker/settings/base.py`), `infrastructure/render-env.sh` (host-side secret resolution,
`ddp-sync/credentials` + the RDS secret -> a git-ignored `.env`, since the container turned out
to reach Secrets Manager directly anyway -- `config_source` came back `"secrets_manager"` on its
own health check, so the rendered `.env` is a harmless redundant fallback, not load-bearing), and
`infrastructure/ddp-sync.service` (Docker-Compose-oneshot, matching `ddp-broker.service`'s
pattern exactly, `Requires=docker.service ddp-broker.service`).

Image builds clean. Installed + started the systemd unit; health check passed
(`{"status":"healthy", ..., "config_source":"secrets_manager", "scheduler":{"running":true,
"jobs":10,...}}`).

**That `scheduler.running: true` is the problem.** `scripts/start-ddp-sync.sh` has a comment and
an `export SCHEDULER_ENABLED=true` with reasoning attached ("must be enabled explicitly so
accidental restarts on EC2 don't result in two schedulers fighting over the same Redis jobs") --
but `SCHEDULER_ENABLED` doesn't appear anywhere in `src/ddp_sync/` at all (grepped the whole
tree). The scheduler starts unconditionally whenever the process does; that script's own safety
claim doesn't match what the code actually does. `GET /ddp-sync/v1/schedule` showed all 10 jobs
already live: `voatz_user_sync` (every 30 min), `daily_bill_sync` (cron, next 04:00 UTC),
several weekly Webflow jobs, `voatz_full_sync` (monthly).

Stopped the container within ~43 seconds of starting it -- checked every job's `next_run`
against that window first; none had fired (`voatz_user_sync`'s was 30 min out, matching "just
scheduled," not "just ran"). So nothing actually executed this time, but that was luck of the
timing, not anything this deployment enforced.

## The actual question

Does `ddp-sync` already run this same scheduler somewhere else today -- the Mac Studio, or
wherever it currently lives -- for these same jobs (Voatz->Brevo sync, daily bill sync, the
Webflow jobs)? If yes: this EC2 instance would be a second, fully independent scheduler with no
shared coordination (this box's Redis is `ddp-broker-py`'s, a different instance entirely from
wherever the existing copy runs), so leaving it up past a job's interval risks real duplicate
processing -- duplicate Brevo syncs, duplicate Webflow writes, not just a cosmetic double-log.

This wasn't part of what OPEN-193 asked for (the FL scrape canary only needs the FastAPI app +
the manual `/trigger/openstates-scrape/<state>` endpoint reachable, not the general-purpose
scheduler running at all) -- so before bringing this container back up, need one of:

1. Confirmation no other instance is actually running these jobs today, or
2. A real code change (a `ddp-sync` PR) making the scheduler actually skippable -- the
   `SCHEDULER_ENABLED` gate `start-ddp-sync.sh` already assumes exists, added for real -- so this
   instance can run API-only for the canary, or
3. Some other existing safeguard I'm not aware of that already prevents this collision.

Left the container stopped in the meantime; systemd unit is installed and enabled but not
running.
