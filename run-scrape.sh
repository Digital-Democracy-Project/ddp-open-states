#!/usr/bin/env bash
# Usage: run-scrape.sh <state> [session=XXXX]
set -e

STATE=$1
SESSION_ARG=${2:-""}
LOG_DIR=/Users/agentsmith/Developer/repos/ddp-open-states/logs
OS_UPDATE=/Users/agentsmith/Developer/repos/ddp-open-states/.venv/bin/os-update

LAST_RUN_DIR="$LOG_DIR/last-run"
SCRAPE_KEY=$(echo "${STATE}${SESSION_ARG:+ $SESSION_ARG}" | tr ' =' '__')
TS_FILE="$LAST_RUN_DIR/${SCRAPE_KEY}.ts"
COUNT_FILE="$LAST_RUN_DIR/${SCRAPE_KEY}.count"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_DIR/scraper.log"; }

# App-managed log rotation (mirrors the CAMS/broker convention — no newsyslog/logrotate, no sudo).
# scraper.log is written by concurrent run-scrape.sh processes, so we copy-then-truncate IN PLACE
# (same inode) at 50 MB so in-flight tee/>> appenders keep writing safely; keep 7 gzipped archives.
# No lock needed: copy-then-truncate + keep-N is race-tolerant (worst case a duplicate archive).
rotate_scraper_log() {
    local f="$LOG_DIR/scraper.log" max=$((50 * 1024 * 1024))
    [ -f "$f" ] || return 0
    local size; size=$(stat -f%z "$f" 2>/dev/null || echo 0)
    [ "$size" -gt "$max" ] || return 0
    gzip -c "$f" > "$f.$(date -u +%Y%m%dT%H%M%SZ).gz" 2>/dev/null && : > "$f"
    ls -1t "$f".*.gz 2>/dev/null | tail -n +8 | xargs rm -f 2>/dev/null || true
}
rotate_scraper_log

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

# CAMS's CodeBot failure listener (PLAN-failure-to-codebot) — a real, repeated
# scrape bug should reach Agent Smith triage, not just the Slack alert below.
# Found 2026-07-23: the FL 2024 backfill failed 3 days running on the same
# ValueError (fl/bills.py's vote-count check) and nothing ever told CAMS,
# because nothing here called it.
CAMS_TOKEN=$(grep -E '^CAMS_API_TOKEN=' /Users/agentsmith/Developer/repos/ddp-agents/.env \
    2>/dev/null | head -1 | cut -d'=' -f2- | tr -d '"'"'" | awk '{print $1}')
CAMS_URL="${CAMS_URL:-http://localhost:8000}"

on_failure() {
    log "ERROR: scrape/import failed for $STATE"
    [ -n "$SLACK_TOKEN" ] && curl -sf --max-time 10 \
        -X POST https://slack.com/api/chat.postMessage \
        -H "Authorization: Bearer $SLACK_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"channel\": \"#automation-errors\", \"text\": \"⚠️ *OpenStates scrape failed: $STATE* — check ~/Developer/repos/ddp-open-states/logs/scraper.log\"}" \
        >/dev/null || true
    report_failure_to_cams
}

# Best-effort POST to CAMS's `/api/v1/failures` (service="ddp-open-states",
# matching config/codebot_allowlist.yaml's OPEN-project services list) so a
# genuine scrape/import bug can get triaged into a Jira ticket. FAILURE_ERROR_TYPE
# / FAILURE_MESSAGE are set by the caller when a real exception was parsed out of
# the scrape output; otherwise this reports a generic failure (still useful —
# CAMS/Agent Smith decides whether it's code-bug-shaped or not). curl -sf + || true
# throughout: a reporting failure (CAMS down, bad token, network) must never fail
# the scrape script itself or mask the real error above.
report_failure_to_cams() {
    [ -n "$CAMS_TOKEN" ] || return 0
    local error_type="${FAILURE_ERROR_TYPE:-ScrapeOrImportFailure}"
    local message="${FAILURE_MESSAGE:-scrape/import failed for $STATE ${SESSION_ARG} (see logs/scraper.log)}"
    python3 -c '
import json, sys
print(json.dumps({
    "v": 1,
    "service": "ddp-open-states",
    "error_type": sys.argv[1],
    "message": sys.argv[2],
    "metadata": {"state": sys.argv[3], "session": sys.argv[4]},
}))
' "$error_type" "$message" "$STATE" "$SESSION_ARG" 2>/dev/null | \
        curl -sf --max-time 10 -X POST "$CAMS_URL/api/v1/failures" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $CAMS_TOKEN" \
            -d @- >/dev/null || true
}
trap 'on_failure' ERR

# Apply local patches — skipped when SKIP_PATCHES=1 (managed by ddp-sync scheduler)
if [ "${SKIP_PATCHES:-}" != "1" ]; then
    bash /Users/agentsmith/Developer/repos/ddp-open-states/apply-local-patches.sh \
        >> "$LOG_DIR/scraper.log" 2>&1
fi

# Worktree lock (READER) — drop a PID marker so apply-local-patches.sh won't rebuild the scraper
# tree while this scrape reads it. Per-PID file → concurrent secondary-state scrapes coexist
# (each its own marker). Created AFTER the patch step above (so this run's own patch step isn't
# blocked by it) and removed on any exit.
SCRAPE_MARKER_DIR=/tmp/ddp-openstates-scrapes
mkdir -p "$SCRAPE_MARKER_DIR"
READER_MARKER="$SCRAPE_MARKER_DIR/$$"
touch "$READER_MARKER"
trap 'rm -f "$READER_MARKER"' EXIT

MODE="full"
[ -n "$INCREMENTAL_FLAG" ] && MODE="incremental"
log "Starting scrape: $STATE $SESSION_ARG ($MODE${INCREMENTAL_FLAG:+ cutoff=${INCREMENTAL_FLAG#start=}})"

# Pass cache/data dirs explicitly so os-update doesn't fall back to
# os.getcwd()/_cache — which resolves to /_cache (read-only) under launchd.
DIR_FLAGS="--cachedir $CACHE_DIR --datadir $SCRAPED_DATA_DIR"

# Marker file so we can count only files written by this scrape, not leftovers.
SCRAPE_MARKER=$(mktemp)

# First attempt: normal scrape.
# On failure, retry with --fastmode which reads previously fetched pages from
# _cache/ instead of re-hitting the legislature website. The cache persists
# across runs even when _data/{state}/ is wiped, so a mid-run interruption
# still benefits from whatever was fetched before the failure.
SCRAPE_OUT=$(mktemp)
scrape_attempt() {  # $1 = extra flags (e.g. --fastmode). Streams to scraper.log AND captures
                    # to SCRAPE_OUT; returns os-update's real exit code (not tee's).
    $OS_UPDATE "$STATE" --scrape bills $SESSION_ARG $INCREMENTAL_FLAG $1 $DIR_FLAGS 2>&1 \
        | tee "$SCRAPE_OUT" >> "$LOG_DIR/scraper.log"
    return "${PIPESTATUS[0]}"
}

# An incremental run that legitimately finds nothing changed since the cutoff makes
# os-update raise "no objects returned" and exit non-zero. That is a clean no-op, not a
# failure — record it and skip the import instead of firing the failure alert.
finish_no_op() {
    log "=== SCRAPE SUMMARY: $STATE ${SESSION_ARG} | mode=incremental | bills_scraped=0 | no changes since cutoff (no-op) ==="
    log "No new bills for $STATE ${SESSION_ARG} since cutoff; skipping import."
    mkdir -p "$LAST_RUN_DIR"
    date -u +%Y-%m-%dT%H:%M:%S > "$TS_FILE"
    echo "0:incremental" > "$COUNT_FILE"
    rm -f "$SCRAPE_OUT" "$SCRAPE_MARKER"
    exit 0
}

# FASTMODE_ONLY=1 skips the network attempt entirely and scrapes from the local
# cache only — for re-running a session that already has most pages cached from
# a prior run (e.g. one that died partway through on an unrelated bug).
FIRST_ATTEMPT_FLAGS=""
if [ "${FASTMODE_ONLY:-}" = "1" ]; then
    FIRST_ATTEMPT_FLAGS="--fastmode"
    log "FASTMODE_ONLY=1: starting with --fastmode (cache-only, no network)"
fi

rc=0; scrape_attempt "$FIRST_ATTEMPT_FLAGS" || rc=$?
if [ "$rc" -ne 0 ] && [ "$FIRST_ATTEMPT_FLAGS" != "--fastmode" ]; then
    log "Scrape failed, retrying with --fastmode (using local cache)..."
    rc=0; scrape_attempt "--fastmode" || rc=$?
fi
if [ "$rc" -ne 0 ]; then
    # Benign: incremental run with nothing new since the cutoff.
    if [ "$MODE" = "incremental" ] && grep -q "no objects returned from" "$SCRAPE_OUT"; then
        finish_no_op
    fi
    # Genuine failure — pull the actual Python exception line out of the scrape
    # output (before it's removed below) so the CAMS report carries a real
    # error_type/message instead of the generic fallback in report_failure_to_cams.
    FAILURE_MESSAGE=$(grep -E '^[A-Za-z_][A-Za-z0-9_.]*(Error|Exception): ' "$SCRAPE_OUT" 2>/dev/null | tail -1)
    FAILURE_ERROR_TYPE=$(echo "$FAILURE_MESSAGE" | grep -oE '^[A-Za-z_][A-Za-z0-9_.]*(Error|Exception)')
    # Alert once (disable the ERR trap so it can't double-fire) and stop.
    rm -f "$SCRAPE_OUT" "$SCRAPE_MARKER"
    trap - ERR
    on_failure
    exit 1
fi
rm -f "$SCRAPE_OUT"

# Count bill JSON files written during this scrape (excludes leftovers from prior runs).
SCRAPED_BILLS=$(find "$SCRAPED_DATA_DIR/$STATE" -name "bill_*.json" -newer "$SCRAPE_MARKER" 2>/dev/null | wc -l | tr -d ' ')
rm -f "$SCRAPE_MARKER"

# Emit a clearly-visible summary line and warn on suspicious drops.
if [ -f "$COUNT_FILE" ]; then
    PREV_BILLS=$(cut -d: -f1 "$COUNT_FILE")
    PREV_MODE=$(cut -d: -f2 "$COUNT_FILE")
    log "=== SCRAPE SUMMARY: $STATE ${SESSION_ARG} | mode=$MODE | bills_scraped=$SCRAPED_BILLS | prev_run=${PREV_BILLS} (${PREV_MODE}) ==="
    # Warn if two consecutive incremental runs diverge by more than 80%.
    if [ "$MODE" = "incremental" ] && [ "$PREV_MODE" = "incremental" ] && [ "${PREV_BILLS:-0}" -gt 10 ]; then
        THRESHOLD=$(python3 -c "print(max(1, int($PREV_BILLS * 0.2)))")
        if [ "$SCRAPED_BILLS" -lt "$THRESHOLD" ]; then
            log "WARNING: bills_scraped ($SCRAPED_BILLS) is <20% of previous incremental run ($PREV_BILLS) — possible over-filtering for $STATE ${SESSION_ARG}"
        fi
    fi
else
    log "=== SCRAPE SUMMARY: $STATE ${SESSION_ARG} | mode=$MODE | bills_scraped=$SCRAPED_BILLS | prev_run=none (first run) ==="
fi

log "Scrape done: $STATE. Starting import..."

# MI has a pagination overlap that produces duplicate bill JSON files.
# VA has the same issue (confirmed 2026-06-29 via DuplicateItemError on HB 1054).
# --allow_duplicates keeps the first instance and silently skips the rest.
# See: https://github.com/openstates/openstates-scrapers/issues/5697
if [ "$STATE" = "mi" ] || [ "$STATE" = "fl" ] || [ "$STATE" = "va" ]; then
    $OS_UPDATE "$STATE" --import --allow_duplicates $DIR_FLAGS \
        >> "$LOG_DIR/scraper.log" 2>&1
else
    $OS_UPDATE "$STATE" --import $DIR_FLAGS \
        >> "$LOG_DIR/scraper.log" 2>&1
fi

log "Import done: $STATE."
mkdir -p "$LAST_RUN_DIR"
date -u +%Y-%m-%dT%H:%M:%S > "$TS_FILE"
echo "${SCRAPED_BILLS}:${MODE}" > "$COUNT_FILE"
