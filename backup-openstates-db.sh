#!/usr/bin/env bash
# Nightly pg_dump of the dedicated openstates Postgres (WS0b). Keeps 7 local copies.
# Off-host S3 push is WS9 (blocked on AWS creds) — wired below but disabled until creds exist.
set -euo pipefail

OUT="/Users/agentsmith/Developer/repos/ddp-open-states/logs/db-backups"
LOG="/Users/agentsmith/Developer/repos/ddp-open-states/logs/os-api.log"
mkdir -p "$OUT"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
DUMP="$OUT/openstates_${STAMP}.dump"

log() { echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ') [db-backup] $*" | tee -a "$LOG"; }

slack_fail() {
    local token
    token=$(grep -E '^SLACK_BOT_TOKEN=' /Users/agentsmith/Developer/repos/ddp-agents/.env \
        2>/dev/null | head -1 | cut -d'=' -f2- | tr -d '"'"'" | awk '{print $1}')
    [ -n "${token:-}" ] && curl -sf --max-time 10 -X POST https://slack.com/api/chat.postMessage \
        -H "Authorization: Bearer $token" -H "Content-Type: application/json" \
        -d '{"channel":"#automation-errors","text":":red_circle: openstates DB backup FAILED — check logs/os-api.log"}' \
        >/dev/null 2>&1 || true
}

if ! docker exec ddp-openstates-postgres-1 pg_dump -U openstates -Fc openstates > "$DUMP" 2>>"$LOG"; then
    log "ERROR: pg_dump failed"; rm -f "$DUMP"; slack_fail; exit 1
fi
log "dumped $(du -h "$DUMP" | cut -f1) -> $DUMP"

# keep 7 most recent
ls -1t "$OUT"/openstates_*.dump 2>/dev/null | tail -n +8 | xargs -r rm -f

# --- WS9 (off-host) — enable once AWS creds + bucket exist ---
# for attempt in 1 2 3; do
#   aws s3 cp "$DUMP" "s3://ddp-openstates-backups/db/$(basename "$DUMP")" --storage-class STANDARD_IA && ok=1 && break
#   sleep $((attempt * 10))
# done
# [ "${ok:-0}" != 1 ] && { log "ERROR: S3 upload failed"; slack_fail; }
