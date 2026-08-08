#!/usr/bin/env bash
# check-scrape-staleness.sh — scraper staleness watchdog (OPEN-40, PLAN-open-states §11.3)
#
# Detects jurisdictions that silently stop scraping. Every other failure path in
# this repo (run-scrape.sh's ERR trap / on_failure) fires only from INSIDE a run;
# nothing noticed "this job should have produced a fresh logs/last-run/<key>.ts
# by now and didn't" — which is exactly how MA ran wrong for six weeks in silence.
#
# Invoked every 5 minutes by the existing com.ddp.health-monitor LaunchDaemon via a
# one-line `bash <this script> || true` hook in ddp-agents/deployment/scripts/
# health-check-slack.sh — deliberately OUTSIDE ddp-sync and the scrape scripts, so
# the watchdog survives every failure mode it exists to catch, including "the
# scheduler daemon itself is dead" (observed live: ddp-sync down 2026-07-04→08,
# nothing alerted). Runs as root under that daemon; sentinel files it writes into
# logs/last-run/ will be root-owned (the directory is agentsmith-owned, so manual
# cleanup still works).
#
# Self-contained on purpose: sources nothing from this repo, so it cannot be broken
# by the things it monitors. The Slack/CAMS block below is a copy of run-scrape.sh's
# on_failure()/report_failure_to_cams() pattern — the fifth copy in this repo.
# OPEN-43 tracks extracting a shared helper; this script may stay a deliberate copy
# even then (monitoring shouldn't share code with the monitored).
#
# Alert lifecycle per key (sentinel de-dupe, once per staleness episode):
#   stale + no sentinel  -> alert Slack #automation-errors + CAMS, write <key>.stale-alerted
#   stale + sentinel     -> silent (already alerted this episode)
#   fresh + sentinel     -> remove sentinel, post recovery message
#   missing .ts entirely -> maximally stale (alerts, never skips)
#
# STALE_* env vars below are test seams (see test-check-scrape-staleness.sh) —
# production (the health-monitor hook) sets none of them.

set -uo pipefail

REPO_DIR=/Users/agentsmith/Developer/repos/ddp-open-states
LOG_DIR="$REPO_DIR/logs"
LAST_RUN_DIR="${STALE_LAST_RUN_DIR:-$LOG_DIR/last-run}"
LOG_FILE="${STALE_LOG_FILE:-$LOG_DIR/staleness-check.log}"
DRY_RUN="${STALE_DRY_RUN:-0}"
NOW_EPOCH="${STALE_NOW_EPOCH:-$(date +%s)}"
MISSING_AGE_HOURS=999999   # "maximally stale" — a missing marker always exceeds any threshold

# Own log file, not scraper.log: this runs every 5 minutes under the monitor and
# quiet runs log nothing, but scraper.log's rotation/summary greps shouldn't have
# to filter watchdog chatter. Same log() shape as run-scrape.sh (local-time variant).
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

# --- Watched key -> threshold map (hardcoded allowlist, AC #2) -------------------
#
# key:threshold_hours, one entry per line. The key is run-scrape.sh's SCRAPE_KEY —
# the exact basename of the logs/last-run/<key>.ts marker. Hardcoded on purpose
# (the §11.3 design's own decision): logs/last-run/ also holds one-time backfill
# markers (fl_session_2023..2025C, usa_session_118_*) that will correctly never
# update and must never be watched, so globbing the directory is wrong.
#
# Verified against ddp-sync config/sync_schedule.yaml + production logs/last-run/
# on 2026-08-08 (OPEN-40 architecture assessment — supersedes the original §11.3
# table). This map is THE thing to touch when the ddp-sync schedule changes:
#   - 48h  = daily jobs   (2x their cadence)
#   - 228h = weekly jobs  (~9.5 days: Sunday jobs get until Tuesday-ish before alarm)
#   - fl_session_2026*: weekly ONLY while sync_schedule.yaml has primary.fl.sync_day:
#     sunday (out-of-session since 2026-07-16). Move back to 48h when FL reverts to
#     daily for the 2027 session.
#   - ma is the BARE key, not ma_session_194th: ddp-sync passes session_arg=None for
#     all secondaries (OPEN-24 — VA/UT each had two simultaneously-active sessions),
#     so run-scrape.sh derives SCRAPE_KEY=ma and writes ma.ts. Watching
#     ma_session_194th would be a permanent false alert.
WATCHLIST="${STALE_WATCHLIST:-
wa:48
usa_session_119_chamber_lower:48
usa_session_119_chamber_upper:48
fl_session_2026:228
fl_session_2026D:228
fl_session_2026E:228
fl_session_2026F:228
va:228
mi:228
ut:228
az:228
ma:228
}"

# --- Alerting (copy of run-scrape.sh's pattern — see OPEN-43 header note) --------

SLACK_TOKEN=""
CAMS_TOKEN=""
CAMS_URL="${CAMS_URL:-http://localhost:8000}"
if [ "$DRY_RUN" != "1" ]; then
    SLACK_TOKEN=$(grep -E '^SLACK_BOT_TOKEN=' /Users/agentsmith/Developer/repos/ddp-agents/.env \
        2>/dev/null | head -1 | cut -d'=' -f2- | tr -d '"'"'" | awk '{print $1}')
    CAMS_TOKEN=$(grep -E '^CAMS_API_TOKEN=' /Users/agentsmith/Developer/repos/ddp-agents/.env \
        2>/dev/null | head -1 | cut -d'=' -f2- | tr -d '"'"'" | awk '{print $1}')
fi

post_slack() {
    # $1 = message text. Keys/ages are hardcoded/derived alphanumerics, so inline
    # JSON is injection-safe here (same reasoning as run-scrape.sh's on_failure).
    if [ "$DRY_RUN" = "1" ]; then
        echo "DRY_RUN slack: $1"
        return 0
    fi
    [ -n "$SLACK_TOKEN" ] && curl -sf --max-time 10 \
        -X POST https://slack.com/api/chat.postMessage \
        -H "Authorization: Bearer $SLACK_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"channel\": \"#automation-errors\", \"text\": \"$1\"}" \
        >/dev/null || true
}

post_cams() {
    # $1 = message, $2 = key, $3 = age display, $4 = threshold hours.
    # Best-effort POST to CAMS /api/v1/failures so a real staleness episode reaches
    # Agent Smith triage, not just Slack. curl -sf + || true throughout: an alerting
    # outage must never break the health monitor this script runs under.
    if [ "$DRY_RUN" = "1" ]; then
        echo "DRY_RUN cams: ScrapeStalenessDetected key=$2 age=$3 threshold=${4}h"
        return 0
    fi
    [ -n "$CAMS_TOKEN" ] || return 0
    python3 -c '
import json, sys
print(json.dumps({
    "v": 1,
    "service": "ddp-open-states",
    "error_type": "ScrapeStalenessDetected",
    "message": sys.argv[1],
    "metadata": {"key": sys.argv[2], "age": sys.argv[3], "threshold_hours": sys.argv[4]},
}))
' "$1" "$2" "$3" "$4" 2>/dev/null | \
        curl -sf --max-time 10 -X POST "$CAMS_URL/api/v1/failures" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $CAMS_TOKEN" \
            -d @- >/dev/null || true
}

# --- Main check ------------------------------------------------------------------

for entry in $WATCHLIST; do
    key="${entry%%:*}"
    threshold_hours="${entry##*:}"
    ts_file="$LAST_RUN_DIR/$key.ts"
    sentinel="$LAST_RUN_DIR/$key.stale-alerted"

    if [ -f "$ts_file" ]; then
        mtime=$(stat -f %m "$ts_file" 2>/dev/null || echo 0)   # BSD stat (this Mac), not GNU
        age_hours=$(( (NOW_EPOCH - mtime) / 3600 ))
        age_display="${age_hours}h"
    else
        # Missing marker = the job has NEVER succeeded (or someone removed the
        # marker) — maximally stale. Alerts, never skips (AC #3).
        age_hours=$MISSING_AGE_HOURS
        age_display="never (no ${key}.ts marker)"
    fi

    if [ "$age_hours" -gt "$threshold_hours" ]; then
        if [ ! -f "$sentinel" ]; then
            log "STALE: $key last-run age ${age_display} exceeds ${threshold_hours}h threshold — alerting"
            msg="🕰️ *OpenStates scrape stale: ${key}* — last successful run: ${age_display} (threshold ${threshold_hours}h). The job that should refresh logs/last-run/${key}.ts is not completing. See ~/Developer/repos/ddp-open-states/RUNBOOK.md (staleness watchdog) and logs/scraper.log."
            post_slack "$msg"
            post_cams "scrape staleness: $key last run ${age_display}, threshold ${threshold_hours}h" \
                "$key" "$age_display" "$threshold_hours"
            # Sentinel = "already alerted this episode". If the write fails we'd
            # re-alert every 5 minutes, so log that loudly instead of hiding it.
            date -u +%Y-%m-%dT%H:%M:%S > "$sentinel" \
                || log "ERROR: could not write sentinel $sentinel — $key will re-alert every run"
        fi
    else
        if [ -f "$sentinel" ]; then
            log "RECOVERED: $key fresh again (age ${age_display}, threshold ${threshold_hours}h) — clearing sentinel"
            rm -f "$sentinel" \
                || log "ERROR: could not remove sentinel $sentinel — recovery will re-post every run"
            post_slack "✅ *OpenStates scrape recovered: ${key}* — fresh last-run marker (age ${age_display}, threshold ${threshold_hours}h)."
        fi
    fi
done

exit 0
