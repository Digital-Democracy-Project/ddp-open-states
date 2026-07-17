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
