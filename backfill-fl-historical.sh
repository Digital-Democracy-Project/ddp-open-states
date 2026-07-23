#!/usr/bin/env bash
# One-shot backfill of all FL sessions from 2023 onward (regular + special).
# Runs sequentially, smallest sessions first so quick wins land immediately.
# Each session goes through run-scrape.sh (full mode on first run — no last-run
# marker exists yet), which writes logs/last-run/fl_session_<id>.{ts,count} on
# success. Re-running skips sessions that already produced a marker, so this is
# resumable: if it's interrupted, just launch it again.
#
# WHY sequential + detached: a full FL scrape crawls ~1 bill/min through
# flhouse.gov bot-detection backoffs (30+ hrs for a regular session). Running
# two FL scrapes at once provokes harder throttling, and the nightly runner
# preempts anything still going. Launch this OFF the nightly window.
#
# Usage:
#   nohup ./backfill-fl-historical.sh >> logs/backfill/fl-historical.out 2>&1 &   # all 8
#   ./backfill-fl-historical.sh 2023B 2023C 2025A 2025B 2025C                     # just these
# Sessions with an existing last-run marker are skipped, so a plain re-run only
# picks up whatever hasn't landed yet.
set -u

SCRIPT_DIR="/Users/agentsmith/Developer/repos/ddp-open-states"
LOG_DIR="$SCRIPT_DIR/logs/backfill"
mkdir -p "$LOG_DIR"

# Default: smallest first — five special sessions (handful of bills each,
# minutes), then the three regular sessions (thousands of bills, hours each).
# Override by passing session identifiers as arguments.
if [ "$#" -gt 0 ]; then
    SESSIONS=("$@")
else
    SESSIONS=(2023B 2023C 2025A 2025B 2025C 2024 2025 2023)
fi

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_DIR/fl-historical.out"; }

log "=== FL historical backfill starting: ${SESSIONS[*]} ==="

for s in "${SESSIONS[@]}"; do
    marker="$SCRIPT_DIR/logs/last-run/fl_session_${s}.ts"
    if [ -f "$marker" ]; then
        log "--- fl session=$s: already has marker ($(cat "$marker")), skipping ---"
        continue
    fi
    log "--- fl session=$s: starting full scrape ---"
    if bash "$SCRIPT_DIR/run-scrape.sh" fl "session=$s" >> "$LOG_DIR/fl_${s}.log" 2>&1; then
        log "--- fl session=$s: DONE (count=$(cat "$SCRIPT_DIR/logs/last-run/fl_session_${s}.count" 2>/dev/null)) ---"
    else
        log "!!! fl session=$s: FAILED (see $LOG_DIR/fl_${s}.log) — continuing ==="
    fi
done

log "=== FL historical backfill complete ==="
