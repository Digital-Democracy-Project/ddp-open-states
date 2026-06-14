#!/usr/bin/env bash
set -euo pipefail

API_DIR="/Users/agentsmith/Developer/repos/open-states/api-v3"
UVICORN="/Users/agentsmith/Library/Python/3.9/bin/uvicorn"
LOG_PREFIX="[start-os-api]"

log() { echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ') $LOG_PREFIX $*"; }

# Wait for Postgres (same container as CAMS)
wait_for_postgres() {
    local attempts=0
    while ! docker exec ddp-agents-postgres-1 pg_isready -U openstates >/dev/null 2>&1; do
        attempts=$((attempts + 1))
        [ $attempts -ge 30 ] && { log "ERROR: PostgreSQL not ready after 30s"; exit 1; }
        sleep 1
    done
    log "PostgreSQL is healthy"
}

wait_for_postgres

log "Launching api-v3 on :8002"
cd "$API_DIR"
exec "$UVICORN" api.main:app \
    --host 0.0.0.0 \
    --port 8002
