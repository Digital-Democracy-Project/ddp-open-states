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
# Permanent bill-document archive (PLAN-bill-document-provenance.md, Phase 1).
# text_extract.py appends raw/{jurisdiction}/{session}/{bill_id}/ under this root itself.
export ARCHIVE_ROOT_DIR="/Volumes/DDP-HOT"
# Rollout gate, added 2026-07-24: archiving only runs for jurisdictions listed here (comma-
# separated abbrs). Start with just FL — the plan's own rollout criteria call for validating
# one jurisdiction's first full historical backfill before enabling the rest. Widen this list
# once FL has been checked against Phase 1's pass/fail criteria (PLAN-bill-document-provenance.md).
# FL's first full run (2026-07-26) passed cleanly: 7,685 bills, 19,521 documents, 0 unresolved
# errors after the retry-settings + apply-local-patches.sh sync fixes (2026-07-28).
# UT added 2026-07-28 as the smallest tracked jurisdiction (1,021 bills) for a cautious second
# validation -- but its run was a clean no-op (0 fetched/skipped/archived): UT has ZERO
# BillVersionLink/BillDocumentLink rows in the DB. Root cause traced: scrapers/ut/bills.py only
# calls add_version_link()/add_document_link() inside parse_bill_details_from_html(), the
# legacy HTML-scraping path used for pre-2025 sessions. UT switched to an API/JSON-rendered
# bill page starting 2025 (see scrape_bill()'s own comment), which routes through
# scrape_bill_details_from_api() instead -- and that function never calls either. UT has
# captured zero bill text/document links since that rendering switch; this is a real scraper
# gap, not an archive-tool problem. Left enabled here anyway since it's a harmless no-op, not a
# failure -- fixing scrape_bill_details_from_api() to add version/document links is a separate,
# not-yet-scoped task (affects bill-text availability generally, not just archiving).
# AZ added 2026-07-28 as the actual second cautious validation -- confirmed 8,904 version links
# already present, next-smallest tracked jurisdiction with real data (2,190 bills).
export ARCHIVE_ENABLED_STATES="fl,ut,az"
# Dedicated venv for the OpenStates toolchain (isolates its pydantic<2 pin from
# other services' shared installs — see notes/scraper-status-and-pydantic-break).
# Rebuild with: /usr/bin/python3 -m venv .venv && .venv/bin/pip install 'pip<24.1' \
#   && .venv/bin/pip install --no-deps -r requirements-openstates.txt
export OS_VENV="$SCRIPT_DIR/.venv"
export PATH="$OS_VENV/bin:$PATH"
export OS_INITDB="$OS_VENV/bin/os-initdb"
export OS_UPDATE="$OS_VENV/bin/os-update"
export OS_PEOPLE="$OS_VENV/bin/os-people"
export OS_TEXT_EXTRACT="$OS_VENV/bin/os-text-extract"
