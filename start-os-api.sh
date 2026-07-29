#!/usr/bin/env bash
# Bring up the containerized api-v3 stack (api + dedicated Postgres) via docker-compose.
# Used by launchd (com.ddp.openstates-api) as a one-shot at boot; the container's
# restart:unless-stopped policy owns the lifecycle thereafter. Idempotent — safe to re-run.
set -euo pipefail

COMPOSE_DIR="/Users/agentsmith/Developer/repos/ddp-open-states/deploy"
COMPOSE_FILE="docker-compose.ddp.yml"
LOG="/Users/agentsmith/Developer/repos/ddp-open-states/logs/os-api.log"

log() { echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ') [start-os-api] $*" | tee -a "$LOG"; }

# Reach Docker via Colima's socket directly, independent of the docker "colima"
# context (a colima bounce can drop the context meta.json). Needed as a system
# LaunchDaemon, which has no GUI docker context. Mirrors start-cams.sh.
if [ -z "${DOCKER_HOST:-}" ]; then
    for _sock in "$HOME/.colima/default/docker.sock" "/Users/agentsmith/.colima/default/docker.sock"; do
        [ -S "$_sock" ] && export DOCKER_HOST="unix://$_sock" && break
    done
fi

# Wait for the Docker daemon (Colima may still be booting after a reboot).
attempts=0
until docker info >/dev/null 2>&1; do
    attempts=$((attempts + 1))
    [ "$attempts" -ge 60 ] && { log "ERROR: Docker not ready after 180s"; exit 1; }
    log "waiting for Docker daemon..."; sleep 3
done

# api-v3 depends on CAMS's ddp-agents_default network + ddp-agents-redis-1 (rate
# limiter). As a boot-time system daemon we can start BEFORE CAMS creates them, so
# bounded wait/retry (every 5s up to 300s) instead of fail-fast. On timeout exit
# non-zero: launchd (KeepAlive={SuccessfulExit:false}, ThrottleInterval=30)
# relaunches us until CAMS is up, rather than silently dying on the reboot race.
attempts=0
until docker network inspect ddp-agents_default >/dev/null 2>&1; do
    attempts=$((attempts + 1))
    [ "$attempts" -ge 60 ] && { log "ERROR: network ddp-agents_default absent after 300s — is CAMS up?"; exit 1; }
    log "waiting for ddp-agents_default network (CAMS)... (${attempts}/60)"; sleep 5
done

attempts=0
until docker exec ddp-agents-redis-1 redis-cli ping >/dev/null 2>&1; do
    attempts=$((attempts + 1))
    [ "$attempts" -ge 60 ] && { log "ERROR: ddp-agents-redis-1 unreachable after 300s — is CAMS up?"; exit 1; }
    log "waiting for ddp-agents-redis-1 (CAMS rate limiter)... (${attempts}/60)"; sleep 5
done

cd "$COMPOSE_DIR"
log "Bringing up api-v3 stack (docker-compose up -d)"
# Image is built ahead of time on deploy; do not --build here (slow at boot).
docker-compose -f "$COMPOSE_FILE" up -d
log "api-v3 stack up; container restart policy now owns the lifecycle"

slack_fail() {
    local text="$1" token
    token=$(grep -E '^SLACK_BOT_TOKEN=' /Users/agentsmith/Developer/repos/ddp-agents/.env \
        2>/dev/null | head -1 | cut -d'=' -f2- | tr -d '"'"'" | awk '{print $1}')
    [ -n "${token:-}" ] && curl -sf --max-time 10 -X POST https://slack.com/api/chat.postMessage \
        -H "Authorization: Bearer $token" -H "Content-Type: application/json" \
        -d "{\"channel\":\"#automation-errors\",\"text\":\"$text\"}" \
        >/dev/null 2>&1 || true
}

# Wait for the api-v3 container's own healthcheck (GET /healthz) before touching its DB —
# docker-compose up -d returns as soon as the container starts, not once it's ready.
attempts=0
until [ "$(docker inspect -f '{{.State.Health.Status}}' ddp-openstates-api-1 2>/dev/null)" = "healthy" ]; do
    attempts=$((attempts + 1))
    [ "$attempts" -ge 60 ] && { log "ERROR: ddp-openstates-api-1 not healthy after 300s"; slack_fail ":red_circle: openstates api-v3 container never became healthy at boot — check logs/os-api.log"; exit 1; }
    log "waiting for ddp-openstates-api-1 healthcheck... (${attempts}/60)"; sleep 5
done

# bulk_dataexport (backing LegislativeSession.downloads) is part of openstates.org's own
# "bulk export" Django app, not the OCD/pupa scraping schema openstates-core's os-initdb
# creates — so it's absent from a freshly-initialized DDP database. Its absence 500s
# GET /jurisdictions/{iso2}?include=legislative_sessions for every jurisdiction, since
# JurisdictionPagination.include_map_overrides (api-v3/api/pagination.py) always
# selectinloads legislative_sessions.downloads alongside legislative_sessions. api-v3 is a
# pristine, unpatched upstream checkout (PRIMITIVES.md) with no migration system of its own,
# so create the table here instead of hand-editing that checkout. Uses api-v3's own
# DataExport model as the schema source of truth; create_all(checkfirst=True) is idempotent.
# See OPEN-12 / notes/openstates-jurisdiction-sessions-500-root-cause-20260729.md.
if ! docker exec ddp-openstates-api-1 python -c "
from api.db.models.jurisdiction import DataExport
from api.db import engine
from sqlalchemy import inspect
DataExport.__table__.metadata.create_all(engine, tables=[DataExport.__table__], checkfirst=True)
assert inspect(engine).has_table(DataExport.__tablename__)
" >>"$LOG" 2>&1; then
    log "ERROR: failed to ensure bulk_dataexport table exists"
    slack_fail ":red_circle: openstates api-v3 could not create bulk_dataexport table at boot — GET /jurisdictions/{iso2}?include=legislative_sessions will 500 — check logs/os-api.log"
    exit 1
fi
log "bulk_dataexport table present (created if missing)"

# Regression guard for the exact OPEN-12 failure mode: smoke-test the include that broke
# (500'd for every tracked jurisdiction, not just some) so a future schema drift alerts
# instead of silently breaking ddp-broker-py's session picker again.
APIKEY="00000000-0000-0000-0000-000000000001"
smoke_failed=""
for j in us fl mi az va wa ut; do
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 \
        "http://localhost:8002/jurisdictions/$j?include=legislative_sessions&apikey=$APIKEY" || echo "000")
    if [ "$code" != "200" ]; then
        log "ERROR: /jurisdictions/$j?include=legislative_sessions returned $code (expected 200)"
        smoke_failed="${smoke_failed}${smoke_failed:+, }$j=$code"
    fi
done
if [ -n "$smoke_failed" ]; then
    slack_fail ":red_circle: openstates api-v3 include=legislative_sessions smoke test failed at boot ($smoke_failed) — check logs/os-api.log"
    exit 1
fi
log "include=legislative_sessions smoke test passed for all 7 tracked jurisdictions"
