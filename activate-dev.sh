#!/usr/bin/env bash
# Source this (never activate.sh, which is production's) to set up an ISOLATED openstates
# dev/test environment. Nothing here touches the production checkout at
# ~/Developer/repos/ddp-open-states, its Postgres, its cache, or /Volumes/DDP-HOT.
#
# Why this file exists: found 2026-07-24 that ddp-open-states had no real dev/prod
# separation -- one shared checkout read by every scheduled scrape, so editing code
# risked corrupting a live multi-hour job (see ddp-infra's PLAN-bill-document-provenance.md
# Risk Register). This is a second, fully independent checkout+venv+DB for safe interactive
# testing. It is NOT wired into any launchd plist or ddp-sync schedule -- run everything
# here by hand.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Dev-only database -- same Postgres container as production (ddp-openstates-postgres-1,
# host :5433) but a separate database name, so schema/data are fully isolated without
# needing a second container.
export DATABASE_URL="postgresql://openstates:openstates_dev@localhost:5433/openstates_dev"
export OS_PEOPLE_DIRECTORY="$SCRIPT_DIR/people"
export PYTHONPATH="$SCRIPT_DIR/openstates-scrapers/scrapers"
export SCRAPELIB_RPM=60
export SCRAPED_DATA_DIR="$SCRIPT_DIR/openstates-scrapers/_data"
export CACHE_DIR="$SCRIPT_DIR/openstates-scrapers/_cache"
# Permanent bill-document archive (PLAN-bill-document-provenance.md, Phase 1). Scratch
# location under this dev checkout -- deliberately NOT /Volumes/DDP-HOT, so dev/test runs
# can never mix with or pollute the real archive.
export ARCHIVE_ROOT_DIR="$SCRIPT_DIR/_archive_scratch"
export OS_VENV="$SCRIPT_DIR/.venv"
export PATH="$OS_VENV/bin:$PATH"
export OS_INITDB="$OS_VENV/bin/os-initdb"
export OS_UPDATE="$OS_VENV/bin/os-update"
export OS_PEOPLE="$OS_VENV/bin/os-people"
export OS_TEXT_EXTRACT="$OS_VENV/bin/os-text-extract"

echo "ddp-open-states-dev environment active: DB=openstates_dev, ARCHIVE_ROOT_DIR=$ARCHIVE_ROOT_DIR"
