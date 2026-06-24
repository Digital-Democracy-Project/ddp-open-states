#!/usr/bin/env bash
# Bring up the containerized api-v3 stack (api + dedicated Postgres) via docker-compose.
# Used by launchd (com.ddp.openstates-api) as a one-shot at boot; the container's
# restart:unless-stopped policy owns the lifecycle thereafter. Idempotent — safe to re-run.
set -euo pipefail

COMPOSE_DIR="/Users/agentsmith/Developer/repos/ddp-open-states/api-v3"
COMPOSE_FILE="docker-compose.ddp.yml"
LOG="/Users/agentsmith/Developer/repos/ddp-open-states/logs/os-api.log"

log() { echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ') [start-os-api] $*" | tee -a "$LOG"; }

# Wait for the Docker daemon (Colima may still be booting after a reboot).
attempts=0
until docker info >/dev/null 2>&1; do
    attempts=$((attempts + 1))
    [ "$attempts" -ge 60 ] && { log "ERROR: Docker not ready after 180s"; exit 1; }
    log "waiting for Docker daemon..."; sleep 3
done

# The shared network is owned by the ddp-agents stack — fail loud if it isn't up (we need it for Redis).
if ! docker network inspect ddp-agents_default >/dev/null 2>&1; then
    log "ERROR: network ddp-agents_default missing — is the ddp-agents stack up?"; exit 1
fi

cd "$COMPOSE_DIR"
log "Bringing up api-v3 stack (docker-compose up -d)"
# Image is built ahead of time on deploy; do not --build here (slow at boot).
docker-compose -f "$COMPOSE_FILE" up -d
log "api-v3 stack up; container restart policy now owns the lifecycle"
