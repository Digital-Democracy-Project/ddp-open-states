#!/usr/bin/env bash
# Nightly pg_dump of the dedicated openstates Postgres (WS0b). Keeps 7 local copies.
# Off-host S3 push (WS9) via the ddp-prod-s3-openstates-backups proxy wrapper (sudo-gated,
# root-owned credentials under /usr/local/ddp-db-proxy/ — see ddp-infra/Production_S3_Wrappers.md).
# Storage class (STANDARD_IA) is set by the proxy itself; do not pass --storage-class here.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# Slack alerts go through lib/slack-alert.sh (OPEN-325). Test -r first: under `set -e`, bash 3.2 exits the
# whole script when `source` hits a missing file even with a `||` fallback, and a missing alert helper
# must not take the job down with it.
[ -r "$SCRIPT_DIR/lib/slack-alert.sh" ] && source "$SCRIPT_DIR/lib/slack-alert.sh" \
    || post_slack_alert() { echo "slack-alert: lib/slack-alert.sh not found; alert not sent: ${1:-}" >&2; return 0; }

OUT="/Users/agentsmith/Developer/repos/ddp-open-states/logs/db-backups"
LOG="/Users/agentsmith/Developer/repos/ddp-open-states/logs/os-api.log"
mkdir -p "$OUT"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
DUMP="$OUT/openstates_${STAMP}.dump"

log() { echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ') [db-backup] $*" | tee -a "$LOG"; }

slack_fail() {
    post_slack_alert ":red_circle: openstates DB backup FAILED — check logs/os-api.log"
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
