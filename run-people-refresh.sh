#!/usr/bin/env bash
# Pull latest people data and import all states into the database.
# Called by ddp-sync's weekly people_refresh job (Sundays after secondary scrapes).
# Can also be run manually.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"

source "$SCRIPT_DIR/activate.sh"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_DIR/scraper.log"; }

log "--- people refresh ---"

cd "$SCRIPT_DIR/people"
git pull --ff-only >> "$LOG_DIR/scraper.log" 2>&1

source "$SCRIPT_DIR/activate.sh"

# OPEN-285: activate.sh's OS_PEOPLE always resolves to $SCRIPT_DIR/.venv, which is built
# directly on the bare EC2 host for host-level execution -- its own python3.9 is a symlink to
# /usr/bin/python3.9, present on the host but not inside ddp-sync's own container. That venv is
# still visible in the container (this whole directory is bind-mounted), just not executable
# there. ddp-sync's container already bundles a separate, working copy of the same toolchain at
# /opt/venv-openstates (OPEN-248, built for os-update inside this exact container) -- os-people
# lives in that same venv. Prefer it when present, without touching activate.sh's own
# resolution (still correct for every other caller running directly on the bare host, where
# /opt/venv-openstates doesn't exist and shouldn't be preferred).
if [ -x /opt/venv-openstates/bin/os-people ]; then
    OS_PEOPLE=/opt/venv-openstates/bin/os-people
fi

# OPEN-285: a per-state failure used to be logged and swallowed (`|| log ... continuing`) with
# no effect on this script's own exit code, so the overall job always reported "completed" in
# Redis flow-status even when every single state failed -- confirmed live, this masked a real
# venv/interpreter mismatch that produced zero actual imports for a full run. Still continuing
# through every state on a per-state failure (one bad state's data shouldn't block the rest),
# but now tracking whether any state failed and reflecting that in the script's own exit code,
# so a real failure actually surfaces as "failed" in flow-status and reaches OPEN-286's alerting
# instead of silently reporting success.
any_failed=0
for state in fl wa us va mi ma ut az al; do
    log "  os-people to-database $state"
    "$OS_PEOPLE" to-database "$state" >> "$LOG_DIR/scraper.log" 2>&1 \
        || { log "ERROR: os-people to-database $state failed (continuing)"; any_failed=1; }
done

if [ "$any_failed" -ne 0 ]; then
    log "People refresh finished with at least one state failure."
    exit 1
fi

log "People refresh done."
