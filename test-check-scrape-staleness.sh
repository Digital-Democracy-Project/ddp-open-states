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

# run_watchdog_at <hours_after_NOW> <watchlist> — same, with "now" pushed forward so
# an episode can age without the test sleeping (OPEN-130 escalation tiers). The
# marker stays put and time moves, which is what actually happens in production.
run_watchdog_at() {
    STALE_LAST_RUN_DIR="$FIXTURE" \
    STALE_LOG_FILE="$TMPDIR_ROOT/test.log" \
    STALE_DRY_RUN=1 \
    STALE_NOW_EPOCH="$(( NOW_EPOCH + $1 * 3600 ))" \
    STALE_WATCHLIST="$2" \
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

# === OPEN-130: self-evidencing alerts + escalation tiers ==========================
#
# Reproduces the az timeline from OPEN-130: tripped at 229h against a 228h weekly
# threshold ("reads as a rounding error"), then silence while it grew to 14 days.
# The marker is placed once and "now" walks forward, as it does in production.

echo "=== 8. first alert is self-evidencing (missed runs + absolute last-success date) ==="
touch_age "$FIXTURE/az.ts" 229
LAST_SUCCESS_DATE=$(date -r $(( NOW_EPOCH - 229 * 3600 )) '+%Y-%m-%d')
OUT=$(run_watchdog "az:228")
assert_contains "first alert names missed scheduled runs" "$OUT" "1 scheduled weekly run(s) missed"
assert_contains "first alert states staleness in days, not just hours" "$OUT" "no successful scrape in 9 days"
assert_contains "first alert names the absolute last-success date" "$OUT" "Last success: $LAST_SUCCESS_DATE"
assert_contains "first alert states the multiple of threshold" "$OUT" "× threshold"
assert_contains "cams metadata carries the missed-run count" "$OUT" "missed_runs=1"
assert_contains "cams detail block replaces the empty stacktrace" "$OUT" "scheduled runs missed:  1"
assert_contains "cams details rule out the out-of-session explanation" "$OUT" "out of session does NOT explain this"
assert_file "first alert writes sentinel" "$FIXTURE/az.stale-alerted" exists
assert_contains "sentinel records the tier" "$(cat "$FIXTURE/az.stale-alerted")" "tier=1"
assert_contains "sentinel records the first-alert age" "$(cat "$FIXTURE/az.stale-alerted")" "first_alerted_age_hours=229"

echo "=== 9. between tiers (329h, the real az 14-day point) -> still silent ==="
OUT=$(run_watchdog_at 100 "az:228")
assert_not_contains "no re-alert below 2x threshold" "$OUT" "DRY_RUN slack"
assert_not_contains "no re-post to cams below 2x threshold" "$OUT" "DRY_RUN cams"

echo "=== 10. crossing 2x threshold (460h) -> escalated re-alert ==="
OUT=$(run_watchdog_at 231 "az:228")
assert_contains "2x escalation alerts slack" "$OUT" "OpenStates scrape STILL stale and getting worse: az"
assert_contains "2x escalation says twice past threshold" "$OUT" "twice past its threshold"
assert_contains "2x escalation shows the growth from the first alert" "$OUT" "Was 229h when first alerted"
assert_contains "2x escalation marks it the same episode, not a new outage" "$OUT" "same unresolved episode escalating"
assert_contains "2x escalation reports the grown missed-run count" "$OUT" "2 scheduled weekly run(s) missed"
assert_contains "2x escalation re-posts to cams with tier" "$OUT" "tier=2"
assert_contains "sentinel bumped to tier 2" "$(cat "$FIXTURE/az.stale-alerted")" "tier=2"
assert_contains "sentinel preserves the original first-alert age" "$(cat "$FIXTURE/az.stale-alerted")" "first_alerted_age_hours=229"

echo "=== 11. between 2x and 4x (629h) -> silent again (de-dupe still holds) ==="
OUT=$(run_watchdog_at 400 "az:228")
assert_not_contains "no re-alert between 2x and 4x" "$OUT" "DRY_RUN slack"

echo "=== 12. crossing 4x threshold (929h) -> second escalation, distinct wording ==="
OUT=$(run_watchdog_at 700 "az:228")
assert_contains "4x escalation alerts slack" "$OUT" "OpenStates scrape SEVERELY stale: az"
assert_contains "4x escalation says four times past threshold" "$OUT" "four times past its threshold"
assert_contains "4x escalation reports 5 missed weekly runs" "$OUT" "5 scheduled weekly run(s) missed"
assert_contains "sentinel bumped to tier 4" "$(cat "$FIXTURE/az.stale-alerted")" "tier=4"
# Wording (not just numbers) differs per tier because CAMS fingerprints failures
# with all digits normalized to <n> — same words at 2x and 4x would de-dupe away.
assert_not_contains "4x wording differs from 2x wording" "$OUT" "STILL stale and getting worse"

echo "=== 13. past the top tier (1129h) -> silent, no alert storm ==="
OUT=$(run_watchdog_at 900 "az:228")
assert_not_contains "no alerts above the top tier" "$OUT" "DRY_RUN slack"

echo "=== 14. recovery clears escalation state; a later episode starts at tier 1 ==="
touch -t "$(date -r $(( NOW_EPOCH + 900 * 3600 )) '+%Y%m%d%H%M.%S')" "$FIXTURE/az.ts"
OUT=$(run_watchdog_at 900 "az:228")
assert_contains "recovery posts after escalation" "$OUT" "OpenStates scrape recovered: az"
assert_file "recovery removes escalation sentinel" "$FIXTURE/az.stale-alerted" absent
touch_age "$FIXTURE/az.ts" 300
OUT=$(run_watchdog "az:228")
assert_contains "new episode alerts as a first alert, not an escalation" "$OUT" "🕰️ *OpenStates scrape stale: az*"
assert_not_contains "new episode is not worded as an escalation" "$OUT" "same unresolved episode"
assert_contains "new episode sentinel restarts tier accounting" "$(cat "$FIXTURE/az.stale-alerted")" "first_alerted_age_hours=300"

echo "=== 15. pre-OPEN-130 sentinel (bare timestamp) upgrades without re-alerting ==="
touch_age "$FIXTURE/ut.ts" 300
date -u +%Y-%m-%dT%H:%M:%S > "$FIXTURE/ut.stale-alerted"   # old-format sentinel
OUT=$(run_watchdog "ut:228")
assert_not_contains "legacy sentinel still suppresses the tier-1 repeat" "$OUT" "DRY_RUN slack"
OUT=$(run_watchdog_at 200 "ut:228")
assert_contains "legacy sentinel still escalates at 2x" "$OUT" "OpenStates scrape STILL stale and getting worse: ut"
assert_not_contains "legacy sentinel claims no growth baseline it doesn't have" "$OUT" "Was 300h when first alerted"
assert_contains "legacy sentinel says so plainly in the detail block" "$OUT" "first-alert details unrecorded"

echo "=== 16. malformed tier= in a sentinel must not silently suppress the alert ==="
# `[ x -gt y ]` on a non-numeric value is an error that evaluates false under
# `set -uo pipefail` — i.e. silence, the exact failure OPEN-130 exists to remove.
touch_age "$FIXTURE/va.ts" 300
printf 'tier=oops\n' > "$FIXTURE/va.stale-alerted"
OUT=$(run_watchdog "va:228")
assert_contains "malformed tier still alerts" "$OUT" "OpenStates scrape stale: va"
assert_contains "malformed tier is logged, not swallowed" "$OUT" "non-numeric tier"
assert_contains "malformed sentinel is rewritten cleanly" "$(cat "$FIXTURE/va.stale-alerted")" "tier=1"
OUT=$(run_watchdog "va:228")
assert_not_contains "self-healed sentinel then de-dupes normally" "$OUT" "DRY_RUN slack"

echo "=== 17. Slack payload invariant: single line, no JSON-breaking characters ==="
# post_slack() builds its JSON inline in bash, so a newline, double quote or
# backslash in the message would produce an invalid request body. The multi-line
# evidence block must stay confined to the CAMS path (python3 json.dumps).
touch_age "$FIXTURE/mi.ts" 500
rm -f "$FIXTURE/mi.stale-alerted"
SLACK_LINES=$(run_watchdog "mi:228" | grep -c '^DRY_RUN slack')
if [ "$SLACK_LINES" = "1" ]; then
    echo "PASS: alert produces exactly one Slack line"; PASS=$((PASS + 1))
else
    echo "FAIL: alert produced $SLACK_LINES Slack lines (expected 1 — message must not contain newlines)"; FAIL=$((FAIL + 1))
fi
rm -f "$FIXTURE/mi.stale-alerted"
SLACK_MSG=$(run_watchdog "mi:228" | grep '^DRY_RUN slack')
if echo "$SLACK_MSG" | grep -q '["\\]'; then
    echo "FAIL: Slack message contains a JSON-breaking character: $SLACK_MSG"; FAIL=$((FAIL + 1))
else
    echo "PASS: Slack message has no unescaped quote or backslash"; PASS=$((PASS + 1))
fi
# Same invariant on the escalation and recovery wordings, not just the first alert.
SLACK_MSG=$(run_watchdog_at 500 "mi:228" | grep '^DRY_RUN slack')
assert_contains "escalation path exercised for this check" "$SLACK_MSG" "past its threshold"
if echo "$SLACK_MSG" | grep -q '["\\]'; then
    echo "FAIL: escalation message contains a JSON-breaking character"; FAIL=$((FAIL + 1))
else
    echo "PASS: escalation message has no unescaped quote or backslash"; PASS=$((PASS + 1))
fi

# ===================================================================================
# OPEN-135: the watchlist is derived from ddp-sync's schedule, not hardcoded here
# ===================================================================================
#
# These drive the real script with STALE_WATCHLIST UNSET, which is the only way to
# exercise derive_watchlist(). Every other test above sets it, so the derivation was
# entirely uncovered until now.

SCHED="$TMPDIR_ROOT/sync_schedule.yaml"

write_schedule() {  # $1 = fl sync_day line ("" for daily)
    cat > "$SCHED" <<YAML
openstates_scrape:
  primary:
    fl:
      enabled: true
      sync_time_utc: "02:00"
      ${1}
      sessions:
        - "2026"
        - "2026F"
    wa:
      enabled: true
      sync_time_utc: "02:30"
    disabled_juris:
      enabled: false
      sync_time_utc: "02:00"
  secondary:
    enabled: true
    sync_day: sunday
    sync_time_utc: "02:00"
    jurisdictions:
      - va
      - mi
YAML
}

run_derived() {  # runs with the derivation live; $1 = optional extra env assignment
    STALE_LAST_RUN_DIR="$FIXTURE" STALE_LOG_FILE="$TMPDIR_ROOT/test.log" \
    STALE_DRY_RUN=1 STALE_NOW_EPOCH="${2:-$NOW_EPOCH}" \
    STALE_SCHEDULE_FILE="$SCHED" ${1:-} bash "$WATCHDOG" 2>&1
}

echo ""
echo "=== 18. OPEN-135: watchlist derived from the schedule file ==="
write_schedule 'sync_day: sunday'
rm -f "$FIXTURE"/*.ts "$FIXTURE"/*.stale-alerted 2>/dev/null
OUT=$(run_derived)
assert_contains "derivation reports how many keys it watches" "$OUT" "derived from"
# Session-qualified primary keys, bare secondary keys (OPEN-24), disabled juris skipped.
for k in fl_session_2026 fl_session_2026F wa va mi; do
    if echo "$OUT" | grep -q "$k"; then
        echo "PASS: derived watchlist includes $k"; PASS=$((PASS + 1))
    else
        echo "FAIL: derived watchlist missing $k"; FAIL=$((FAIL + 1))
    fi
done
if echo "$OUT" | grep -q "disabled_juris"; then
    echo "FAIL: watched a jurisdiction with enabled: false"; FAIL=$((FAIL + 1))
else
    echo "PASS: a jurisdiction with enabled: false is not watched"; PASS=$((PASS + 1))
fi

echo ""
echo "=== 19. OPEN-135: an unreadable schedule ALERTS, never watches nothing quietly ==="
OUT=$(STALE_LAST_RUN_DIR="$FIXTURE" STALE_LOG_FILE="$TMPDIR_ROOT/test.log" \
      STALE_DRY_RUN=1 STALE_NOW_EPOCH="$NOW_EPOCH" \
      STALE_SCHEDULE_FILE="$TMPDIR_ROOT/does-not-exist.yaml" bash "$WATCHDOG" 2>&1); RC=$?
assert_contains "missing schedule alerts to Slack" "$OUT" "cannot read the scrape schedule"
assert_contains "missing schedule says it is watching nothing" "$OUT" "watching NOTHING"
if [ "$RC" -ne 0 ]; then
    echo "PASS: missing schedule exits non-zero"; PASS=$((PASS + 1))
else
    echo "FAIL: missing schedule exited 0 — a blind watchdog must not look healthy"; FAIL=$((FAIL + 1))
fi

printf 'this: is: not: valid: yaml: [\n' > "$TMPDIR_ROOT/broken.yaml"
OUT=$(STALE_LAST_RUN_DIR="$FIXTURE" STALE_LOG_FILE="$TMPDIR_ROOT/test.log" \
      STALE_DRY_RUN=1 STALE_NOW_EPOCH="$NOW_EPOCH" \
      STALE_SCHEDULE_FILE="$TMPDIR_ROOT/broken.yaml" bash "$WATCHDOG" 2>&1)
assert_contains "unparseable schedule alerts too" "$OUT" "cannot read the scrape schedule"

printf 'some_other_block:\n  a: 1\n' > "$TMPDIR_ROOT/nokeys.yaml"
OUT=$(STALE_LAST_RUN_DIR="$FIXTURE" STALE_LOG_FILE="$TMPDIR_ROOT/test.log" \
      STALE_DRY_RUN=1 STALE_NOW_EPOCH="$NOW_EPOCH" \
      STALE_SCHEDULE_FILE="$TMPDIR_ROOT/nokeys.yaml" bash "$WATCHDOG" 2>&1)
assert_contains "a schedule with no openstates_scrape block alerts" "$OUT" "cannot read the scrape schedule"

echo ""
echo "=== 20. OPEN-135: FL flipping daily<->weekly needs no edit to this script ==="
write_schedule 'sync_day: sunday'
W1=$(run_derived | grep -o 'watching [0-9]* keys')
write_schedule ''
W2=$(run_derived | grep -o 'watching [0-9]* keys')
if [ "$W1" = "$W2" ]; then
    echo "PASS: same keys watched whether FL is daily or weekly ($W1)"; PASS=$((PASS + 1))
else
    echo "FAIL: key count changed with cadence ($W1 vs $W2)"; FAIL=$((FAIL + 1))
fi

echo ""
echo "RESULT: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] && { echo "ALL PASS"; exit 0; } || exit 1
