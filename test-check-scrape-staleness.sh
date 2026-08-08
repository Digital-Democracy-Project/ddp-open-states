#!/usr/bin/env bash
# test-check-scrape-staleness.sh — fixture tests for check-scrape-staleness.sh (OPEN-40)
#
# No network, no production paths: every path the watchdog writes is redirected into
# a mktemp dir via the STALE_* test seams, and STALE_DRY_RUN=1 turns both alert paths
# into grep-able stdout lines instead of curl calls. Run it anywhere:
#     bash test-check-scrape-staleness.sh
# Exits 0 with "ALL PASS" or 1 with the first failing assertion.

set -u

WATCHDOG="$(cd "$(dirname "$0")" && pwd)/check-scrape-staleness.sh"
TMPDIR_ROOT=$(mktemp -d /tmp/staleness-test.XXXXXX)
trap 'rm -rf "$TMPDIR_ROOT"' EXIT

FIXTURE="$TMPDIR_ROOT/last-run"
mkdir -p "$FIXTURE"

PASS=0
FAIL=0

# Fixed "now" so ages are deterministic; markers are backdated relative to it with
# touch -t (BSD touch, local time — the watchdog reads mtime, not file contents).
NOW_EPOCH=$(date +%s)

run_watchdog() {
    STALE_LAST_RUN_DIR="$FIXTURE" \
    STALE_LOG_FILE="$TMPDIR_ROOT/test.log" \
    STALE_DRY_RUN=1 \
    STALE_NOW_EPOCH="$NOW_EPOCH" \
    STALE_WATCHLIST="$1" \
    bash "$WATCHDOG"
}

# touch_age <file> <hours_ago>
touch_age() {
    local ts
    ts=$(date -r $(( NOW_EPOCH - $2 * 3600 )) '+%Y%m%d%H%M.%S')
    touch -t "$ts" "$1"
}

assert_contains() {  # <label> <haystack> <needle>
    if echo "$2" | grep -qF "$3"; then
        echo "PASS: $1"; PASS=$((PASS + 1))
    else
        echo "FAIL: $1 — expected to find: $3"; echo "--- output was:"; echo "$2"; FAIL=$((FAIL + 1))
    fi
}

assert_not_contains() {  # <label> <haystack> <needle>
    if echo "$2" | grep -qF "$3"; then
        echo "FAIL: $1 — expected NOT to find: $3"; echo "--- output was:"; echo "$2"; FAIL=$((FAIL + 1))
    else
        echo "PASS: $1"; PASS=$((PASS + 1))
    fi
}

assert_file() {  # <label> <path> <exists|absent>
    if [ "$3" = "exists" ] && [ -f "$2" ]; then echo "PASS: $1"; PASS=$((PASS + 1))
    elif [ "$3" = "absent" ] && [ ! -f "$2" ]; then echo "PASS: $1"; PASS=$((PASS + 1))
    else echo "FAIL: $1 ($2 should be $3)"; FAIL=$((FAIL + 1)); fi
}

echo "=== 0. syntax check (bash 3.2 on this machine) ==="
if bash -n "$WATCHDOG"; then echo "PASS: bash -n"; PASS=$((PASS + 1)); else echo "FAIL: bash -n"; FAIL=$((FAIL + 1)); fi

echo "=== 1. fresh marker within threshold -> no alert, no sentinel ==="
touch "$FIXTURE/wa.ts"
OUT=$(run_watchdog "wa:48")
assert_not_contains "fresh wa emits no alert" "$OUT" "DRY_RUN slack"
assert_file "fresh wa writes no sentinel" "$FIXTURE/wa.stale-alerted" absent

echo "=== 2. marker older than threshold -> alert (slack + cams) + sentinel ==="
touch_age "$FIXTURE/wa.ts" 72
OUT=$(run_watchdog "wa:48")
assert_contains "stale wa alerts slack" "$OUT" "DRY_RUN slack: 🕰️ *OpenStates scrape stale: wa*"
assert_contains "stale wa reports age vs threshold" "$OUT" "72h (threshold 48h)"
assert_contains "stale wa alerts cams" "$OUT" "DRY_RUN cams: ScrapeStalenessDetected key=wa"
assert_file "stale wa writes sentinel" "$FIXTURE/wa.stale-alerted" exists

echo "=== 3. still stale on re-run -> silent (sentinel de-dupe) ==="
OUT=$(run_watchdog "wa:48")
assert_not_contains "second run does not re-alert" "$OUT" "DRY_RUN slack"
assert_not_contains "second run does not re-post cams" "$OUT" "DRY_RUN cams"
assert_file "sentinel still present" "$FIXTURE/wa.stale-alerted" exists

echo "=== 4. marker refreshed -> recovery message + sentinel cleared ==="
touch "$FIXTURE/wa.ts"
OUT=$(run_watchdog "wa:48")
assert_contains "recovery posts to slack" "$OUT" "DRY_RUN slack: ✅ *OpenStates scrape recovered: wa*"
assert_file "recovery removes sentinel" "$FIXTURE/wa.stale-alerted" absent
OUT=$(run_watchdog "wa:48")
assert_not_contains "recovered key stays silent afterwards" "$OUT" "DRY_RUN"

echo "=== 5. missing marker entirely -> maximally stale, alerts (not skips) ==="
OUT=$(run_watchdog "ma:228")
assert_contains "missing ma.ts alerts" "$OUT" "DRY_RUN slack: 🕰️ *OpenStates scrape stale: ma*"
assert_contains "missing marker reported as never-run" "$OUT" "never (no ma.ts marker)"
assert_file "missing-marker alert writes sentinel" "$FIXTURE/ma.stale-alerted" exists

echo "=== 6. weekly threshold boundary: 6-day-old marker is healthy at 228h ==="
touch_age "$FIXTURE/fl_session_2026.ts" 144
OUT=$(run_watchdog "fl_session_2026:228")
assert_not_contains "6-day-old FL Sunday marker does not alert at 228h" "$OUT" "DRY_RUN slack"

echo "=== 7. multi-key run: one stale key alerts, fresh keys untouched ==="
touch "$FIXTURE/va.ts"
touch_age "$FIXTURE/mi.ts" 336
OUT=$(run_watchdog "va:228
mi:228")
assert_contains "mi alerts in multi-key run" "$OUT" "OpenStates scrape stale: mi"
assert_not_contains "va stays silent in multi-key run" "$OUT" "stale: va"

echo ""
echo "RESULT: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] && { echo "ALL PASS"; exit 0; } || exit 1
