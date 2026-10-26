#!/usr/bin/env bash
# Nightly scrape runner — called by com.ddp.openstates-scraper launchd job.
# Primary states (FL, WA, US) run daily; secondary states + people refresh run Sunday.
set -e

SCRIPT_DIR="/Users/agentsmith/Developer/repos/ddp-open-states"
LOG_DIR="$SCRIPT_DIR/logs"
DAY=$(date +%u)  # 1=Mon … 7=Sun

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_DIR/scraper.log"; }

log "=== Starting nightly scrape run (day=$DAY) ==="

# Florida — regular + special sessions scraped explicitly (auto-detect only returns active)
for fl_session in "session=2026" "session=2026D" "session=2026E" "session=2026F"; do
    log "--- fl $fl_session ---"
    bash "$SCRIPT_DIR/run-scrape.sh" fl "$fl_session" || log "ERROR: fl $fl_session failed (continuing)"
done

# Washington
log "--- wa ---"
bash "$SCRIPT_DIR/run-scrape.sh" wa || log "ERROR: wa failed (continuing)"

# US Congress: House + Senate are separate scrapes (module name is "usa", not "us")
log "--- usa-lower ---"
bash "$SCRIPT_DIR/run-scrape.sh" usa "session=119 chamber=lower" || log "ERROR: usa-lower failed (continuing)"
log "--- usa-upper ---"
bash "$SCRIPT_DIR/run-scrape.sh" usa "session=119 chamber=upper" || log "ERROR: usa-upper failed (continuing)"

# Secondary states + people refresh — Sundays only
if [ "$DAY" = "7" ]; then
    for state in va mi ut az; do  # va requires VA_API_KEY in .env
        log "--- $state ---"
        bash "$SCRIPT_DIR/run-scrape.sh" "$state" || log "ERROR: $state failed (continuing)"
    done

    # MA needs an explicit session= arg, same as FL above — run-scrape.sh's incremental-cutoff
    # cache key is derived from the session argument it's given (SCRAPE_KEY in run-scrape.sh),
    # and calling it with no session at all produces the key "ma", which has never had a
    # timestamp file and so silently falls back to a full scrape every single time. The real
    # timestamp file (ma_session_194th.ts) sat unused since 2026-07-03 because of this. Fixed
    # 2026-07-28 -- see PLAN-coverage-completeness-check.md SS10 for the full diagnosis (MA
    # hadn't completed a full scrape since 2026-06-16 as a result). Update "194th" when MA's
    # session changes -- scrapers/ma/__init__.py's legislative_sessions list is the source of
    # truth for the current session identifier.
    log "--- ma session=194th ---"
    bash "$SCRIPT_DIR/run-scrape.sh" ma "session=194th" || log "ERROR: ma failed (continuing)"

    log "--- people refresh ---"
    cd /Users/agentsmith/Developer/repos/ddp-open-states/people && git pull --ff-only >> "$LOG_DIR/scraper.log" 2>&1
    source "$SCRIPT_DIR/activate.sh"
    for state in fl wa us va mi ma ut az al; do
        $OS_PEOPLE to-database "$state" >> "$LOG_DIR/scraper.log" 2>&1
    done
    log "People refresh done"
fi

log "=== Nightly scrape run complete ==="
