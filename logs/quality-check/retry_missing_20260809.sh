#!/usr/bin/env bash
# Retry pass for the 5 jurisdiction/session pairs that never completed a single
# attempt in run_full_sweep_20260809.sh (WA, VA/2026, MI, MA/194th, US/119) --
# all failed repeatedly on 429/ReadTimeout even with 90s cooldowns. This pass
# uses longer cooldowns (7 min) and a smaller Tier 2 sample (100 instead of 500)
# for just these five, to reduce total live-API load per attempt.
set -uo pipefail
cd "$(dirname "$0")/../.."

export OPENSTATES_API_KEY
OPENSTATES_API_KEY=$(grep '^OPENSTATES_API_KEY=' .env | cut -d= -f2-)

source .venv/bin/activate

PAIRS=(
  "wa 2025-2026"
  "va 2026"
  "mi 2025-2026"
  "ma 194th"
  "us 119"
)

SUMMARY=logs/quality-check/retry_missing_summary_20260809.txt
: > "$SUMMARY"

MAX_ATTEMPTS=5
COOLDOWN_SECONDS=420

for pair in "${PAIRS[@]}"; do
  read -r jur sess <<< "$pair"
  log="logs/quality-check/${jur}_${sess}_retry20260809.log"
  attempt=1
  while true; do
    echo "=== $(date '+%H:%M:%S') starting $jur $sess (attempt $attempt/$MAX_ATTEMPTS) ===" | tee -a "$SUMMARY"
    python3 quality_check.py --coverage "$jur" "$sess" --tier2-limit 100 --tier2-random \
      > "$log" 2>&1
    code=$?
    if grep -q "passed  |" "$log"; then
      echo "$jur $sess exit=$code (completed)" | tee -a "$SUMMARY"
      break
    fi
    echo "$jur $sess attempt $attempt CRASHED (exit=$code):" | tee -a "$SUMMARY"
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

echo "=== $(date '+%H:%M:%S') RETRY PASS COMPLETE ===" | tee -a "$SUMMARY"
