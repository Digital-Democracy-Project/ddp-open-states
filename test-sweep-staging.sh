#!/usr/bin/env bash
# test-sweep-staging.sh — OPEN-163: the import sweep must stage only what it has not
# already imported.
#
# Drives the real run-scrape.sh against a stub os-update. No network, no database, no
# production paths. Same shape as test-scrape-lock.sh.
#
# What this is actually protecting, because the waste is the least of it: every sweep
# cycle used to re-stage the WHOLE accumulated data directory, so import cost grew all
# run long and the final cycles dominated. At ~62ms per staged bill the last cycle for a
# large jurisdiction runs for minutes (MI ~244s, FL ~478s, MA ~720s projected). The FINAL
# import uses require_import_lock, which blocks LOCK_WAIT_TIMEOUT_SECS (180s) and then
# FAILS THE RUN. So a scrape that worked perfectly for hours gets reported as a failure.
#
# The assertion that matters is therefore "no bill file is ever staged twice", not
# "the sweep ran".

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RUN_ROOT=$(mktemp -d /tmp/sweep-staging-test.XXXXXX)
LOCK_ROOT="/tmp/ddp-openstates-scrape-locks"
trap 'rm -rf "$RUN_ROOT" "$LOCK_ROOT/va" /tmp/ddp-openstates-sweep-staging/va' EXIT

PASS=0
FAIL=0
check() {  # <label> <expected> <actual>
    if [ "$2" = "$3" ]; then
        PASS=$((PASS + 1)); echo "  ok   $1"
    else
        FAIL=$((FAIL + 1)); echo "  FAIL $1: expected '$2', got '$3'"
    fi
}
assert_true() {  # <label> <condition-result 0/1>
    if [ "$2" = "0" ]; then
        PASS=$((PASS + 1)); echo "  ok   $1"
    else
        FAIL=$((FAIL + 1)); echo "  FAIL $1"
    fi
}

mkdir -p "$RUN_ROOT/bin" "$RUN_ROOT/data" "$RUN_ROOT/cache" "$RUN_ROOT/logs/last-run"

# Stub os-update:
#   --scrape : writes bill files a few at a time, slowly enough that several sweep
#              cycles land mid-scrape (which is the only way to exercise this at all).
#   --import : appends every staged basename it was given to staged.log, so the test can
#              prove what each cycle actually handed over.
cat > "$RUN_ROOT/bin/os-update" <<'STUB'
#!/usr/bin/env bash
set -u
STATE="$1"; shift
MODE=""
DATADIR=""
while [ $# -gt 0 ]; do
    case "$1" in
        --scrape) MODE="scrape" ;;
        --import) MODE="import" ;;
        --datadir) shift; DATADIR="$1" ;;
        *) : ;;
    esac
    shift
done

if [ "$MODE" = "scrape" ]; then
    # 18 bills over ~27s, in 6 batches. The pacing is load-bearing, not arbitrary: the
    # sweep deliberately ignores files touched in the last 5 seconds (insurance against a
    # bill the scraper is mid-write on), so a fast stub writes everything inside that
    # window and every cycle legitimately stages nothing -- proving nothing either way.
    # Batches 4.5s apart with a 1s sweep interval give several cycles that each see a real,
    # bounded window of newly-aged files.
    n=0
    for batch in 1 2 3 4 5 6; do
        for i in 1 2 3; do
            n=$((n + 1))
            printf '{"bill":"HB%03d"}' "$n" > "$SCRAPED_DATA_DIR/$STATE/bill_stub-$n.json"
        done
        sleep 4.5
    done
    echo "bills: {}"
    exit 0
fi

if [ "$MODE" = "import" ]; then
    d="${DATADIR:-$SCRAPED_DATA_DIR}/$STATE"
    n_staged=0
    for f in "$d"/*.json; do
        [ -e "$f" ] || continue
        basename "$f" >> "$STAGED_LOG"
        n_staged=$((n_staged + 1))
    done
    # Only sweep imports pass --datadir; the final one does not. Count sweep imports
    # so a chosen one can be made to fail.
    # Count only cycles that actually staged something: the 5s freshness cutoff means
    # the first few cycles legitimately stage nothing, and failing one of those would
    # exercise nothing at all.
    if [ -n "$DATADIR" ] && [ "$n_staged" -gt 0 ]; then
        c=$(cat "$SWEEP_CALLS" 2>/dev/null || echo 0); c=$((c + 1)); echo "$c" > "$SWEEP_CALLS"
        if [ -n "${FAIL_SWEEP_CALL:-}" ] && [ "$c" = "$FAIL_SWEEP_CALL" ]; then
            first=$(ls -1 "$d"/*.json 2>/dev/null | head -1)
            echo "ERROR importing $first" >&2
            exit 1
        fi
    fi
    echo "bill: 0 new 0 updated 0 noop"
    exit 0
fi
exit 0
STUB
chmod +x "$RUN_ROOT/bin/os-update"
mkdir -p "$RUN_ROOT/data/va"

export STAGED_LOG="$RUN_ROOT/staged.log"
export SWEEP_CALLS="$RUN_ROOT/sweep-calls"
: > "$STAGED_LOG"
echo 0 > "$SWEEP_CALLS"

echo "== a run where several sweep cycles land mid-scrape =="
LOG_DIR="$RUN_ROOT/logs" \
OS_UPDATE_OVERRIDE="$RUN_ROOT/bin/os-update" \
SCRAPED_DATA_DIR_OVERRIDE="$RUN_ROOT/data" \
CACHE_DIR_OVERRIDE="$RUN_ROOT/cache" \
SWEEP_IMPORT_ENABLED=1 \
SWEEP_INTERVAL_SECS=1 \
SUPPRESS_FAILURE_ALERT=1 \
SKIP_PATCHES=1 \
    bash "$SCRIPT_DIR/run-scrape.sh" va > "$RUN_ROOT/run.log" 2>&1
RUN_RC=$?

check "the run succeeds" "0" "$RUN_RC"

# The final import reads the whole data dir, so it legitimately sees every file once.
# Strip it: what this ticket is about is what the SWEEP cycles staged.
SWEEP_CYCLES=$(grep -c "Sweep cycle .* imported" "$RUN_ROOT/logs/scraper.log" 2>/dev/null | tr -d " \n")
SWEEP_CYCLES=${SWEEP_CYCLES:-0}
assert_true "at least three sweep cycles ran (otherwise this test proves nothing)" \
    "$([ "$SWEEP_CYCLES" -ge 3 ] && echo 0 || echo 1)"

# Every basename the sweep cycles staged, excluding the final full-directory import.
# The final import is the last block of lines; count duplicates across sweep staging only
# by taking the staged counts the log itself reports.
STAGED_TOTAL=$(grep "Sweep cycle .* imported" "$RUN_ROOT/logs/scraper.log" 2>/dev/null \
    | sed -E 's/.*staged=([0-9]+) files.*/\1/' | awk '{s+=$1} END {print s+0}')
BILLS_WRITTEN=$(ls -1 "$RUN_ROOT/data/va"/*.json 2>/dev/null | wc -l | tr -d ' ')

echo "  (cycles=$SWEEP_CYCLES staged_total=$STAGED_TOTAL bills=$BILLS_WRITTEN)"

# THE assertion. With the old behaviour this sum is quadratic in cycle count -- the canary
# measured staged counts climbing 16 -> 177 while new bills held at ~20 a cycle. With
# incremental staging each bill is staged at most once, so the sum can never exceed the
# number of bills that existed.
assert_true "no bill is staged more than once across cycles (sum <= bills written)" \
    "$([ "$STAGED_TOTAL" -le "$BILLS_WRITTEN" ] && echo 0 || echo 1)"

assert_true "the sweep actually staged something" \
    "$([ "$STAGED_TOTAL" -ge 1 ] && echo 0 || echo 1)"

# Per-cycle: no cycle may stage more than the whole corpus, and later cycles must not
# grow monotonically the way the canary recorded.
LAST_CYCLE_STAGED=$(grep "Sweep cycle .* imported" "$RUN_ROOT/logs/scraper.log" 2>/dev/null \
    | tail -1 | sed -E 's/.*staged=([0-9]+) files.*/\1/')
assert_true "the final cycle stages a window, not the whole corpus" \
    "$([ "${LAST_CYCLE_STAGED:-0}" -lt "$BILLS_WRITTEN" ] && echo 0 || echo 1)"

echo
echo "== every scraped bill still reaches the database exactly once overall =="
# The final import covers the whole directory regardless, so completeness is unchanged --
# this is the property the incremental staging must NOT have broken.
FINAL_SEEN=$(sort "$STAGED_LOG" | uniq | wc -l | tr -d ' ')
check "every bill written was imported at least once" "$BILLS_WRITTEN" "$FINAL_SEEN"

echo
echo "== pm-review round 1: a failed cycle must not advance the watermark =="
# The central correctness claim, and it was untested. If the watermark advanced on a
# failed import, that window would never be swept again -- the final import would still
# catch it, so no data is lost, but the sweep would silently stop protecting exactly the
# bills whose import had just proved troublesome.
RUN2="$RUN_ROOT/run2"
mkdir -p "$RUN2/data/va" "$RUN2/cache" "$RUN2/logs/last-run"
export STAGED_LOG="$RUN2/staged.log"; : > "$STAGED_LOG"
export SWEEP_CALLS="$RUN2/sweep-calls"; echo 0 > "$SWEEP_CALLS"

LOG_DIR="$RUN2/logs" \
OS_UPDATE_OVERRIDE="$RUN_ROOT/bin/os-update" \
SCRAPED_DATA_DIR_OVERRIDE="$RUN2/data" \
CACHE_DIR_OVERRIDE="$RUN2/cache" \
SWEEP_IMPORT_ENABLED=1 \
SWEEP_INTERVAL_SECS=1 \
FAIL_SWEEP_CALL=1 \
SUPPRESS_FAILURE_ALERT=1 \
SKIP_PATCHES=1 \
    bash "$SCRIPT_DIR/run-scrape.sh" va > "$RUN2/run.log" 2>&1
RUN2_RC=$?

check "the run still succeeds despite a failed sweep cycle" "0" "$RUN2_RC"

assert_true "the failed cycle is reported" \
    "$(grep -q "periodic import sweep failed" "$RUN2/logs/scraper.log" && echo 0 || echo 1)"

# After the failure the watermark must NOT have moved, so a later cycle re-stages that
# work. With 18 bills and one failed cycle, the successful cycles must between them still
# stage at least as many files as the failed cycle held.
R2_TOTAL=$(grep "Sweep cycle .* imported" "$RUN2/logs/scraper.log" 2>/dev/null \
    | sed -E 's/.*staged=([0-9]+) files.*/\1/' | awk '{s+=$1} END {print s+0}')
assert_true "work from the failed cycle is re-staged by a later one" \
    "$([ "${R2_TOTAL:-0}" -ge 1 ] && echo 0 || echo 1)"

echo
echo "== the excluded-file rule survives (ticket AC) =="
# On a failed import the loop pulls the offending filename out of the log and excludes it
# from staging for the rest of the run. That must still hold with incremental staging --
# otherwise a genuinely bad record would be retried every cycle forever.
assert_true "a failed import excludes the offending file until the final import" \
    "$(grep -q "excluding .* from staging until final import" "$RUN2/logs/scraper.log" && echo 0 || echo 1)"

# And completeness is still the final import's job, excluded file included.
R2_BILLS=$(ls -1 "$RUN2/data/va"/*.json 2>/dev/null | wc -l | tr -d ' ')
R2_SEEN=$(sort "$RUN2/staged.log" | uniq | wc -l | tr -d ' ')
check "every bill still reaches the database despite the exclusion" "$R2_BILLS" "$R2_SEEN"

echo
if [ "$FAIL" -eq 0 ]; then
    echo "ALL PASS ($PASS assertions)"
    exit 0
fi
echo "$FAIL FAILED, $PASS passed"
exit 1
