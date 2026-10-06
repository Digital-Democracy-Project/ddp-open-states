#!/usr/bin/env bash
# Usage: run-archive.sh <state>
#
# Standalone bill-document archiver — split out of run-scrape.sh (2026-07-31). Archiving to
# DDP-HOT is slower and less reliable than scrape+import, and used to gate run-scrape.sh's
# .ts/.count marker write on finishing too, which created a compounding failure mode: a run
# whose archive step ran long or died left the incremental cutoff stuck, so the next run had to
# treat more bills as "changed since cutoff," making that run slower too and more likely to also
# miss its own archive window. This script has no relationship to the incremental cutoff at
# all — it just archives whatever's not yet captured, on its own schedule, independent of
# whether/when the last scrape ran. Safe to run concurrently with a scrape for the SAME
# jurisdiction (the natural-key skip check in os-text-extract makes an already-archived version a
# cheap DB check, not a re-fetch) or a DIFFERENT one.
set -e

STATE=$1
LOG_DIR=/Users/agentsmith/Developer/repos/ddp-open-states/logs

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_DIR/scraper.log"; }

# OPEN-159: this checkout's own activate.sh, not the production one by absolute path. Same bug and
# same fix as run-scrape.sh -- these two were the only scripts here still sourcing it absolutely;
# run-all-scrapes.sh, run-people-refresh.sh and the OPEN-37 backfill already did it this way.
# SCRIPT_DIR did not exist in this script at all, hence the definition rather than just a swap.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=activate.sh
source "$SCRIPT_DIR/activate.sh"
# Slack alerts go through lib/slack-alert.sh (OPEN-325). Test -r first: under `set -e`, bash 3.2 exits the
# whole script when `source` hits a missing file even with a `||` fallback, and a missing alert helper
# must not take the job down with it.
[ -r "$SCRIPT_DIR/lib/slack-alert.sh" ] && source "$SCRIPT_DIR/lib/slack-alert.sh" \
    || post_slack_alert() { echo "slack-alert: lib/slack-alert.sh not found; alert not sent: ${1:-}" >&2; return 0; }

# Same Slack/CAMS failure-alerting pattern as run-scrape.sh. The Slack half is now shared
# (lib/slack-alert.sh, OPEN-325): four scripts each carried their own copy of the call, and none
# set the CodeBot sender identity. The CAMS half is still copied between the two scripts.
CAMS_TOKEN=$(grep -E '^CAMS_API_TOKEN=' /Users/agentsmith/Developer/repos/ddp-agents/.env \
    2>/dev/null | head -1 | cut -d'=' -f2- | tr -d '"'"'" | awk '{print $1}')
CAMS_URL="${CAMS_URL:-http://localhost:8000}"

on_failure() {
    log "ERROR: archive failed for $STATE"
    post_slack_alert "⚠️ *OpenStates archive failed: $STATE* — check ~/Developer/repos/ddp-open-states/logs/scraper.log"
    report_failure_to_cams
}

report_failure_to_cams() {
    [ -n "$CAMS_TOKEN" ] || return 0
    local error_type="${FAILURE_ERROR_TYPE:-ArchiveFailure}"
    local message="${FAILURE_MESSAGE:-archive failed for $STATE (see logs/scraper.log)}"
    python3 -c '
import json, sys
print(json.dumps({
    "v": 1,
    "service": "ddp-open-states",
    "error_type": sys.argv[1],
    "message": sys.argv[2],
    "metadata": {"state": sys.argv[3]},
}))
' "$error_type" "$message" "$STATE" 2>/dev/null | \
        curl -sf --max-time 10 -X POST "$CAMS_URL/api/v1/failures" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $CAMS_TOKEN" \
            -d @- >/dev/null || true
}
trap 'on_failure' ERR

# Worktree lock (READER) — same marker convention run-scrape.sh uses, for the same reason:
# os-text-extract is installed editable from openstates-core, so apply-local-patches.sh
# pulling a fresh main while this reads that checkout is the same class of risk as a live
# scrape. Deliberately does NOT run apply-local-patches.sh itself (unlike run-scrape.sh) — this
# script can run independently of, and concurrently with, any scrape's own patch-refresh step;
# doing its own refresh here would just re-introduce that exact race for no benefit, since
# ddp-sync's nightly openstates_patch_refresh job already keeps both forks current.
SCRAPE_MARKER_DIR=/tmp/ddp-openstates-scrapes
mkdir -p "$SCRAPE_MARKER_DIR"
READER_MARKER="$SCRAPE_MARKER_DIR/$$"
touch "$READER_MARKER"
trap 'rm -f "$READER_MARKER"' EXIT

case ",${ARCHIVE_ENABLED_STATES:-}," in
    *",$STATE,"*)
        log "Archiving bill documents: $STATE..."
        # os-text-extract archive takes the DB/metadata abbreviation, not the scraper module
        # name -- `usa` (used everywhere else: run-scrape.sh, ARCHIVE_ENABLED_STATES, ddp-sync's
        # trigger routing) isn't in STATES_BY_ABBR at all; the archiver expects `us`. Found live
        # 2026-07-31 sizing-testing federal archiving: passing `$STATE` straight through raised
        # `KeyError: 'USA'`, which reads like federal jurisdiction isn't supported at all -- it
        # is, `os-text-extract archive us` runs fine. This is the one known exception (every
        # other ARCHIVE_ENABLED_STATES entry is already a 2-letter code matching both
        # conventions); see PRIMITIVES.md's "module name is usa, not us" gotcha.
        ARCHIVE_ABBR="$STATE"
        [ "$STATE" = "usa" ] && ARCHIVE_ABBR="us"
        ARCHIVE_OUT=$(mktemp)
        $OS_TEXT_EXTRACT archive "$ARCHIVE_ABBR" 2>&1 | tee "$ARCHIVE_OUT" >> "$LOG_DIR/scraper.log"
        archive_rc="${PIPESTATUS[0]}"  # tee's own exit code, not os-text-extract's, would mask a real failure
        if [ "$archive_rc" -ne 0 ]; then
            FAILURE_MESSAGE=$(grep -E '^[A-Za-z_][A-Za-z0-9_.]*(Error|Exception): ' "$ARCHIVE_OUT" 2>/dev/null | tail -1)
            FAILURE_ERROR_TYPE=$(echo "$FAILURE_MESSAGE" | grep -oE '^[A-Za-z_][A-Za-z0-9_.]*(Error|Exception)')
            FAILURE_ERROR_TYPE="${FAILURE_ERROR_TYPE:-ArchiveFailure}"
            FAILURE_MESSAGE="${FAILURE_MESSAGE:-bill-document archive failed for $STATE (see logs/scraper.log)}"
            rm -f "$ARCHIVE_OUT"
            trap - ERR  # alert once, can't double-fire
            on_failure
            exit 1
        fi
        rm -f "$ARCHIVE_OUT"
        log "Archiving done: $STATE."
        ;;
    *)
        log "Archiving not enabled for $STATE (see ARCHIVE_ENABLED_STATES in activate.sh) — skipping"
        ;;
esac
