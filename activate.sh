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
# BillVersionLink/BillDocumentLink rows in the DB. **Correction, same day:** the root cause
# first written here (scrape_bill_details_from_api() supposedly never calling
# add_version_link()/add_document_link() since a 2025 site redesign) was wrong -- that code has
# called both correctly for a long time, confirmed by running it live against a real bill. The
# actual bug: an incremental-scraping optimization added 2026-06-30 skips re-processing a bill
# once it decides nothing's changed, but used to still hand the (now-empty) bill to the importer
# anyway -- which deletes a bill's existing versions/documents/actions/sponsorships when a new
# scrape reports zero of them. Every incremental UT run since 2026-06-30 silently wiped each
# unchanged bill's already-good data this way, which is why the DB shows zero across the board.
# Fixed in scrapers/ut/bills.py (PR openstates-scrapers#10, 2026-07-28) -- the skip case no
# longer yields the bill at all, so existing data is left alone. Left enabled here since a
# fresh UT run (after the fix + a rescrape) is expected to produce real archived documents.
# AZ added 2026-07-28 as the actual second cautious validation -- confirmed 8,904 version links
# already present, next-smallest tracked jurisdiction with real data (2,190 bills). AZ's run
# also completed clean: 2,190 bills checked, 3,584 documents archived, 0 errors.
# WA/VA/MI added 2026-07-28 -- all three confirmed healthy (real version-link data present,
# regular successful incremental scrapes, no known scraper gaps like UT's). MA intentionally
# NOT added yet -- its local data is still the stale pre-fix snapshot from 2026-06-16 (see
# PLAN-coverage-completeness-check.md SS10's starvation-bug fix) until it gets a fresh full
# re-scrape; archiving now would just archive outdated documents. US federal intentionally NOT
# added yet either -- ~37,206 bills is a different scale problem (likely a multi-day run against
# govinfo.gov, not just a bigger version of what's already been validated) and deserves its own
# sizing pass before enabling, not a default inclusion alongside the states.
export ARCHIVE_ENABLED_STATES="fl,ut,az,wa,va,mi"
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
