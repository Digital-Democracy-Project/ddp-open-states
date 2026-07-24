# PLAN — Production Hardening of the DDP OpenStates Services

**Status:** 🚧 BUILDING — core stack live & functionally tested (approved 2026-06-24; cleared 3
rounds of PM review at `ship_with_caution`).
**Built, live & verified:** WS0 (Colima 16GB/8CPU), WS0b (dedicated Postgres :5433 + migration
+ nightly backup + restore drill passed), WS1 (containerized; deploy files in `deploy/`), WS3
(live cutover on :8002 + scrapers repointed + launchd/watchdog/restart-policy supervision),
**WS4** (container log caps + in-script `scraper.log` rotation), **WS5** (health-probe readiness check, ddp-agents), **WS6** (health alerts
→ direct Slack, Zapier dropped, ddp-sync), **WS7** (incremental no-op fix + worktree lock;
scheduler verified). **Functional tests passed** (API 15/15 incl. auth/Redis + pagination;
API⇄:5433 consistency; restart-on-crash; scraper→:5433 write proof via sentinel).
**Pending:** WS8a (optional proxy tweaks, ddp-api), WS9 (off-host S3 — **blocked on AWS creds**),
old-DB decommission (after soak — see WS0b update below).
**Update 2026-07-17 — WS3 supervision superseded:** the GUI-LaunchAgent design described in
§5 WS3 below (verified-by-construction via auto-login + `RunAtLoad`) was replaced by a real
**system LaunchDaemon** for `com.ddp.openstates-api` and `com.ddp.openstates-db-backup`, as
Phase 2 of a separate `ddp-agents`-owned plan (`PLAN-cams-hardening-isolation.md`, shipped +
deployed). `start-os-api.sh` was hardened at the same time for the boot-order race this
creates against CAMS. No longer relies on auto-login or a logged-in GUI session; §5 and the
§8 checklist are updated in place below, but the workstream itself is tracked and owned in
the other repo's plan, not here.
**Earlier interim stopgap (superseded by the production stack above):** api-v3 first came back on
:8002 as the `docker-compose.stopgap.yml` container against the CAMS DB; it's retained only as
the one-command rollback during the soak.
**Author:** drafted 2026-06-24
**Related:** `PLAN-open-states.md` (architecture), `PLAN-incremental-scraping.md`, `RUNBOOK.md`

> **Two findings from building the stopgap (must carry into the full build):**
> 1. **psycopg2 / SCRAM (arm64).** The pinned `psycopg2-binary` links an old **libpq 9.6**
>    on Apple Silicon, which can't do Postgres 16 `scram-sha-256` auth → every DB query 500s
>    even with pydantic pinned. Fix: force-reinstall `psycopg2-binary==2.9.9` (bundles libpq
>    16). Baked into `Dockerfile.ddp`. **This affects the dedicated Postgres too** (also v16).
> 2. **Compose command:** this host has the standalone **`docker-compose`** (hyphen) binary,
>    not the `docker compose` plugin. All commands below should use `docker-compose`.
> 3. **File placement (local-fork convention):** the deploy files live in **`deploy/`** in the
>    DDP-owned `ddp-open-states` repo (build context → `../api-v3`), NOT inside the public
>    `api-v3/` checkout, which stays pristine. Inline `api-v3/…` paths in the workstreams below
>    predate this; the authoritative locations are in §9 and `RUNBOOK.md`.

---

## 1. Objective & scope

Make the local OpenStates replica robust enough that **production services can depend on
it**, as we increasingly fork the public OpenStates repos for DDP purposes.

**Decisions locked in (from review on 2026-06-24):**
- **Run model: Docker.** api-v3 runs as a container built from the repo's pinned
  `poetry.lock`, fully isolated from the host's `~/Library/Python/3.9` site-packages. It sits
  in its own `ddp-openstates` compose project and also attaches to `ddp-agents_default` to
  reach the shared Redis.
- **Scope: full production hardening** — isolation + supervision + multi-worker + log
  rotation + health monitoring/alerting + a runbook.
- **No Sentry.** We don't have a Sentry account. Instead we follow the existing DDP model:
  scheduled health checks that post **directly to Slack** on failure.
- **Cut Zapier out of alerting.** ddp-sync's current health alerts go through a Zapier
  webhook that reformats and forwards to Slack. We post straight to Slack with the existing
  `SLACK_BOT_TOKEN` (the same pattern `run-scrape.sh` and the bash health monitor already
  use), removing Zapier as a moving part.
- **Dedicated Postgres.** The openstates replica gets its **own** Postgres container
  (`ddp-openstates-postgres-1`, host port 5433) instead of sharing the CAMS database. The
  data is a rebuildable replica and nothing else connects to it directly, so the split is
  clean — and it removes the shared-connection-budget coupling entirely (WS0b).
- **Bump the Colima VM to 16 GB / 8 CPU.** The VM is currently capped at 8 GB / 4 CPU on a
  96 GB, 91%-idle host. Raising it gives headroom for the API container + the dedicated
  Postgres + future growth. Done once, as a coordinated step (it restarts all containers) — WS0.
- **Workers: 4** (raised from 3 now that Postgres is dedicated — WS2).

**In scope:** api-v3 (the read API on :8002), its supervision and observability, the
reverse proxy that fronts it, log rotation, and hardening of the scraper pipeline's
*operational* surface (alerting, locks, log growth).

**Out of scope (with rationale in §12):** containerizing the scrapers themselves;
migrating api-v3 to pydantic v2; the production cutover env-var flip (already specified in
`PLAN-open-states.md` §8).

---

## 2. Why this is needed — root-cause analysis

The immediate trigger: **every api-v3 endpoint currently returns HTTP 500.**

```
pydantic.errors.PydanticUserError: You must set the config attribute
`from_attributes=True` to use from_orm
```

### What actually happened
- api-v3 is written for **pydantic v1** — confirmed: every model in `api-v3/api/schemas.py`
  uses `class Config: orm_mode = True`, and `api-v3/api/pagination.py:127` calls
  `cls.ObjCls.from_orm(data)`. A v2 migration would touch all 504 lines of `schemas.py`
  plus pagination.
- The repo **pins pydantic to `1.10.2`** in `api-v3/poetry.lock`, and ships a `Dockerfile`
  that installs from that lock. **But the live deployment ignores all of it.**
- The actual process runs as a bare `uvicorn` against **shared user site-packages**:
  `start-os-api.sh` calls `~/Library/Python/3.9/bin/uvicorn`. That global environment is
  **shared with the scraper CLIs** (`os-update`, `os-people`, etc. also live in
  `~/Library/Python/3.9/bin`).
- At some point a `pip install` elsewhere upgraded **pydantic `1.10.2 → 2.13.4`** in that
  shared env. api-v3 silently broke on the next request and **stayed broken** because
  nothing rebuilds or pins it.

This is the textbook failure mode of "production service running off a shared, mutable,
unpinned interpreter." The drift was even anticipated in `PLAN-open-states.md` (lines
423/447 specify `api-v3/.venv/bin/uvicorn` — an isolated venv) but the deployed script
regressed to the global interpreter.

### Other fragility found during the read
| # | Finding | Impact |
|---|---|---|
| F1 | No process isolation (shared global interpreter) | The pydantic break; any future `pip` elsewhere can re-break it |
| F2 | Single uvicorn process, **no workers** | One slow request blocks others; no concurrency headroom for prod load |
| F3 | The `com.ddp.openstates-api` launchd job is **not even loaded** — the live process was started by hand (uptime 5+ days) | No supervised restart; a crash = silent outage |
| F4 | `logs/scraper.log` is **93 MB and unbounded**; `os-api.log` likewise | Disk-fill risk; unusable logs |
| F5 | Rate limiter reads `RRL_REDIS_HOST/PORT/DB`, but the plist sets only `REDIS_URL` | `REDIS_URL` is **ignored**; limiter silently falls back to `localhost:6379 db 0`. Works today by luck; will break in-container |
| F6 | The existing 5-min health monitor probes the FL *government-detail* endpoint — one of the routes that 500s | Liveness check is coupled to a heavy, currently-broken path; misses nothing now but is the wrong probe |
| F7 | `/metrics` (Prometheus) is exposed but **nothing scrapes it**; `SENTRY_URL` supported but **never set** | No metrics history, no error aggregation |
| F8 | `api-v3/_cache` (8.4k entries) and `_data` sit in the Docker build context | `COPY . /app` would bloat/slow every image build |

---

## 3. Target architecture

```
              ┌──────────────────── Mac Studio · Colima VM (16 GB / 8 CPU) ─────────────────────┐
              │                                                                                  │
 EC2 services─┼─►(WireGuard 10.0.0.8:8002)┐                                                      │
 (ddp-sync,   │                           ▼   compose: ddp-openstates          shared infra      │
  votebot)    │              ┌───────────────────────┐    ┌─────────────────────────┐           │
 ddp-broker──┼─►ddp-api ────┤  ddp-openstates-api    │───►│ ddp-openstates-postgres │ (NEW,      │
 (EC2,no WG)  │  proxy       │  (gunicorn + 4 uvicorn │    │ db: openstates · :5433  │  dedicated)│
              │ /openstates/*│   workers, pydantic    │    └─────────────────────────┘           │
              │ injects      │   1.10.2, restart:     │    ┌─────────────────────────┐           │
              │ x-api-key    │   unless-stopped)      │───►│ ddp-agents-redis-1      │ (shared,  │
              │              │   :80 → host :8002     │    │ rate-limit counters     │  redis)   │
              │              └───────────┬────────────┘    └─────────────────────────┘           │
              │                          │ /healthz + data probe                                  │
              │              ┌───────────▼────────────┐    ┌─────────────────────────┐           │
              │              │ health-check-slack.sh   │    │ ddp-agents-postgres-1   │           │
              │              │ (launchd, every 5 min)  │    │ (CAMS — now UNRELATED   │           │
              │              └───────────┬─────────────┘    │  to openstates)         │           │
              │                          └─► Slack #automation-errors └────────────────┘          │
              │   Scrapers (native) ── run-scrape.sh ◄── ddp-sync APScheduler ── DATABASE_URL→:5433│
              └──────────────────────────────────────────────────────────────────────────────────┘
```

Key properties:
- **api-v3 in a container** built from `poetry.lock` → pydantic pinned, isolated from host.
- **Dedicated Postgres, shared Redis.** The API + its own `ddp-openstates-postgres-1` live
  in one compose project (`ddp-openstates`); the API also attaches to `ddp-agents_default`
  to reach the shared `ddp-agents-redis-1` (rate-limit counters only). CAMS's
  `ddp-agents-postgres-1` is no longer in the openstates path.
- **Same external contract:** still `:8002` on the host (WireGuard 10.0.0.8:8002), so the
  ddp-api proxy, the cutover docs, and the health monitor all keep working unchanged.
- **Supervised:** container `restart: unless-stopped` for crashes; a launchd one-shot brings
  the stack up after Colima at boot; the Colima watchdog already supervises the VM.

---

## 4. Environment facts this plan relies on (verified 2026-06-24)

| Fact | Value | Source |
|---|---|---|
| DB container | `ddp-agents-postgres-1` (postgres:16-alpine) | `docker ps` |
| Redis container | `ddp-agents-redis-1` (redis:7-alpine) | `docker ps` |
| Network | `ddp-agents_default` (bridge, created by `ddp-agents/docker-compose.yml`, **not** external) | agent recon |
| openstates DB creds | user `openstates` / `<LOCAL_DEV_DB_PASSWORD>`, db `openstates` | `RUNBOOK.md` |
| api-v3 internal key | `00000000-0000-0000-0000-000000000001` | `RUNBOOK.md`, proxy code |
| Colima VM (current) | 8 GB / 4 CPU / 60 GB disk; ~1.9 GB of 7.7 GB used across 9 containers (→ bump to 16 GB / 8 CPU, WS0) | `colima list`, `docker stats` |
| Colima supervision | `com.ddp.colima` launchd → `ddp-agents/deployment/scripts/watch-colima.sh` (KeepAlive) | agent recon |
| Host | Mac Studio (Mac15,14), 96 GB RAM, 91% free, 0 swap | `sysctl`, `memory_pressure` |
| Existing health monitor | `ddp-agents/deployment/scripts/health-check-slack.sh` + `com.ddp.health-monitor.plist` (every 300s; already probes os-api on :8002; Slack-debounced via `/var/tmp/ddp-osapi-health.*`) | agent recon |
| Slack | `SLACK_BOT_TOKEN` in `ddp-agents/.env`; channel `#automation-errors` | `run-scrape.sh`, agent recon |
| Proxy | `ddp-api/app/routes/openstates_proxy.py` → `OPENSTATES_SERVICE_URL` (default `http://10.0.0.8:8002`); 30s timeout; maps ConnectError→502, ReadTimeout→504; passes other statuses through | agent recon |
| Base image | `bmltenabled/uvicorn-gunicorn-fastapi:python3.9-slim` (tiangolo-style; gunicorn + uvicorn workers; `MODULE_NAME=api.main`; serves :80) | `api-v3/Dockerfile` |

---

## 5. Workstreams

Ordered roughly by dependency. Each is independently reviewable. WS0 and WS0b are the
foundational infra steps and come before the api-v3 container.

### WS0 — Bump the Colima VM to 16 GB / 8 CPU (prerequisite)

**Why:** every container lives in the Colima VM, currently capped at **8 GB / 4 CPU** on a
**96 GB, 91%-idle** host. Measured VM usage is only ~1.9 GB of 7.7 GB across 9 containers,
so the API + a dedicated Postgres fit today — but the VM is sized far below the host, and
the 4-CPU cap is the tighter limit under load. Raise it once, deliberately.

**Heads-up — this restarts every container** (CAMS, broker, agents). The
`com.ddp.colima` watchdog (`watch-colima.sh`) will try to restart Colima if it sees it stop,
so the watchdog must be paused during the resize or it will race the manual restart.

**Maintenance window:** budget **~2–3 min of full-host container downtime** (CAMS, broker,
agents, and the api-v3 stopgap all bounce together while the VM restarts) — they auto-recover
via their own restart policies. Do it off-hours and outside a scrape-import window. Production
services still hit the live OpenStates API at this stage, so external user impact is limited
to other CAMS/broker consumers during the bounce — give them a heads-up.

```bash
# 1. Pause the watchdog so it doesn't fight the restart
launchctl bootout gui/$(id -u)/com.ddp.colima 2>/dev/null || true

# 2. Persist the new allocation (watchdog's bare `colima start` will read this afterward)
#    ~/.colima/default/colima.yaml :  cpu: 8   memory: 16   (disk: 60 unchanged)
# 3. Apply (stops + restarts the VM and all containers)
colima stop
colima start --cpu 8 --memory 16

# 4. Verify
colima list                                   # MEMORY 16GiB / CPUS 8
docker info --format '{{.NCPU}} CPU / {{.MemTotal}} bytes'
docker ps --format 'table {{.Names}}\t{{.Status}}'   # all healthy again

# 5. Re-arm the watchdog
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.ddp.colima.plist
```

**Acceptance:** `docker info` reports 8 CPU / ~16 GiB; all pre-existing containers
(CAMS + broker) return to healthy; watchdog re-loaded.

---

### WS0b — Dedicated Postgres for the openstates replica

**Why:** today the `openstates` db lives inside CAMS's `ddp-agents-postgres-1`, sharing one
100-connection limit, one cache, and one autovacuum with CAMS. Giving openstates its own
Postgres removes that coupling (an openstates problem stays an openstates problem) and lets
the API use more workers without starving CAMS. The split is low-risk here: the data is a
rebuildable replica and **nothing outside ddp-open-states connects to it directly** (verified
2026-06-24 — only the API, the scrapers' import, and `quality_check.py`).

> **Honest scope of the isolation:** it's still the same Mac and the same Colima VM, so this
> isolates *software* fault domains (connections, locks, autovacuum, cache, version,
> backup/restore) — **not** hardware or whole-VM disk-fill. Hardware HA would need a second
> machine; out of scope.

**Backup baseline (checked 2026-06-24):** the shared CAMS Postgres has **no backups today** —
`archive_mode=off`, `wal_level=replica`, no `pg_dump` cron/launchd job (the only "backup"
script, `ddp-agents/deployment/scripts/backup-artifacts.sh`, syncs CAMS *file* artifacts to
S3, not the DB). So moving openstates to a dedicated DB is **not a backup regression**, and
the small `pg_dump` below is a net improvement over the status quo. The `openstates` db is
**610 MB**, so dump/restore (both migration and nightly backup) runs in ~1–2 min.

**The `postgres` service is defined in `docker-compose.ddp.yml` (see WS1).** Host port
**5433** (5432 is taken by CAMS), own named volume `os_pg_data`, same `postgres:16-alpine`
image as the others.

**Migration (one-time dump → restore; pipe avoids temp files):**
```bash
cd ~/Developer/repos/ddp-open-states/api-v3

# 1. Bring up ONLY the new Postgres (creates an empty `openstates` db via POSTGRES_DB)
docker-compose -f docker-compose.ddp.yml up -d postgres

# 2. Copy the data across (pg_dump is read-only on the shared DB — needs approval).
#    --no-owner sidesteps any role mismatch; same role name so it's belt-and-suspenders.
docker exec ddp-agents-postgres-1 pg_dump -U openstates -Fc openstates \
  | docker exec -i ddp-openstates-postgres-1 pg_restore -U openstates -d openstates --no-owner

# 3. Sanity-check row counts match (bills/votes) between old and new
docker exec ddp-agents-postgres-1     psql -U openstates -d openstates -tAc \
  "SELECT count(*) FROM opencivicdata_bill;"
docker exec ddp-openstates-postgres-1 psql -U openstates -d openstates -tAc \
  "SELECT count(*) FROM opencivicdata_bill;"
```

**Repoint the native scrapers + tooling** to the new DB (they connect over the host port):

`activate.sh`
```bash
# was: postgresql://openstates:<LOCAL_DEV_DB_PASSWORD>@localhost:5432/openstates
export DATABASE_URL="postgresql://openstates:<LOCAL_DEV_DB_PASSWORD>@localhost:5433/openstates"
```
Also update the hardcoded default in `quality_check.py:37` (`localhost:5432` → `localhost:5433`)
so a forgotten `source activate.sh` doesn't silently hit the old DB.

**Backups (right-sized — the data is a rebuildable replica, so NO WAL/PITR).** Add a simple
nightly `pg_dump` of the dedicated DB for fast restore; this beats today's zero-backup state.
A small script + launchd job (mirrors the existing one-shot pattern):

`backup-openstates-db.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
OUT="/Users/agentsmith/Developer/repos/ddp-open-states/logs/db-backups"
mkdir -p "$OUT"
STAMP=$(date -u +%Y%m%d)
docker exec ddp-openstates-postgres-1 pg_dump -U openstates -Fc openstates \
  > "$OUT/openstates_${STAMP}.dump"
# keep 7 days
ls -1t "$OUT"/openstates_*.dump | tail -n +8 | xargs -r rm -f
```
Schedule daily via a `com.ddp.openstates-db-backup` launchd `StartCalendarInterval` job (or a
ddp-sync APScheduler job for consistency with the scrape schedule). Restore is
`docker exec -i ddp-openstates-postgres-1 pg_restore -U openstates -d openstates --clean --no-owner < <dump>`.
**RPO/RTO (stated plainly for an internal rebuildable replica):** RPO ≈ 1 day (nightly dump);
RTO ≈ minutes (restore the dump) — and in the worst case the data is fully re-derivable by
re-running the scrapers. That posture is appropriate here; we are not promising PITR.

**Off-host copy + restore drill:** local dumps share the Mac's disk with the live DB, so they
must also go off-host — see **WS9** (the S3 path was scaffolded for CAMS but never wired, so we
establish it here). **Ultimate fallback if a dump is unusable:** re-seed (`os-initdb` +
re-import) — the data is fully reproducible from the scrapers.

**The `:5433` consumers are exactly three** (verified 2026-06-24 — nothing else connects to the
openstates DB directly): (1) the api-v3 container (`DATABASE_URL` in compose), (2) the native
scrapers via `activate.sh`, (3) `quality_check.py`. Before decommissioning the old DB, rule out
any *hidden* consumer with a **repo-wide** grep, not just the three known files:
`grep -rn "5432/openstates" ~/Developer/repos 2>/dev/null` should return nothing (catches a
stray script/notebook still on :5432). Then confirm a scrape actually wrote to the new DB:
`docker exec ddp-openstates-postgres-1 psql -U openstates -d openstates -tAc \
"SELECT max(updated_at) FROM opencivicdata_bill;"` shows a timestamp newer than the cutover.

**Decommission (later, after a soak):** once the new DB has taken a few scrape cycles, the
3-consumer check above passes, and `quality_check.py` looks clean, drop the stale copy to
reclaim space: `docker exec ddp-agents-postgres-1 psql -U openstates -c "DROP DATABASE openstates;"` (optional).

**Acceptance:** row counts match post-restore; a manual `./run-scrape.sh` writes to :5433 and
the API serves the new rows; CAMS unaffected on :5432; the nightly `pg_dump` produces a
restorable `.dump`.

---

### WS1 — Containerize api-v3 (the core fix)

**Goal:** Run api-v3 from an isolated, pinned image, in the `ddp-openstates` compose project
alongside its dedicated Postgres (WS0b), attached to the shared network only for Redis. This
alone fixes the 500s permanently (F1) and removes the shared-interpreter failure mode.

**1a. Add `.dockerignore`** (fixes F8 — keeps the 8.4k-entry `_cache` out of the build):

`api-v3/.dockerignore`
```
.git
.venv
_cache
_data
**/__pycache__
*.pyc
*.pyo
.pytest_cache
api/tests
```

**1b. Add a DDP-specific compose file** (additive; does not touch upstream's
`docker-compose.yml`, which targets a different network/port for upstream dev):

`api-v3/docker-compose.ddp.yml`
```yaml
name: ddp-openstates

services:
  # Dedicated Postgres for the openstates replica (WS0b)
  postgres:
    image: postgres:16-alpine
    container_name: ddp-openstates-postgres-1
    restart: unless-stopped
    environment:
      POSTGRES_USER: openstates
      POSTGRES_PASSWORD: <LOCAL_DEV_DB_PASSWORD>
      POSTGRES_DB: openstates
    ports:
      - "0.0.0.0:5433:5432"   # 5432 is CAMS; native scrapers reach this DB on host :5433
    volumes:
      - os_pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U openstates"]
      interval: 5s
      timeout: 3s
      retries: 5
    logging:
      driver: json-file
      options: { max-size: "10m", max-file: "5" }

  api:
    build:
      context: .
      dockerfile: Dockerfile.ddp   # upstream Dockerfile + psycopg2-binary 2.9.9 (SCRAM/arm64 fix)
    image: ddp-openstates-api:local
    container_name: ddp-openstates-api-1
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      # Reach the dedicated Postgres by service name over this compose's own network
      DATABASE_URL: "postgresql://openstates:<LOCAL_DEV_DB_PASSWORD>@postgres:5432/openstates"
      # Redis stays shared — reached over ddp-agents_default by container name.
      # NOTE: rate_limiter.py reads RRL_REDIS_* — NOT REDIS_URL (see F5)
      RRL_REDIS_HOST: "ddp-agents-redis-1"
      RRL_REDIS_PORT: "6379"
      RRL_REDIS_DB: "1"
      WEB_CONCURRENCY: "4"          # dedicated DB → no shared-pool constraint (WS2)
      FORWARDED_ALLOW_IPS: "*"      # honour X-Forwarded-* from the ddp-api proxy / WireGuard
    ports:
      # Bind on all interfaces so WireGuard peers (10.0.0.8) can reach it; container serves :80
      - "0.0.0.0:8002:80"
    networks:
      - default            # this compose's network → reaches `postgres`
      - ddp-agents_default # shared network → reaches `ddp-agents-redis-1`
    healthcheck:
      # python is always present in the base image; curl may not be
      test: ["CMD-SHELL", "python -c \"import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:80/healthz', timeout=3).status==200 else 1)\""]
      interval: 15s
      timeout: 5s
      retries: 5
      start_period: 30s
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"

volumes:
  os_pg_data:

networks:
  default: {}                      # created by this compose (api <-> postgres)
  ddp-agents_default:
    external: true                 # owned by ddp-agents; must be up first (for Redis)
```

**Notes / decisions baked in:**
- **No source bind-mount.** Upstream's dev compose mounts `.:/app`; for prod we ship an
  immutable image (`COPY . /app` in the Dockerfile) and rebuild on change. Deterministic.
- **Two networks on `api`:** its own `default` for the dedicated Postgres, plus the external
  `ddp-agents_default` for the shared Redis. `external: true` means `ddp-agents` must be up
  first; the start script (WS3) checks for it and fails loud if missing.
- **`depends_on … service_healthy`** so the API never starts before its DB is accepting
  connections (avoids a crash-loop on boot).
- **Port mapping `8002:80`** preserves the existing external contract; no proxy/monitor/cutover changes needed.

**1c. Build & first run (after WS0b migration):**
```bash
cd ~/Developer/repos/ddp-open-states/api-v3
docker-compose -f docker-compose.ddp.yml build
docker-compose -f docker-compose.ddp.yml up -d           # brings up postgres (if not already) + api
# verify pinned pydantic inside the image
docker exec ddp-openstates-api-1 python -c "import pydantic; print(pydantic.VERSION)"   # expect 1.10.2
```

**Acceptance:** all four endpoints that 500 today return 200:
```bash
K="apikey=00000000-0000-0000-0000-000000000001"
for u in "healthz" "jurisdictions?$K&per_page=1" "bills?jurisdiction=fl&session=2026&$K&per_page=1" \
         "people?jurisdiction=fl&$K&per_page=1"; do
  curl -s -o /dev/null -w "%{http_code}  /$u\n" "http://localhost:8002/$u"
done
```

---

### WS2 — Multi-worker tuning (F2)

The base image runs **gunicorn with uvicorn workers**; worker count is set via
`WEB_CONCURRENCY` (the image also honours `WORKERS_PER_CORE`/`MAX_WORKERS` — verify the
fork's exact knobs on first build with `docker exec ddp-openstates-api-1 env | grep -i worker`).

**The shared-pool constraint is gone** now that Postgres is dedicated (WS0b). The connection
math is `WEB_CONCURRENCY × (pool_size 10 + max_overflow 7)`, i.e. `4 × 17 = 68` — comfortably
under the dedicated DB's default `max_connections=100`, with **no CAMS to compete with**. So:

- **`WEB_CONCURRENCY=4`** — locked in (8 vCPUs after WS0). Plenty for the proxy's serialized
  traffic and prod read load; revisit with metrics if needed.
- The previously-considered env-configurable pool patch (`DB_POOL_SIZE`/`DB_MAX_OVERFLOW`) is
  **no longer needed** — keep api-v3 strictly upstream, no code change. (If we ever want
  many more workers, that patch stays available on a `ddp-patches` branch per WS8b.)

**Acceptance:** under a short load test (e.g. `hey`/`ab` at modest concurrency), no
`QueuePool limit ... timed out` errors in container logs and `pg_stat_activity` for
`application_name='os_api_v3'` stays well under 100.

---

### WS3 — Supervision & boot order (F3)

> **✅ DONE, then superseded (2026-07-17).** The GUI LaunchAgent design below shipped
> 2026-06-24 and was accepted as verified-by-construction. It was then replaced outright by a
> **system LaunchDaemon** (`/Library/LaunchDaemons/com.ddp.openstates-api.plist` +
> `com.ddp.openstates-db-backup.plist`, installed via the `ddp-agents` `cams` CLI's
> `sudo cams install-daemons`, not a bare `launchctl bootstrap`) as Phase 2 of
> `ddp-agents/.../PLAN-cams-hardening-isolation.md` — the same GUI-agents-don't-reload-over-SSH
> fix already proven for `com.ddp.ddp-sync`. As a system daemon, `openstates-api` can now start
> *before* CAMS creates `ddp-agents_default` + `ddp-agents-redis-1`, so `start-os-api.sh` was
> rewritten with a bounded wait/retry (5s × 60 = 300s) for the Colima docker socket → network →
> redis, reached via `DOCKER_HOST=unix://.../docker.sock` (a system daemon has no GUI docker
> context). On timeout it exits non-zero so `KeepAlive={SuccessfulExit:false}` +
> `ThrottleInterval=30` relaunches it until CAMS is up, instead of dying silently. No longer
> depends on auto-login or a logged-in GUI session — the real gap called out in the original
> "Real sleep + reboot test" note below is closed by this migration, not by the sleep/reboot
> test itself (which is still undone; see §8).

**Goal:** the API comes back automatically after a crash, a Colima restart, or a Mac reboot
— with no manual `uvicorn` ever again.

Three layers (mirroring the existing `ddp-agents` pattern):
1. **Crash recovery:** `restart: unless-stopped` on the container (WS1).
2. **VM recovery:** the existing `com.ddp.colima` watchdog already restarts Colima.
3. **Boot bring-up:** a launchd one-shot that waits for Docker, verifies the shared network,
   and `docker compose up -d`. The container's restart policy handles everything after.

**3a. Replace `start-os-api.sh`** (currently runs bare `uvicorn`) with a compose launcher:

`start-os-api.sh` (proposed)
```bash
#!/usr/bin/env bash
set -euo pipefail
COMPOSE_DIR="/Users/agentsmith/Developer/repos/ddp-open-states/api-v3"
COMPOSE_FILE="docker-compose.ddp.yml"
LOG="/Users/agentsmith/Developer/repos/ddp-open-states/logs/os-api.log"

log() { echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ') [start-os-api] $*" | tee -a "$LOG"; }

# Wait for the Docker daemon (Colima may still be booting after a reboot)
attempts=0
until docker info >/dev/null 2>&1; do
    attempts=$((attempts + 1))
    [ "$attempts" -ge 60 ] && { log "ERROR: Docker not ready after 180s"; exit 1; }
    log "waiting for Docker daemon..."; sleep 3
done

# The shared network is owned by ddp-agents — fail loud if that stack isn't up
if ! docker network inspect ddp-agents_default >/dev/null 2>&1; then
    log "ERROR: network ddp-agents_default missing — is the ddp-agents stack up?"; exit 1
fi

cd "$COMPOSE_DIR"
log "Bringing up api-v3 (compose up -d)"
# Image is built ahead of time on deploy; do not --build here (slow at boot)
docker compose -f "$COMPOSE_FILE" up -d
log "api-v3 up; container restart policy now owns the lifecycle"
```

**3b. Replace the launchd plist** `~/Library/LaunchAgents/com.ddp.openstates-api.plist` —
change from a KeepAlive long-running uvicorn to a **one-shot at load/boot** (the container,
not launchd, stays alive):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>            <string>com.ddp.openstates-api</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/agentsmith/Developer/repos/ddp-open-states/start-os-api.sh</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key> <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
    <key>RunAtLoad</key>        <true/>
    <key>KeepAlive</key>        <false/>   <!-- one-shot; container has restart:unless-stopped -->
    <key>StandardOutPath</key>  <string>/Users/agentsmith/Developer/repos/ddp-open-states/logs/os-api.log</string>
    <key>StandardErrorPath</key><string>/Users/agentsmith/Developer/repos/ddp-open-states/logs/os-api.log</string>
</dict>
</plist>
```

**3c. Cutover sequence (during change window):**
```bash
# stop the hand-started bare uvicorn (PID was 12981 on :8002)
launchctl bootout gui/$(id -u)/com.ddp.openstates-api 2>/dev/null || true
pkill -f "uvicorn api.main:app" || true
# build + bring up container (WS1c), confirm :8002 healthy, then reload supervised job
launchctl bootout gui/$(id -u)/com.ddp.openstates-api 2>/dev/null || true
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.ddp.openstates-api.plist
```

**3d. Switchover safety — what we touch vs. what we leave alone.**
The switchover is deliberately *additive* to shared infrastructure:
- **We never restart or stop** the shared `ddp-agents-postgres-1`, `ddp-agents-redis-1`, or
  Colima itself. We only (a) stop our own hand-started uvicorn and (b) start a new container
  that *connects* to those existing services. So CAMS, ddp-broker-py, and anything else on
  the shared containers keep running untouched.
- **The only shared-resource impact** is up to ~51 new Postgres connections (WS2) and a few
  Redis keys under the `v3:` prefix (rate-limiter counters). Nothing destructive.

Pre-switchover, confirm what's currently using the shared services so we go in with eyes
open (these are read-only and safe to run anytime):
```bash
# What containers are up and who shares the network
docker ps --format 'table {{.Names}}\t{{.Status}}'
docker network inspect ddp-agents_default --format '{{range .Containers}}{{.Name}} {{end}}'

# Who is connected to the shared Postgres right now (needs approval — shared container)
docker exec ddp-agents-postgres-1 psql -U openstates -d openstates \
  -tAc "SELECT datname, application_name, count(*) FROM pg_stat_activity GROUP BY 1,2 ORDER BY 3 DESC;"

# Active scrape? (don't switch over mid-import)
tail -5 logs/scraper.log
curl -s -H "X-API-Key: <key>" http://localhost:8001/ddp-sync/v1/jobs   # next/last run times
```
Recommended window: not during a scrape-import (check `scraper.log`), though even then the
risk is only transient extra DB connections, not data loss.

**Acceptance:** `docker kill ddp-openstates-api-1` → container auto-restarts within seconds;
a Colima stop/start (or simulated reboot via `launchctl kickstart`) → API is back on :8002
without manual intervention; CAMS/broker health unaffected throughout.

**Real sleep + reboot test (don't rely on the simulation).** A Mac actually sleeps and reboots,
and the launchd-one-shot → Colima-watchdog → container-restart-policy chain is unproven through
those. Once: (1) `pmset sleepnow`, wake, confirm :8002 healthy with no manual steps and no
restart loop in `os-api.log`; (2) full `sudo reboot`, confirm Colima comes up, then api-v3
returns on its own. Watch for a supervision loop (launchd re-running while the container is
already up) — the one-shot + `docker-compose up -d` is idempotent, but verify it in the logs.

---

### WS4 — Log rotation (F4)

**House pattern (verified 2026-06-24):** CAMS and DDP Broker do **app-managed rotation** via
Python `logging.handlers.RotatingFileHandler` (CAMS 50 MB × 14; broker 50 MB × 5) and
**deliberately rejected `newsyslog`/`logrotate`** ("Python manages the fd internally; no
newsyslog/logrotate needed"). We mirror that "the app rotates its own logs, no external daemon,
no sudo" convention — **dropping the original `newsyslog` plan.**

**Container logs:** already capped by the `logging:` block in WS1 (json-file, 10 MB × 5) —
*better* than CAMS/broker, whose compose files don't cap container logs at all.

**Host log files** written by the shell layer:
- `logs/scraper.log` — the only real grower (hit 93 MB; truncated once to a `.gz` already).
- `logs/os-api.log` — now just the launchd one-shot's `compose up` output (negligible).

**4a. ✅ Immediate one-time cleanup — done** (89 MB archived to `scraper.log.20260624.gz`, truncated).

**4b. In-script rotation (no sudo, version-controlled).** `scraper.log` is written by *concurrent*
shell processes (`run-scrape.sh` per jurisdiction), so a Python handler doesn't fit; use a small
bash rotator called at the start of each `run-scrape.sh`. It uses **copy-then-truncate (same
inode)** so concurrent appenders keep writing safely, size-based at 50 MB (mirrors CAMS), keep 7
gzipped archives. No lock needed — copy-then-truncate + keep-N is race-tolerant.

```bash
rotate_scraper_log() {          # called once at the top of run-scrape.sh
    local f="$LOG_DIR/scraper.log" max=$((50 * 1024 * 1024))
    [ -f "$f" ] || return 0
    local size; size=$(stat -f%z "$f" 2>/dev/null || echo 0)
    [ "$size" -gt "$max" ] || return 0
    # copy-then-truncate in place (same inode) so concurrent tee/>> appenders keep writing
    gzip -c "$f" > "$f.$(date -u +%Y%m%dT%H%M%SZ).gz" 2>/dev/null && : > "$f"
    ls -1t "$f".*.gz 2>/dev/null | tail -n +8 | xargs rm -f 2>/dev/null || true
}
```

**Acceptance:** with a `scraper.log` over 50 MB, a `run-scrape.sh` invocation archives it to a
timestamped `.gz`, leaves `scraper.log` small, keeps ≤7 archives; a small log is left untouched;
concurrent invocations don't corrupt the file.

---

### WS5 — Health monitoring & alerting (F5, F6)

> **✅ DONE (2026-06-24, `ddp-agents` `e369864`).** `health-check-slack.sh`'s os-api check now
> does liveness (`/healthz`) + a DB-backed readiness query (`curl -sf` fails on a 500, `grep`
> guards a broken 200) — catches the "up but every query 500s" failure. No python dependency
> (root LaunchDaemon). F5 (`RRL_REDIS_*`) is set explicitly in the compose. Picks up on the
> daemon's next 5-min run; verified it reports os-api healthy.

We **enhance the existing monitor** rather than add a new one — `health-check-slack.sh`
already runs every 5 min, debounces via `/var/tmp/ddp-osapi-health.*`, and posts to
`#automation-errors`. Two upgrades:

**5a. Probe the right things.** Today it hits the FL government-detail route (heavy, and one
of the routes that 500s). Replace the os-api probe with **liveness + a cheap DB-backed
readiness probe** so it catches both "process down" *and* the pydantic-class "process up but
every query 500s" failure:

```bash
OSAPI_KEY="00000000-0000-0000-0000-000000000001"
OSAPI_HEALTHZ="http://localhost:8002/healthz"
OSAPI_DATA="http://localhost:8002/bills?jurisdiction=fl&session=2026&per_page=1&apikey=${OSAPI_KEY}"

check_osapi() {
    # 1) liveness — no DB, no redis
    curl -sf --max-time 5 "$OSAPI_HEALTHZ" >/dev/null || return 1
    # 2) readiness — exercises DB + pydantic serialization + redis rate-limiter
    local body
    body=$(curl -sf --max-time 8 "$OSAPI_DATA") || return 1
    echo "$body" | python3 -c 'import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get("results") is not None else 1)' || return 1
    return 0
}
```
> Had this readiness probe existed, the current outage would have paged on 2026-06-19, not
> been found by hand 5 days later.

**Success criteria (explicit, to avoid false positives):** liveness = HTTP 200 from `/healthz`
within 5s; readiness = HTTP 2xx + valid JSON with a non-null `results` from the data query
within 8s. Both `curl -sf` calls already treat non-2xx and timeouts as failure (non-zero exit).
Keep the existing `/var/tmp/ddp-osapi-health.*` debounce so a single blip doesn't page; alert
only after the probe fails on consecutive 5-min runs.

**5b. Fix the latent redis-config bug (F5)** as part of this pass: the rate limiter never
reads `REDIS_URL`. Removing the dead `REDIS_URL` from the old plist (done in WS3's new
plist) and setting `RRL_REDIS_*` in the compose (WS1) makes the redis target explicit and
correct in-container.

**Acceptance:** stop the container → Slack alert within ~5–10 min; restore → recovery
message. Manually point `DATABASE_URL` at a bad host in a throwaway run → readiness probe
fails (liveness still 200), proving the deeper probe works.

---

### WS6 — Alerting delivery (cut Zapier) & metrics (F7)

> **✅ DONE (2026-06-24, `ddp-sync` `6dcb6b4`).** `push_health_alert` now calls Slack
> `chat.postMessage` with `SLACK_BOT_TOKEN` instead of the Zapier webhook (signature unchanged;
> `zapier_webhook_url` kept for the other pipelines that still use it). `start-ddp-sync.sh`
> exports `SLACK_BOT_TOKEN` from the canonical `ddp-agents/.env`. Verified with a mocked post.
> Activates when the `api_health_check` job is re-enabled (still gated on `DDP_API_KEY`) + ddp-sync restarts.

**Decision:** no Sentry. Follow the existing DDP model — scheduled health checks that post
**directly to Slack** — and remove Zapier from the path.

**6a. Direct-to-Slack alerts.** Today ddp-sync's `api_health_check` pipeline posts failures
to a Zapier webhook (`push_health_alert` → `zapier_webhook_url`), and Zapier reformats and
forwards to Slack. The message is *already* fully formatted in Python (`slack_message`), so
Zapier is just a relay we can delete. Repoint `push_health_alert` straight at Slack with the
same `SLACK_BOT_TOKEN` the scrapers already use (change tracked in **ddp-sync**):

`ddp-sync/src/ddp_sync/pipelines/api_health_check.py` (proposed)
```python
import os, requests

SLACK_ALERT_CHANNEL = os.getenv("HEALTH_ALERT_SLACK_CHANNEL", "#automation-errors")

def push_health_alert(_unused_webhook, results) -> bool:
    """Post failed health checks straight to Slack (no Zapier). Never raises."""
    token = os.getenv("SLACK_BOT_TOKEN", "")
    failures = [r for r in results if not r.passed]
    if not failures:
        return True
    if not token:
        logger.warning("SLACK_BOT_TOKEN not set — cannot post health alert")
        return False
    failures_text = "\n".join(f"• *{r.name}*: {r.error}" for r in failures)
    text = (
        f":red_circle: *DDP health check* — {len(failures)}/{len(results)} checks failed\n"
        + failures_text
    )
    try:
        resp = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {token}"},
            json={"channel": SLACK_ALERT_CHANNEL, "text": text},
            timeout=10,
        )
        return resp.ok and resp.json().get("ok", False)
    except Exception as e:  # noqa: BLE001
        logger.error("Slack health alert failed: %s", e)
        return False
```
Supporting changes in ddp-sync: drop `zapier_webhook_url` from `config.py` (or leave it
unused), and make `SLACK_BOT_TOKEN` available to the ddp-sync process (it already lives in
`ddp-agents/.env`; `start-ddp-sync.sh` sources `ddp-sync/.env`, so add the token there or
have the launchd job export it).

**6b. api-v3 coverage stays in the bash heartbeat (WS5).** The `health-check-slack.sh`
monitor already runs every 5 minutes and already posts **directly to Slack** (no Zapier) —
this *is* the heartbeat-to-Slack model. WS5 just upgrades its probe to catch the
"up-but-every-query-500s" failure. So api-v3 itself is covered by the 5-minute heartbeat;
the WS6a change is about cleaning up ddp-sync's *own* health-check delivery for the
DDP-API endpoints it already watches. We avoid double-monitoring api-v3.

**6c. Prometheus (optional this pass):** the metrics exist; consuming them needs a Prometheus
+ Grafana pair. There is **no metrics stack today**. Proposal: add a small
`prometheus` service to the `ddp-agents` compose (it owns shared infra) scraping
`ddp-openstates-api-1:80/metrics`, plus a couple of alert rules (5xx rate, p99 latency).
Sketch:

```yaml
# (future) addition to ddp-agents/docker-compose.yml
  prometheus:
    image: prom/prometheus
    restart: unless-stopped
    volumes: [ "./deployment/prometheus.yml:/etc/prometheus/prometheus.yml:ro" ]
    ports: [ "9090:9090" ]
```
```yaml
# deployment/prometheus.yml
scrape_configs:
  - job_name: openstates-api
    metrics_path: /metrics
    static_configs:
      - targets: ["ddp-openstates-api-1:80"]
```
Recommend **deferring 6c** unless we want dashboards now; WS5 + WS6a cover alerting on outages.

---

### WS7 — Scraper pipeline operational hardening

> **✅ DONE (2026-06-24).** 7a verified (no code change): the running scheduler (`GET /schedule`)
> matches the committed YAML — `openstates_secondary_scrapes` triggers `day_of_week='sun'`
> (next run a Sunday), so the Monday-preemption bug is not present; no stale jobs. 7b implemented
> (`ddp-open-states` `52d8531`): PID-marker worktree lock (macOS has no flock) so
> `apply-local-patches.sh` skips its rebuild while any live scrape reads the tree; concurrent
> secondary scrapes coexist. 7d (no-objects no-op) done earlier (`bc5a3d0`).
>
> **Timezone bug — fixed for OpenStates (ddp-sync `04960db`).** APScheduler `CronTrigger`
> objects built without a tz default to **local EDT**, so `sync_time_utc` fired ~4h late. Set
> the scheduler to UTC + `timezone=UTC` on the 6 openstates triggers; verified all at `+00:00`.
> **Same latent bug remains in the other ddp-sync jobs** (`daily_bill_sync`, `legislator`/`bio`
> syncs are config-driven and UTC-intended; `webflow_*`/`voatz`/`monthly` use hardcoded hours of
> unclear tz intent) — left for a separate decision since they coordinate with external systems.

The scraper scheduling is **already in good shape** (migrated to ddp-sync APScheduler):
independent per-jurisdiction jobs, `max_instances=1`, `coalesce=True`,
`misfire_grace_time=3600`, per-jurisdiction timeouts (FL 16h/WA 8h/USA 4h/others 6h),
`SKIP_PATCHES=1`, `start_new_session=True` to kill grandchildren on timeout, and Slack
alerts from `run-scrape.sh`. Remaining items:

**7a. The Monday-preemption bug (from `RUNBOOK.md` / memory `[[ddp-sync-bug]]`).** On
2026-06-22 the secondary states ran on a Monday and preempted WA mid-scrape. The schedule in
`ddp-sync/config/sync_schedule.yaml` now scopes `secondary` to `sync_day: sunday`, but the
RUNBOOK records it firing off-schedule — **verify the running scheduler matches the committed
YAML** (a stale in-Redis APScheduler job from before the fix can linger):
```bash
curl -s -H "X-API-Key: <key>" http://localhost:8001/ddp-sync/v1/jobs   # confirm next-run dates
```
If a stale `openstates_secondary_scrapes` job shows a weekday next-run, it needs
`replace_existing` to re-register (a scheduler restart does this). **This is a ddp-sync
change, tracked there, not in this repo** — flagged here for completeness.

**7b. Cross-job lock for the shared working tree.** All scrapes share
`openstates-scrapers` on the `local-patches` branch, which `apply-local-patches.sh` rebuilds.
The 01:00 `patch_refresh` job is meant to own that, but a manually-triggered scrape with
`SKIP_PATCHES` unset (e.g. via `run-scrape.sh` directly) could rebuild the branch *while* a
scheduled scrape imports. Low frequency, high blast radius. Proposal: a coarse flock in
`apply-local-patches.sh` and around the scrape body:
```bash
exec 9>/tmp/ddp-openstates-worktree.lock
flock -n 9 || { log "another scrape/patch holds the worktree lock — exiting"; exit 0; }
```

**7c.** Confirm `run-scrape.sh`'s Slack alert still fires under the container world — it
reads `SLACK_BOT_TOKEN` from `ddp-agents/.env` and is independent of api-v3, so unaffected.

**7d. ✅ DONE — incremental "no objects" false-alarm fixed (2026-06-24).** Functional testing
surfaced that an incremental run with nothing changed since the cutoff makes openstates raise
`no objects returned` (non-zero exit) → `run-scrape.sh`'s `ERR` trap fired a false Slack alert
to `#automation-errors` every night for dormant sessions. Fixed: the scrape output is captured
(still streamed via `tee`), and a `no objects returned` in **incremental** mode is treated as a
clean no-op (logs `bills_scraped=0 | no changes since cutoff`, advances the cutoff, skips import,
exits 0 — no alert). Real failures and any full-scrape failure still alert. Verified on `fl 2026E`.

---

### WS8 — Reverse-proxy hardening (ddp-api) & patch conventions

**8a. Proxy (`ddp-api/app/routes/openstates_proxy.py`).** Already solid: 30s timeout,
ConnectError→502, ReadTimeout→504, strips caller `apikey`, injects internal `x-api-key`.

> **✅ DONE (2026-06-25).** Upstream hop confirmed (200 on `http://10.0.0.8:8002`), and a
> **read-scoped managed key (`ddp-ro-…`) was issued** via `POST /admin/keys` and loaded into
> **prod ddp-broker-py** (`DDP_OPENSTATES_BEARER_TOKEN` + `DDP_OPENSTATES_API_ROOT`). Public path
> verified end-to-end. Cutover is gradual/per-jurisdiction via `DDP_OPENSTATES_JURISDICTIONS`
> (see RUNBOOK). Issuance had been 500ing — the EC2 role `DDP-API-EC2-Role` was missing
> `secretsmanager:PutSecretValue`; fixed. (ddp-api logging also moved file → journald.)

Minor hardening to consider (changes tracked in `ddp-api`, not here):
- **Health passthrough:** allow `GET /openstates/healthz` unauthenticated (or a dedicated
  `/openstates/_up`) so external uptime checks can probe without a bearer token.
- **One bounded retry** on `ConnectError` (covers the few-second window during a container
  restart) — but keep it single and short to avoid masking real outages.

**8b. api-v3 change management.** api-v3 currently tracks `origin/main` with no DDP branch.
This plan adds **additive** files only to the api-v3 checkout (`.dockerignore`,
`docker-compose.ddp.yml`); the rewritten `start-os-api.sh`/plist live in `ddp-open-states`,
not in api-v3. With the dedicated Postgres (WS0b), the env-configurable pool patch is **no
longer needed** (WS2), so **api-v3 stays strictly upstream — zero edits to tracked files**.
If a future need arises (many more workers), that patch can go on a `ddp-patches` branch of
api-v3 and be cherry-picked by `apply-local-patches.sh`, mirroring the `openstates-core`
convention (`RUNBOOK.md` §"apply-local-patches.sh cherry-picks").

---

### WS9 — Off-host backups via S3 (wire up the never-configured path)

**Finding (2026-06-24):** the S3 backup for the DDP stack was **scaffolded but never wired**.
`ddp-agents/deployment/scripts/backup-artifacts.sh` exists (syncs `/app/artifacts` →
`s3://ddp-cams-artifacts/`) but: it's **scheduled nowhere** (no launchd/cron), the **`aws` CLI
isn't installed**, there are **no `~/.aws` credentials**, and its default `LOCAL_DIR=/app/artifacts`
is a *container* path. So today there is **no off-host backup of anything** on this Mac.

Establishing this path benefits both the openstates DB dumps (WS0b) and, finally, the intended
CAMS artifact backup.

> **PREREQUISITE / OPEN DEPENDENCY:** an AWS account + IAM credentials with write to a bucket
> (reuse `ddp-cams-artifacts` or a new `ddp-openstates-backups`). **This is the one thing that
> blocks WS9 and needs you** — everything else is local. Until it exists, WS0b's *local* nightly
> dump still runs; it just isn't copied off-host yet.

Steps once creds exist:
1. `brew install awscli`; `aws configure` (or drop a scoped profile in `~/.aws/`). Store creds
   outside the repo; keep them out of compose files and logs.
2. Extend `backup-openstates-db.sh` (WS0b) to push after the local dump, with a bounded retry
   and a Slack alert on failure (the dump + upload must be monitored, not just the API):
   ```bash
   # aws s3 cp already retries transient errors; add a small outer retry + alert-on-failure
   for attempt in 1 2 3; do
     aws s3 cp "$OUT/openstates_${STAMP}.dump" \
       "s3://ddp-openstates-backups/db/openstates_${STAMP}.dump" \
       --storage-class STANDARD_IA && ok=1 && break
     sleep $((attempt * 10))
   done
   if [ "${ok:-0}" != 1 ]; then
     curl -sf --max-time 10 -X POST https://slack.com/api/chat.postMessage \
       -H "Authorization: Bearer $SLACK_BOT_TOKEN" -H "Content-Type: application/json" \
       -d '{"channel":"#automation-errors","text":":red_circle: openstates DB backup -> S3 FAILED"}' >/dev/null || true
   fi
   ```
   Likewise alert if the *local* `pg_dump` exits non-zero (wrap the WS0b dump in the same
   check) — a silent backup failure is the failure mode we most want to catch.

**Backup spec (nail down before building):**
- **Bucket:** `ddp-openstates-backups` (or a prefix under the existing `ddp-cams-artifacts`) —
  your call when creds are provisioned. **Region:** match the existing DDP S3 region.
- **Retention:** S3 lifecycle rule expiring objects after **30 days**; local keep-7.
- **IAM (least privilege):** a scoped policy allowing only `s3:PutObject`/`s3:GetObject`/
  `s3:ListBucket` on `arn:aws:s3:::ddp-openstates-backups/*` — no broad `s3:*`.
- **Schedule:** nightly at **11:00 UTC** — after the daily scrapes finish (USA ~09:00) and
  clear of the FL/USA import windows (FL 02:00, WA 02:30, USA 03:00). Document the time + TZ.
3. **Restore drill (do once, document the real time):** pull a dump from S3 and restore into a
   throwaway container; confirm it round-trips and time it (validates the "~1–2 min" estimate).
4. **Bonus — finish the CAMS artifact backup** the script intended: fix `LOCAL_DIR` to the real
   host artifacts path and schedule `backup-artifacts.sh` via launchd. (Tracked in `ddp-agents`;
   in scope per stakeholder since we're wiring S3 anyway.)

**Encryption:** legislative data is public, so dump encryption isn't required; S3 default
server-side encryption (SSE-S3) is free and fine. No PII handling needed.

**Acceptance:** a nightly dump lands in S3; the documented restore drill succeeds from an S3
object; (bonus) CAMS artifacts appear in the bucket on schedule.

---

## 6. Execution order (once approved)

1. **WS0** — bump the Colima VM to 16 GB / 8 CPU (coordinated; restarts all containers).
   Confirm CAMS + broker healthy afterward.
2. **WS0b** — bring up the dedicated Postgres; dump/restore the openstates data (~1–2 min,
   610 MB); verify counts; install the nightly `pg_dump` backup job.
3. **WS1** — `.dockerignore` + `docker-compose.ddp.yml`; build the image; bring up `api`
   alongside the old process on a throwaway port to validate 200s (e.g. temporarily `8003:80`).
4. **WS4a** — rotate/truncate the 93 MB `scraper.log` (independent; do anytime).
5. **WS3 + WS0b repoint** — change window: stop bare uvicorn, switch container to `8002`,
   point `activate.sh`/`quality_check.py` at `:5433`, swap the launchd plist, verify
   supervised restart.
6. **WS3 sleep/reboot test** — immediately after the supervision chain is in place, run the
   real `pmset sleepnow` + `sudo reboot` verification, so launchd/Colima edge cases surface
   *before* the rest is built on top.
7. **WS5** — enhance the health probe + confirm Slack alert/recovery.
8. **WS4b** — ✅ in-script `scraper.log` rotation in `run-scrape.sh` (50 MB, keep 7; no sudo).
9. **WS6a** — switch ddp-sync health alerts from Zapier to direct Slack.
10. **WS9** — wire up S3 off-host backups + restore drill. **Gated on AWS creds (you)**; the
    local nightly dump from WS0b runs regardless, so this can land whenever creds are ready.
11. **WS7 / WS8** — scheduler verification, worktree lock, proxy tweaks (tracked in their own repos).
12. **WS0b decommission** (later) — verify the 3-consumer `:5433` check passes, then drop the
    stale `openstates` db inside CAMS's Postgres after a soak period.

Steps 1–2 are the coordinated infra changes; only step 5 is user-visible for api-v3. Each
step is independently revertible. **WS9 is the only step with an external blocker (AWS creds).**

---

## 7. Rollback

**Primary rollback is a known-good container, not bare uvicorn.** The interim
`docker-compose.stopgap.yml` build (pydantic 1.10.2 + the psycopg2 SCRAM fix, pointed at the
CAMS DB on :5432) is itself a working, pinned image — so a rollback stays containerized and
**does not reintroduce the pydantic break**. Keep the stopgap image (`ddp-openstates-api:local`)
and compose file in place through the soak.

```bash
# Roll back the full stack to the interim stopgap (still isolated + pinned):
docker-compose -f api-v3/docker-compose.ddp.yml down          # stop dedicated PG + new api
cd api-v3 && docker-compose -f docker-compose.stopgap.yml up -d --force-recreate  # back on :8002 vs CAMS DB
```
> Why not bare uvicorn: reverting `start-os-api.sh` to the host interpreter **reintroduces the
> pydantic break** (host pydantic is 2.x) unless someone also pins `pydantic<2` on the host.
> That's the last-resort path only — the stopgap container is the real fallback.
>
> DB caveat: **keep the old `openstates` db inside CAMS's Postgres until the soak is done**
> (delay the WS0b decommission). While it exists, the stopgap rollback above targets :5432 and
> works with zero data steps. After decommission, point the stopgap at the dedicated `:5433` DB
> instead (it holds the live data), or re-seed.
>
> Mid-cutover failure (e.g. scrapers already repointed to :5433 but the new api-v3 misbehaves):
> the stopgap container is still on :5432, so revert it there AND revert `activate.sh`/
> `quality_check.py` to :5432 together, so the API and the scrapers read/write the same DB. The
> two pointers must always match — never leave the API on one DB and the scrapers on the other.

---

## 8. Validation checklist (definition of done)

- [x] `docker info` → **8 CPU / 16 GiB**; CAMS + broker containers healthy after the VM resize
- [x] Dedicated Postgres up on `:5433`; row counts **match** (bills 41829, votes 11312, people 4098, juris 343)
- [x] Nightly `pg_dump` job produces a `.dump` that round-trips via `pg_restore` (**restore drill passed: 41829 bills**)
- [x] `activate.sh` + `quality_check.py` point at `:5433`; **scraper write to :5433 proven** (sentinel: import restored a corrupted title)
- [x] `pydantic.VERSION` → **`1.10.2`**; `psycopg2 libpq_version()` → **`160000`** (SCRAM-capable)
- [x] Representative endpoints return 200 — **API functional suite 15/15** (incl. the formerly-500 jurisdiction-detail + bill-detail-with-includes; auth 403/401/200; pagination)
- [x] Container restart-on-crash works (throwaway proof + same policy). NOTE: `docker kill` is **excluded by Docker design** (manual action) — not a valid crash test
- [x] Colima restart → all containers (incl. api) returned unattended
- [x] Container logs capped (json-file 10 MB × 5, in compose)
- [x] `RUNBOOK.md` updated (compose start/stop, :5433, rotation, rollback, no-op behavior)
- [x] **Upstream hop verified:** `http://10.0.0.8:8002/{healthz,jurisdictions,bills}` all 200 over WireGuard
- [x] (WS4b) `scraper.log` auto-rotates in-script at 50 MB (copy-then-truncate, keep 7) — tested; no sudo
- [ ] (WS5) Stop container → Slack alert in `#automation-errors`; readiness probe fails on DB-broken run while liveness green
- [ ] (WS9) nightly dump lands in S3; restore drill from an S3 object — **blocked on AWS creds**
- [x] (WS3) reboot recovery — **originally accepted verified-by-construction** (2026-06-24: auto-login
      ON → `RunAtLoad` GUI agents (`com.ddp.colima`, `com.ddp.openstates-api`) fire → Colima +
      `restart:unless-stopped` containers return). **Superseded 2026-07-17:** `com.ddp.openstates-api`
      + `com.ddp.openstates-db-backup` migrated to system LaunchDaemons (see §5 WS3 update), so this
      no longer depends on auto-login at all — confirmed live on disk and running. A literal
      `sudo reboot` end-to-end drill is still not done (it kills the on-box agent + remote session;
      user-driven if ever wanted); the auto-login dependency it was meant to catch is now moot.
- [ ] (WS0b) repo-wide `5432/openstates` consumer check clean before dropping the old DB (after
      soak — **also gated on the FL historical backfill** (2023/2024 regular sessions still
      landing as of 2026-07-21); don't run the consumer check or drop `:5432` until that backfill
      is done, since backfill scrapes still write through the same `activate.sh`/`quality_check.py`
      pointers this check inspects)
- [ ] Load test at modest concurrency → no QueuePool timeouts (optional)
- [x] **End-to-end public path** (bearer) returns 200 — `ddp-ro-…` key issued + loaded into prod ddp-broker-py (2026-06-25)

---

## 9. New / changed artifacts summary

| Path | Type | Repo |
|---|---|---|
| `~/.colima/default/colima.yaml` | edit (8→16 GB, 4→8 CPU) — WS0 | (host) |
| `deploy/Dockerfile.ddp` (+ `deploy/Dockerfile.ddp.dockerignore`) | new — upstream Dockerfile + psycopg2 SCRAM fix | ddp-open-states |
| `deploy/docker-compose.ddp.yml` | new (api **+ dedicated postgres** + `os_pg_data` volume; build context → `../api-v3`) | ddp-open-states |
| `deploy/docker-compose.stopgap.yml` | interim rollback artifact | ddp-open-states |
| `backup-openstates-db.sh` + `com.ddp.openstates-db-backup` plist | new (nightly pg_dump, keep 7, + S3 push) — WS0b/WS9 | ddp-open-states / (host) |
| `aws` CLI install + `~/.aws` creds; S3 bucket + lifecycle | new (WS9) — **blocked on AWS creds** | (host) / AWS |
| `backup-artifacts.sh` (fix `LOCAL_DIR`) + `com.ddp.cams-backup` plist | wire up the never-scheduled CAMS artifact backup (WS9 bonus) | ddp-agents / (host) |
| `activate.sh` | edit `DATABASE_URL` → `localhost:5433` (WS0b) | ddp-open-states |
| `quality_check.py` | edit default DB host → `:5433` (WS0b) | ddp-open-states |
| `start-os-api.sh` | rewrite (uvicorn → compose; brings up postgres + api) | ddp-open-states |
| `~/Library/LaunchAgents/com.ddp.openstates-api.plist` | rewrite (KeepAlive uvicorn → one-shot) | (host) |
| `run-scrape.sh` `rotate_scraper_log()` | in-script log rotation (replaces newsyslog; no sudo) | ddp-open-states |
| `health-check-slack.sh` | enhance os-api probe (readiness) | ddp-agents |
| `api_health_check.py` | Zapier → direct Slack delivery (WS6a) | ddp-sync |
| `run-scrape.sh` | ✅ incremental "no objects" → clean no-op (WS7d) | ddp-open-states |
| `sync_schedule.yaml` verify / worktree flock | WS7 (remaining) | ddp-sync / ddp-open-states |
| `openstates_proxy.py` health passthrough + 1 retry | optional WS8a | ddp-api |
| `RUNBOOK.md` | update ops docs (compose, :5433 DB, VM size) | ddp-open-states |

---

## 10. Risks & mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| **Schema drift:** the container's `openstates` pin (`^6.7.0` via poetry.lock) expects ORM columns that differ from the DB schema created by the separately-installed `openstates-core` (on `local-patches`) | Medium | Validate in WS1c against the migrated DB before cutover; the four-endpoint acceptance test exercises jurisdictions/bills/people models. If drift appears, pin the container's `openstates` to match the installed core version |
| **WS0 Colima resize restarts ALL containers** (CAMS, broker) | Medium | Do it deliberately in the change window; pause the colima watchdog first; verify every container healthy after; one-time |
| **Scrapers keep writing to the old DB** if `activate.sh`/`quality_check.py` aren't repointed to `:5433` | Medium | Repoint both in the same change window (WS0b); the decommission DROP of the old db makes a missed repoint fail loud instead of silently splitting writes |
| **Migration dump/restore mismatch** (extensions/roles) | Low | `--no-owner` on restore; row-count parity check; the data is a rebuildable replica (re-seed via `os-initdb` + re-import is the fallback) |
| Postgres connection exhaustion | Low | Dedicated DB, `WEB_CONCURRENCY=4` → ≤68 of 100 conns, no CAMS competing |
| `external` network ordering (api up before ddp-agents Redis network exists) | Low | `start-os-api.sh` checks for the network and exits loud; container `restart` retries |
| `bmltenabled` base image worker-env knobs differ from tiangolo | Low | Verify with `docker exec ... env | grep -i worker` on first build; `WEB_CONCURRENCY` is honoured by gunicorn directly regardless |
| Build context still large despite `.dockerignore` | Low | Confirm with `docker build` context size line; tune ignore |
| Rollback reintroduces pydantic break | Low | Primary rollback is the known-good **stopgap container** (§7), still pinned/isolated — no pydantic break; bare-uvicorn host-pin is last resort only |
| New dedicated DB has no backups | Low | Nightly `pg_dump` (WS0b) + off-host S3 copy (WS9) — a net improvement over today's zero-backup shared DB; data is also rebuildable via re-seed |
| Local-only backup until S3 is wired (shares the Mac's disk with the DB) | Low→Med while pending | WS9 ships dumps off-host; **gated on AWS creds (you)** — until then, rely on the rebuildable-replica fallback |

---

## 11. Decisions & remaining questions

**Resolved in review (2026-06-24):**
1. ~~Sentry?~~ **No Sentry account.** Use scheduled health checks → direct Slack instead (WS6a).
2. ~~Zapier?~~ **Cut Zapier**; post to Slack with `SLACK_BOT_TOKEN` (WS6a).
3. ~~Worker count / shared DB?~~ **Dedicated Postgres (WS0b) + `WEB_CONCURRENCY=4`**, no pool
   code change. (Was going to be 3 on the shared CAMS DB; the dedicated DB removed that limit.)
4. ~~Change-window timing?~~ **No timing constraint**, but switchover must not disturb other
   shared-container consumers — addressed by WS3d (we never restart shared Postgres/Redis/Colima;
   pre-flight check enumerates current users; avoid mid scrape-import).
5. ~~Does the shared Postgres have backups today?~~ **No** (`archive_mode=off`, no dump job).
   So the dedicated DB is not a regression; a nightly `pg_dump` (WS0b) is a net improvement.
6. ~~DB size / cutover time?~~ **`openstates` is 610 MB** → dump/restore ~1–2 min.

### PM-review triage — round 1 (2026-06-24)
External PM review returned `needs_revision`. Folded in (right-sized): rollback = the
known-good stopgap container (§7); a nightly `pg_dump` for the dedicated DB (WS0b); a stated
maintenance window for the Colima bump (WS0). **Deliberately not done** (disproportionate for
an internal, single-Mac, rebuildable-replica service whose prod traffic still hits live
OpenStates): PagerDuty/secondary paging, WAL/PITR archiving, full Prometheus/Grafana now,
secret-rotation framework, elaborate prod-traffic canary (we validate on a throwaway port and
the stopgap already serves real traffic). Migration validation stays at row-count parity + the
four-endpoint smoke test (`pg_dump -Fc` already carries sequences/indexes/extensions).

### PM-review triage — round 3 + sign-off (2026-06-24)
Round 3 held at `ship_with_caution` and began re-circling earlier points, so we folded the
last proportionate items and **closed the review loop** (the reviewer skews toward
enterprise/HA patterns; it won't issue a clean "ship" for an internal single-Mac service).
Folded in: alert-on-failure + bounded retry for the backup job (WS9); backup spec nailed down
(bucket/region/30-day lifecycle/least-privilege IAM/11:00 UTC schedule); the real sleep/reboot
test moved right after WS3; the `:5433` hidden-consumer check broadened to a repo-wide grep; a
plain RPO/RTO statement (WS0b). **Declined:** a second paging product and quarterly
restore-in-CI (a documented periodic manual drill suffices), and re-architecting for Colima
path-drift on OS upgrades. **Agreed in principle:** off-host backup (WS9) is required before
this is "production-ready" — it is *not* de-scoped, only gated on AWS creds (the one external
blocker). WS0–WS8 can proceed now; WS9 lands when creds arrive.

### PM-review triage — round 2 (2026-06-24)
Round 2 upgraded the recommendation to `ship_with_caution`. Folded in (proportionate): **WS9**
off-host S3 backup + restore drill (discovered the CAMS S3 backup was never actually wired —
no aws CLI, no creds, never scheduled — so this is net-new and a real durability win, not
gold-plating); explicit `:5433` consumer list + pre-decommission check (WS0b); a real
sleep/reboot supervision test (WS3); health-probe success thresholds (WS5); a mid-cutover
rollback note for half-repointed scrapers (§7). **Still declined:** a second paging product
(Slack stays primary; a lightweight dead-man's check is noted as optional, below), resource
exporters/Prometheus now, and dump encryption (data is public). New external dependency from
this round: **AWS creds/bucket for WS9** (the only thing blocking off-host backups).

**Still open (smaller, can decide at build time):**
5. **Prometheus/Grafana (WS6c):** stand up a metrics stack this pass, or defer? (Recommendation:
   defer; WS5 + WS6a cover outage alerting.)
6. **Proxy retry (WS8a):** add the single bounded ConnectError retry, or keep fail-fast?
7. **Where to put `SLACK_BOT_TOKEN` for ddp-sync (WS6a):** add to `ddp-sync/.env`, or export it
   from the launchd job? (Token already exists in `ddp-agents/.env`.)
8. **Dead-man's check (optional):** the lightweight answer to "Slack is the only alert channel" —
   alert if the health probe *stops running at all* (not just on a failed check). Cheap; deferred
   unless you want it. Chosen over a second paging product, which is out of proportion here.

---

## 12. Explicitly out of scope (and why)

- **Containerizing the scrapers.** They depend on the live `openstates-scrapers` working
  tree (`local-patches` branch rebuilt per run), the `people` YAML checkout, the
  multi-GB `_cache`/`_data` dirs, and VA's API key — all naturally a host concern. ddp-sync
  already supervises them well. Revisit only if host-Python drift bites them too.
- **pydantic v2 migration.** Large refactor of `schemas.py` + `pagination.py` for no runtime
  benefit; the pinned container removes the motivation. Track upstream instead.
- **Production cutover** (env-var flip in ddp-broker-py/ddp-sync/votebot). Already specified
  in `PLAN-open-states.md` §8; this plan only makes the thing they'll cut over *to* robust.
```
