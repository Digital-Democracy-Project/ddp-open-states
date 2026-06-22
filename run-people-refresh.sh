#!/usr/bin/env bash
# Pull latest people data and import all states into the database.
# Called by ddp-sync's weekly people_refresh job (Sundays after secondary scrapes).
# Can also be run manually.
set -e

SCRIPT_DIR="/Users/agentsmith/Developer/repos/ddp-open-states"
LOG_DIR="$SCRIPT_DIR/logs"

source "$SCRIPT_DIR/activate.sh"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_DIR/scraper.log"; }

log "--- people refresh ---"

cd "$SCRIPT_DIR/people"
git pull --ff-only >> "$LOG_DIR/scraper.log" 2>&1

source "$SCRIPT_DIR/activate.sh"

for state in fl wa us va mi ma ut az al; do
    log "  os-people to-database $state"
    $OS_PEOPLE to-database "$state" >> "$LOG_DIR/scraper.log" 2>&1 \
        || log "ERROR: os-people to-database $state failed (continuing)"
done

log "People refresh done."
