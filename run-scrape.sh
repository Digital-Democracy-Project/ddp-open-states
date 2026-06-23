#!/usr/bin/env bash
# Usage: run-scrape.sh <state> [session=XXXX]
set -e

STATE=$1
SESSION_ARG=${2:-""}
LOG_DIR=/Users/agentsmith/Developer/repos/ddp-open-states/logs
OS_UPDATE=/Users/agentsmith/Library/Python/3.9/bin/os-update

LAST_RUN_DIR="$LOG_DIR/last-run"
SCRAPE_KEY=$(echo "${STATE}${SESSION_ARG:+ $SESSION_ARG}" | tr ' =' '__')
TS_FILE="$LAST_RUN_DIR/${SCRAPE_KEY}.ts"

INCREMENTAL_FLAG=""
if [ -f "$TS_FILE" ]; then
    LAST_RUN=$(cat "$TS_FILE")
    START_ARG=$(python3 -c "
import datetime, sys
try:
    dt = datetime.datetime.strptime('$LAST_RUN', '%Y-%m-%dT%H:%M:%S')
    print((dt - datetime.timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%S'))
except Exception:
    sys.exit(0)
" 2>/dev/null)
    if [ -n "$START_ARG" ]; then
        INCREMENTAL_FLAG="start=$START_ARG"
    fi
fi

source /Users/agentsmith/Developer/repos/ddp-open-states/activate.sh

# Slack alert on any scrape/import failure
SLACK_TOKEN=$(grep -E '^SLACK_BOT_TOKEN=' /Users/agentsmith/Developer/repos/ddp-agents/.env \
    2>/dev/null | head -1 | cut -d'=' -f2- | tr -d '"'"'" | awk '{print $1}')

on_failure() {
    echo "[$(date)] ERROR: scrape/import failed for $STATE" | tee -a "$LOG_DIR/scraper.log"
    [ -n "$SLACK_TOKEN" ] && curl -sf --max-time 10 \
        -X POST https://slack.com/api/chat.postMessage \
        -H "Authorization: Bearer $SLACK_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"channel\": \"#automation-errors\", \"text\": \"⚠️ *OpenStates scrape failed: $STATE* — check ~/Developer/repos/ddp-open-states/logs/scraper.log\"}" \
        >/dev/null || true
}
trap 'on_failure' ERR

# Apply local patches — skipped when SKIP_PATCHES=1 (managed by ddp-sync scheduler)
if [ "${SKIP_PATCHES:-}" != "1" ]; then
    bash /Users/agentsmith/Developer/repos/ddp-open-states/apply-local-patches.sh \
        >> "$LOG_DIR/scraper.log" 2>&1
fi

echo "[$(date)] Starting scrape: $STATE $SESSION_ARG" | tee -a "$LOG_DIR/scraper.log"

# Pass cache/data dirs explicitly so os-update doesn't fall back to
# os.getcwd()/_cache — which resolves to /_cache (read-only) under launchd.
DIR_FLAGS="--cachedir $CACHE_DIR --datadir $SCRAPED_DATA_DIR"

# First attempt: normal scrape.
# On failure, retry with --fastmode which reads previously fetched pages from
# _cache/ instead of re-hitting the legislature website. The cache persists
# across runs even when _data/{state}/ is wiped, so a mid-run interruption
# still benefits from whatever was fetched before the failure.
[ -n "$INCREMENTAL_FLAG" ] && log "Incremental run: $INCREMENTAL_FLAG"

$OS_UPDATE "$STATE" --scrape bills $SESSION_ARG $INCREMENTAL_FLAG $DIR_FLAGS \
    >> "$LOG_DIR/scraper.log" 2>&1 || {
    echo "[$(date)] Scrape failed, retrying with --fastmode (using local cache)..." \
        | tee -a "$LOG_DIR/scraper.log"
    $OS_UPDATE "$STATE" --scrape bills $SESSION_ARG $INCREMENTAL_FLAG --fastmode $DIR_FLAGS \
        >> "$LOG_DIR/scraper.log" 2>&1
}

echo "[$(date)] Scrape done: $STATE. Starting import..." | tee -a "$LOG_DIR/scraper.log"

# MI has a pagination overlap that produces duplicate bill JSON files.
# --allow_duplicates keeps the first instance and silently skips the rest.
# See: https://github.com/openstates/openstates-scrapers/issues/5697
if [ "$STATE" = "mi" ] || [ "$STATE" = "fl" ]; then
    $OS_UPDATE "$STATE" --import --allow_duplicates $DIR_FLAGS \
        >> "$LOG_DIR/scraper.log" 2>&1
else
    $OS_UPDATE "$STATE" --import $DIR_FLAGS \
        >> "$LOG_DIR/scraper.log" 2>&1
fi

echo "[$(date)] Import done: $STATE." | tee -a "$LOG_DIR/scraper.log"
mkdir -p "$LAST_RUN_DIR"
date -u +%Y-%m-%dT%H:%M:%S > "$TS_FILE"
