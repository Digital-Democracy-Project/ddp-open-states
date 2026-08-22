#!/usr/bin/env bash
# OPEN-101: repeatable refresh (checkout+pull+rebuild+redeploy) for the api-v3 fork.
#
# Every patch so far (PR #1, PR #2/OPEN-13, OPEN-118) has needed a fully manual pull/rebuild/
# redeploy cycle -- and the first time that manual cycle ran (2026-07-29), it used a bare
# `docker-compose ... up -d --force-recreate` with no service name, which also recreated the
# *shared* dedicated Postgres (`ddp-openstates-postgres-1`, :5433 -- the same DB native
# scrapers write to) and killed two live scrapes (va, ut) mid-write. This script's whole
# reason to exist is closing that exact failure mode: every docker-compose invocation below is
# explicitly scoped to the `api` service, never a bare `up -d`/`--force-recreate`.
#
# Unlike apply-local-patches.sh, this doesn't need the worktree-lock/scrape-running check --
# api-v3's checkout is only ever read at `docker-compose build` time (the Dockerfile's
# `COPY . /app`), not live by a running process the way openstates-core/openstates-scrapers
# are (installed editable into the scrape venv). Scoping every command to `api` means the
# shared Postgres a live scrape might be writing to is never touched, by construction.
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

cd "$COMPOSE_DIR"
log "rebuilding ddp-openstates-api:local image"
docker-compose -f "$COMPOSE_FILE" build api

log "recreating the api container only -- scoped to 'api', see header comment"
docker-compose -f "$COMPOSE_FILE" up -d --force-recreate api

log "api-v3 refresh complete"
