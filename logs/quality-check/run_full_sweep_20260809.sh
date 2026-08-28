#!/usr/bin/env bash
# One-off driver for the 2026-08-09 full tier1+tier2 sweep across all tracked
# jurisdictions. Not meant to be reused/committed as tooling -- ad hoc for this run.
#
# v2: AL dropped (nothing scrapes it), tier2 sample bumped to 500, and each pair
# gets cooldown-retried on a live-API crash (429/network) -- but NOT retried just
# because the run completed with real Tier1/Tier2 failures, which is a valid
# result, not a crash. Distinguished by whether the report's summary line
# ("N/M passed | ...") made it into the log: a crash never reaches that print.
set -uo pipefail
cd "$(dirname "$0")/../.."

export OPENSTATES_API_KEY
OPENSTATES_API_KEY=$(grep '^OPENSTATES_API_KEY=' .env | cut -d= -f2-)

source .venv/bin/activate

PAIRS=(
  "ut 2025S2"
  "va 2026S1"
  "ut 2026"
  "fl 2026"
  "az 57th-2nd-regular"
  "wa 2025-2026"
  "va 2026"
  "mi 2025-2026"
  "ma 194th"
  "us 119"
)

SUMMARY=logs/quality-check/sweep_summary_20260809.txt
: > "$SUMMARY"

MAX_ATTEMPTS=5
COOLDOWN_SECONDS=90

for pair in "${PAIRS[@]}"; do
  read -r jur sess <<< "$pair"
  log="logs/quality-check/${jur}_${sess}_fresh20260809.log"
  attempt=1
  while true; do
    echo "=== $(date '+%H:%M:%S') starting $jur $sess (attempt $attempt/$MAX_ATTEMPTS) ===" | tee -a "$SUMMARY"
    python3 quality_check.py --coverage "$jur" "$sess" --tier2-limit 500 --tier2-random \
      > "$log" 2>&1
    code=$?
    if grep -q "passed  |" "$log"; then
      echo "$jur $sess exit=$code (completed)" | tee -a "$SUMMARY"
      break
    fi
    echo "$jur $sess attempt $attempt CRASHED (exit=$code) -- likely rate-limited:" | tee -a "$SUMMARY"
    tail -n 4 "$log" | tee -a "$SUMMARY"
    if [ "$attempt" -ge "$MAX_ATTEMPTS" ]; then
      echo "$jur $sess: giving up after $MAX_ATTEMPTS attempts" | tee -a "$SUMMARY"
      break
    fi
    echo "  ...cooling down ${COOLDOWN_SECONDS}s before retry" | tee -a "$SUMMARY"
    sleep "$COOLDOWN_SECONDS"
    attempt=$((attempt + 1))
  done
  tail -n 6 "$log" | tee -a "$SUMMARY"
  echo "" | tee -a "$SUMMARY"
done

echo "=== $(date '+%H:%M:%S') SWEEP COMPLETE ===" | tee -a "$SUMMARY"
