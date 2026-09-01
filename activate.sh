#!/usr/bin/env bash
# Source this to set up the openstates environment

# Load secrets (gitignored)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$SCRIPT_DIR/.env" ] && set -a && source "$SCRIPT_DIR/.env" && set +a
# OPEN-159: everything below that names a checkout is derived from $SCRIPT_DIR -- the directory
# THIS file lives in -- rather than hardcoded to the production checkout. That is not a new
# convention; line 60's OS_VENV already did it, so the venv and its binaries have always followed
# the checkout correctly while the data paths silently did not.
#
# The bug that motivated it: run-scrape.sh used to source this file by absolute path from the
# production checkout, so `./run-scrape.sh az` run in ddp-open-states-dev scraped into
# production's _data/az -- which openstates-core wipes at scrape start -- and imported into the
# production database. The dev checkout provided no isolation at all for the repo's main
# entrypoint. In the production checkout every value below is byte-identical to what it was, so
# this is a no-op there.
#
# PYTHONPATH matters as much as the data dirs: pointing it at the production checkout meant a
# worktree's tests imported the DEPLOYED scrapers rather than the ones under test, which has
# already produced a run of "63 passed" that was measuring the wrong code entirely.

# Dedicated openstates Postgres (host :5433); CAMS keeps :5432. See PLAN-production-hardening.md WS0b.
#
# DATABASE_URL cannot be derived from a path -- the database NAME is what differs between
# production (`openstates`) and dev (`openstates_dev`) -- so it takes an explicit opt-in override
# instead. Keyed on DATABASE_URL_OVERRIDE rather than honouring a pre-set DATABASE_URL, because
# this file is sourced by a script that inherits its parent's whole environment: reading
# DATABASE_URL directly would let any unrelated service's connection string silently become the
# import target. A purpose-named variable cannot be set by accident.
export DATABASE_URL="${DATABASE_URL_OVERRIDE:-postgresql://openstates:openstates_dev@localhost:5433/openstates}"

# The distinction that makes this safe, and the rule to keep if you edit below:
#
#   INPUTS (code, toolchain) may fall back to the production checkout when this one has none.
#   OUTPUTS (scraped data, cache) and the DATABASE never may.
#
# openstates-scrapers/, openstates-core/, people/ and .venv are gitignored nested checkouts, so
# they exist in the production checkout and in ddp-open-states-dev but NOT in a git worktree. An
# input falling back means a worktree can still run; an output falling back means a worktree
# silently writes into production, which is the bug this ticket exists to fix. Borrowing an
# interpreter or a scrapers tree is recoverable. Wiping production's _data/az is not.
_PRODUCTION_CHECKOUT="/Users/agentsmith/Developer/repos/ddp-open-states"

# Inputs: prefer this checkout's, else production's.
if [ -d "$SCRIPT_DIR/openstates-scrapers/scrapers" ]; then
    export PYTHONPATH="$SCRIPT_DIR/openstates-scrapers/scrapers"
else
    export PYTHONPATH="$_PRODUCTION_CHECKOUT/openstates-scrapers/scrapers"
fi
if [ -d "$SCRIPT_DIR/people" ]; then
    export OS_PEOPLE_DIRECTORY="$SCRIPT_DIR/people"
else
    export OS_PEOPLE_DIRECTORY="$_PRODUCTION_CHECKOUT/people"
fi

export SCRAPELIB_RPM=60

# Outputs: strictly this checkout, no fallback. A checkout with no openstates-scrapers/ resolves
# to a path that does not exist, and a run there fails to write rather than writing production's.
# That is the intended outcome.
#
# Note where the escape hatch actually lives: SCRAPED_DATA_DIR_OVERRIDE / CACHE_DIR_OVERRIDE are
# honoured by RUN-SCRAPE.SH (its OPEN-152 restore block), not by this file -- so they work for a
# run-scrape.sh invocation and do nothing if you source this directly. pm-review caught an earlier
# version of this comment implying otherwise.
export SCRAPED_DATA_DIR="$SCRIPT_DIR/openstates-scrapers/_data"
export CACHE_DIR="$SCRIPT_DIR/openstates-scrapers/_cache"

# Sourcing this file directly from a non-production checkout is NOT protected the way
# run-scrape.sh is -- it cannot be, since `exit` in a sourced file would kill the caller's shell.
# So warn instead. The realistic mistake is `cd ddp-open-states-dev && source activate.sh &&
# os-update az --import`, which would import into production. To stdout's sibling, not stdout,
# so nothing parsing a script's output is disturbed.
#
# The fix for the dev checkout is one line in its own gitignored .env, which is sourced above
# before DATABASE_URL is set:  DATABASE_URL_OVERRIDE=postgresql://.../openstates_dev
if [ "$SCRIPT_DIR" != "$_PRODUCTION_CHECKOUT" ] && [ -z "${DATABASE_URL_OVERRIDE:-}" ]; then
    echo "WARNING: $SCRIPT_DIR is not the production checkout, but DATABASE_URL_OVERRIDE is unset" >&2
    echo "         so DATABASE_URL points at the PRODUCTION database. See OPEN-159." >&2
fi
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
# regular successful incremental scrapes, no known scraper gaps like UT's).
#
# MA added 2026-08-10 -- the stale pre-fix snapshot from 2026-06-16 that blocked it (see
# PLAN-coverage-completeness-check.md SS10's starvation-bug fix) is gone: a full re-scrape
# completed 2026-08-09 (bills_scraped=9496, prod scraper.log). US federal and AL added
# 2026-08-10 too, alongside ddp-sync's matching change to run each archive-enabled
# jurisdiction once a week on its own day instead of every jurisdiction daily -- US alone has
# ~83k never-archived documents (two orders of magnitude more than any state), so a daily
# all-jurisdictions run let it dominate shared CPU/network/DDP-HOT I/O and starve the smaller
# jurisdictions' own runs. See ddp-sync's config/sync_schedule.yaml openstates_archive.schedule
# and ARCHIVE_TIMEOUT_S in ddp-sync's openstates_archive.py (us: 24h, sized for its first
# several cold-backfill runs). AL is not in ddp-sync's active scrape rotation (no scheduled
# scrapes, so no new bills land there going forward) -- this just clears its one-time existing
# backlog, not an ongoing pipeline the way MA/US/AZ are.
#
# NC added 2026-08-31 (OPEN-231 Stage 4, PLAN-push-button-onboarding.md §5) -- Phase 1's pilot
# state, probe gate C passed (every media type it scrapes has an extractor entry), DDP-HOT has
# 3.7TB free (2% used). Added here only to permit a manual timed `run-archive.sh nc` dry run --
# NOT yet in ddp-sync's config/sync_schedule.yaml openstates_archive.jurisdictions, so it does
# not run on the recurring weekly schedule until that dry run's evidence (extractor success,
# "no function for" count, S3 mirror sample) is in hand.
export ARCHIVE_ENABLED_STATES="fl,ut,az,wa,va,mi,ma,al,us,nc"
# Dedicated venv for the OpenStates toolchain (isolates its pydantic<2 pin from
# other services' shared installs — see notes/scraper-status-and-pydantic-break).
# Rebuild with: /usr/bin/python3 -m venv .venv && .venv/bin/pip install 'pip<24.1' \
#   && .venv/bin/pip install --no-deps -r requirements-openstates.txt
# OPEN-159: prefer this checkout's own venv, and fall back to the production one when the
# checkout has none. The production checkout and ddp-open-states-dev each have their own; a git
# WORKTREE does not, and creating one per worktree just to run a test would be absurd.
#
# Sharing an interpreter is safe in a way that sharing data is not. The venv is toolchain -- it
# decides which openstates-core is installed, not which database is written or which scrapers are
# imported. PYTHONPATH above is per-checkout, so a worktree borrowing production's interpreter
# still runs ITS OWN scraper code, which is the property that actually matters and the one whose
# absence previously produced a "63 passed" test run against the deployed scrapers.
if [ -d "$SCRIPT_DIR/.venv" ]; then
    export OS_VENV="$SCRIPT_DIR/.venv"
else
    export OS_VENV="$_PRODUCTION_CHECKOUT/.venv"
fi
export PATH="$OS_VENV/bin:$PATH"
export OS_INITDB="$OS_VENV/bin/os-initdb"
export OS_UPDATE="$OS_VENV/bin/os-update"
export OS_PEOPLE="$OS_VENV/bin/os-people"
export OS_TEXT_EXTRACT="$OS_VENV/bin/os-text-extract"
