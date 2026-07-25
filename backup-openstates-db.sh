#!/usr/bin/env bash
# Nightly pg_dump of the dedicated openstates Postgres (WS0b). Keeps 7 local copies.
# Off-host S3 push (WS9) via the ddp-prod-s3-openstates-backups proxy wrapper (sudo-gated,
# root-owned credentials under /usr/local/ddp-db-proxy/ — see ddp-infra/Production_S3_Wrappers.md).
# Storage class (STANDARD_IA) is set by the proxy itself; do not pass --storage-class here.
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

# --- WS9 (off-host): push via the locked-down S3 proxy wrapper ---
ok=0
for attempt in 1 2 3; do
    if /Users/agentsmith/bin/ddp-prod-s3-openstates-backups put "$DUMP" "db/$(basename "$DUMP")"; then
        ok=1; break
    fi
    sleep $((attempt * 10))
done
if [ "$ok" != 1 ]; then
    log "ERROR: S3 upload failed"; slack_fail
else
    log "uploaded -> s3://ddp-openstates-backups/db/$(basename "$DUMP")"
fi
