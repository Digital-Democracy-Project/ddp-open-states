#!/usr/bin/env bash
# Targeted FL rescrape for the 16 real bills confirmed (via `quality_check.py --bill-ids fl 2026
# ...` against production, 2026-08-15) to still be missing votes after OPEN-66's fix
# (openstates-scrapers PR #27, asymmetric WAF-retry coverage across FL's 3-hop House-vote
# fetch chain). Uses the new bill_no= single-bill filter added to scrapers/fl/bills.py
# (FlBillScraper.scrape) instead of a full ~1,900-bill session rescrape.
#
# Two-phase by design, matching the established prod-backfill workflow (dry-run, discuss real
# numbers, then commit): this script only SCRAPES (writes JSON to $CACHE_DIR/$SCRAPED_DATA_DIR,
# touches no database). Importing into the real production DB is a separate, explicit step run
# by hand after reviewing this script's output -- see the trailing comment for the exact command.
set -uo pipefail
cd "$(dirname "$0")/../.."

source activate-dev.sh

# Preflight: this dev checkout's nested openstates-scrapers has drifted stale before (round 3
# of OPEN-63 lost hours to exactly this) -- refuse to run a "post-fix" backfill against pre-fix
# code.
if ! grep -q "_flhouse_waf_retry_verdict" openstates-scrapers/scrapers/fl/bills.py; then
  echo "ABORT: openstates-scrapers/scrapers/fl/bills.py doesn't have OPEN-66's fix" \
       "(_flhouse_waf_retry_verdict not found). Run 'git pull origin main' in" \
       "openstates-scrapers first." >&2
  exit 1
fi

BILLS=(
  HB1253 HB1265 HB1285 HB1293 HB139 HB1553 HB243 HB269
  HB283 HB299 HB309 HB313 HB339 HB371 HB53 HB99
)

LOG_DIR="logs/quality-check"
SUMMARY="$LOG_DIR/fl_open66_targeted_backfill_summary_20260815.txt"
: > "$SUMMARY"

for bill in "${BILLS[@]}"; do
  log="$LOG_DIR/fl_open66_scrape_${bill}_20260815.log"
  echo "=== $(date '+%H:%M:%S') scraping $bill ===" | tee -a "$SUMMARY"
  os-update fl --scrape bills session=2026 "bill_no=$bill" > "$log" 2>&1
  code=$?
  echo "$bill exit=$code" | tee -a "$SUMMARY"
  tail -n 5 "$log" | tee -a "$SUMMARY"
  echo "" | tee -a "$SUMMARY"
  sleep 8
done

echo "=== $(date '+%H:%M:%S') SCRAPE PHASE COMPLETE ===" | tee -a "$SUMMARY"
echo ""
echo "Scrape-only phase done -- no database was touched. Review $SUMMARY and the per-bill logs,"
echo "then confirm the votes actually landed in \$SCRAPED_DATA_DIR/fl (jq '.votes' on the JSON)"
echo "before importing. To import into PRODUCTION (not dev's isolated openstates_dev), run:"
echo ""
echo "  DATABASE_URL=\"postgresql://openstates:openstates_dev@localhost:5433/openstates\" \\"
echo "    os-update fl --import --cachedir \"\$CACHE_DIR\" --datadir \"\$SCRAPED_DATA_DIR\""
