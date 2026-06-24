#!/usr/bin/env bash
# Source this to set up the openstates environment

# Load secrets (gitignored)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$SCRIPT_DIR/.env" ] && set -a && source "$SCRIPT_DIR/.env" && set +a
# Dedicated openstates Postgres (host :5433); CAMS keeps :5432. See PLAN-production-hardening.md WS0b.
export DATABASE_URL="postgresql://openstates:openstates_dev@localhost:5433/openstates"
export OS_PEOPLE_DIRECTORY="$HOME/Developer/repos/ddp-open-states/people"
export PYTHONPATH="/Users/agentsmith/Developer/repos/ddp-open-states/openstates-scrapers/scrapers"
export SCRAPELIB_RPM=60
export SCRAPED_DATA_DIR="$HOME/Developer/repos/ddp-open-states/openstates-scrapers/_data"
export CACHE_DIR="$HOME/Developer/repos/ddp-open-states/openstates-scrapers/_cache"
export OS_INITDB="$HOME/Library/Python/3.9/bin/os-initdb"
export OS_UPDATE="$HOME/Library/Python/3.9/bin/os-update"
export OS_PEOPLE="$HOME/Library/Python/3.9/bin/os-people"
