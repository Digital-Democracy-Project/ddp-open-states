#!/usr/bin/env bash
# Nightly scrape runner — called by com.ddp.openstates-scraper launchd job.
# Primary states (FL, WA, US) run daily; secondary states + people refresh run Sunday.
set -e

SCRIPT_DIR="/Users/agentsmith/Developer/repos/ddp-open-states"
LOG_DIR="$SCRIPT_DIR/logs"
DAY=$(date +%u)  # 1=Mon … 7=Sun

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_DIR/scraper.log"; }

log "=== Starting nightly scrape run (day=$DAY) ==="

# Primary states — run every day
for state in fl wa; do
    log "--- $state ---"
    bash "$SCRIPT_DIR/run-scrape.sh" "$state" || log "ERROR: $state failed (continuing)"
done

# US Congress: House + Senate are separate scrapes (module name is "usa", not "us")
log "--- usa-lower ---"
bash "$SCRIPT_DIR/run-scrape.sh" usa "session=119 chamber=lower" || log "ERROR: usa-lower failed (continuing)"
log "--- usa-upper ---"
bash "$SCRIPT_DIR/run-scrape.sh" usa "session=119 chamber=upper" || log "ERROR: usa-upper failed (continuing)"

# Secondary states + people refresh — Sundays only
if [ "$DAY" = "7" ]; then
    for state in va mi ma ut az; do  # va requires VA_API_KEY in .env
        log "--- $state ---"
        bash "$SCRIPT_DIR/run-scrape.sh" "$state" || log "ERROR: $state failed (continuing)"
    done

    log "--- people refresh ---"
    cd /Users/agentsmith/Developer/repos/ddp-open-states/people && git pull --ff-only >> "$LOG_DIR/scraper.log" 2>&1
    source "$SCRIPT_DIR/activate.sh"
    for state in fl wa us va mi ma ut az al; do
        $OS_PEOPLE to-database "$state" >> "$LOG_DIR/scraper.log" 2>&1
    done
    log "People refresh done"
fi

log "=== Nightly scrape run complete ==="
