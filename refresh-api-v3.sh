#!/usr/bin/env bash
# OPEN-101: repeatable refresh (checkout+pull+rebuild+redeploy) for the api-v3 fork.
#
# Every patch so far (PR #1, PR #2/OPEN-13, OPEN-118) has needed a fully manual pull/rebuild/
# redeploy cycle -- and the first time that manual cycle ran (2026-07-29), it used a bare
# `docker-compose ... up -d --force-recreate` with no service name, which also recreated the
# *shared* dedicated Postgres (`ddp-openstates-postgres-1`, :5433 -- the same DB native
# scrapers write to) and killed two live scrapes (va, ut) mid-write. This script's whole
# reason to exist is closing that exact failure mode: every docker-compose invocation below is
# explicitly scoped to the `api` service (never a bare `up -d`/`--force-recreate`), passes
# `--no-deps` so compose won't even consider `api`'s `depends_on: postgres` (belt-and-
# suspenders on top of the explicit scoping -- pm-review's own question was "could
# --force-recreate on a named service ever still cascade to its dependencies?", and this
# removes that ambiguity structurally rather than relying on observed behavior), and verifies
# postgres's container start-time is unchanged after the fact rather than trusting either of
# those on faith.
#
# Unlike apply-local-patches.sh, this doesn't need the worktree-lock/scrape-running check --
# api-v3's checkout is only ever read at `docker-compose build` time (the Dockerfile's
# `COPY . /app`), not live by a running process the way openstates-core/openstates-scrapers
# are (installed editable into the scrape venv).
#
# Run manually after merging a PR to Digital-Democracy-Project/api-v3's main -- no cron/
# scheduling wired up yet (deploys are still infrequent enough that this is fine; revisit if
# that changes, same call PLAN-fork-management.md §5.F made for drift visibility).
set -euo pipefail

API_V3_DIR="/Users/agentsmith/Developer/repos/ddp-open-states/api-v3"
COMPOSE_DIR="/Users/agentsmith/Developer/repos/ddp-open-states/deploy"
COMPOSE_FILE="docker-compose.ddp.yml"
LOG="/Users/agentsmith/Developer/repos/ddp-open-states/logs/os-api.log"

log() { echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ') [refresh-api-v3] $*" | tee -a "$LOG"; }

cd "$API_V3_DIR"
before="$(git rev-parse --short HEAD)"
git checkout main
git pull origin main
after="$(git rev-parse --short HEAD)"
log "api-v3: $before -> $after"

if [ "$before" = "$after" ]; then
    log "no new commits -- rebuilding/redeploying anyway (idempotent, matches OPEN-101's own manual-cycle precedent of always rebuilding after a pull)"
fi

POSTGRES_CONTAINER="ddp-openstates-postgres-1"
API_CONTAINER="ddp-openstates-api-1"

# The core safety property this script exists for -- verified on every run, not just once by
# hand. `api` depends_on postgres (service_healthy) in docker-compose.ddp.yml, so recreating
# `api` alone could in principle still touch postgres if compose ever decided a dependency
# needed restarting too. `--no-deps` removes that ambiguity structurally (compose won't even
# consider postgres); this start-time check catches it anyway if compose's behavior ever
# changes underneath this script.
postgres_started_before="$(docker inspect --format '{{.State.StartedAt}}' "$POSTGRES_CONTAINER")"

cd "$COMPOSE_DIR"
log "rebuilding ddp-openstates-api:local image"
docker-compose -f "$COMPOSE_FILE" build api

log "recreating the api container only -- scoped to 'api', --no-deps, see header comment"
docker-compose -f "$COMPOSE_FILE" up -d --force-recreate --no-deps api

postgres_started_after="$(docker inspect --format '{{.State.StartedAt}}' "$POSTGRES_CONTAINER")"
if [ "$postgres_started_before" != "$postgres_started_after" ]; then
    log "FATAL: $POSTGRES_CONTAINER's start time changed ($postgres_started_before -> $postgres_started_after) -- it was recreated/restarted, which this script must never do. Investigate immediately -- this is the exact 2026-07-29 failure mode."
    exit 1
fi
log "$POSTGRES_CONTAINER confirmed untouched (start time unchanged)"

# Bounded wait for the api container's own healthcheck rather than trusting `up -d`'s exit
# code alone -- a container can start successfully and still fail its healthcheck a few
# seconds later (e.g. a bad migration, a crashed worker).
log "waiting for $API_CONTAINER to report healthy..."
attempts=0
until [ "$(docker inspect --format '{{.State.Health.Status}}' "$API_CONTAINER" 2>/dev/null)" = "healthy" ]; do
    attempts=$((attempts + 1))
    if [ "$attempts" -ge 20 ]; then
        log "FATAL: $API_CONTAINER did not report healthy within 60s of being recreated -- check 'docker logs $API_CONTAINER'"
        exit 1
    fi
    sleep 3
done

log "api-v3 refresh complete -- $API_CONTAINER healthy, $POSTGRES_CONTAINER untouched"
