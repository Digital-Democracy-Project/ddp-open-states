#!/usr/bin/env bash
# test-scrape-lock.sh — end-to-end tests for OPEN-154's same-jurisdiction scrape lock
#
# Drives the real run-scrape.sh against a stub os-update. No network, no database, no
# production paths: LOG_DIR is redirected and the *_OVERRIDE variables (OPEN-152) keep
# activate.sh from clobbering the stub.
#
#     bash test-scrape-lock.sh
#
# What is being guarded: openstates-core's do_scrape() wipes $SCRAPED_DATA_DIR/$STATE at the
# start of a scrape, so a second concurrent run of the same jurisdiction destroys the first's
# work and both then race to write the watermark. Nothing prevented that before this change.
#
# The assertions worth reading twice are the ones about what the BLOCKED run must not do. A
# blocked run that writes markers is worse than no lock at all: it would advance the watermark
# past a window it never collected, which is OPEN-152's bug arriving by a new route.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOCK_ROOT="/tmp/ddp-openstates-scrape-locks"
PASS=0
FAIL=0

check() {
    local desc="$1" expected="$2" actual="$3"
    if [ "$expected" = "$actual" ]; then
        PASS=$((PASS + 1)); echo "  ok   $desc"
    else
        FAIL=$((FAIL + 1)); echo "  FAIL $desc"
        echo "         expected: [$expected]"
        echo "         actual  : [$actual]"
    fi
}

setup() {
    RUN_ROOT=$(mktemp -d /tmp/scrape-lock-test.XXXXXX)
    RUN_LOG_DIR="$RUN_ROOT/logs"
    mkdir -p "$RUN_LOG_DIR/last-run" "$RUN_ROOT/bin"
    # A watermark must exist or the run is MODE=full, and finish_no_op only applies to
    # incremental runs — the "writes its marker" assertions would then be vacuous.
    printf '2026-01-01T00:00:00' > "$RUN_LOG_DIR/last-run/va.ts"
    # Benign no-op output: the run should reach finish_no_op and write markers, so the "blocked
    # run writes nothing" assertions below are meaningful rather than vacuous.
    cat > "$RUN_ROOT/bin/os-update" <<'STUB'
#!/usr/bin/env bash
printf '%s\n' "INFO openstates: VA search returned a results page with no matching bills -- genuine empty result for this window"
printf '%s\n' "openstates.exceptions.ScrapeError: no objects returned from VaBillScraper scrape"
exit 1
STUB
    chmod +x "$RUN_ROOT/bin/os-update"
}

run_scrape() {
    LOG_DIR="$RUN_LOG_DIR" \
    OS_UPDATE_OVERRIDE="$RUN_ROOT/bin/os-update" \
    SCRAPED_DATA_DIR_OVERRIDE="$RUN_ROOT/data" \
    CACHE_DIR_OVERRIDE="$RUN_ROOT/cache" \
    SUPPRESS_FAILURE_ALERT=1 \
    SKIP_PATCHES=1 \
        bash "$SCRIPT_DIR/run-scrape.sh" va > "$RUN_ROOT/run.log" 2>&1
    RUN_RC=$?
}

marker() { cat "$RUN_LOG_DIR/last-run/$1" 2>/dev/null || echo "<absent>"; }
cleanup() { rm -rf "$RUN_ROOT" "$LOCK_ROOT/va"; }

echo "== an uncontended run is unaffected =="

setup
rm -rf "$LOCK_ROOT/va"
run_scrape
check "uncontended: exits 0" "0" "$RUN_RC"
check "uncontended: writes its marker" "ok:0:0:0:incremental" "$(marker va.imported)"
check "uncontended: releases the lock on exit" "gone" \
    "$([ -d "$LOCK_ROOT/va" ] && echo present || echo gone)"
cleanup

echo "== a second run is refused while a live holder exists =="

setup
# A lock held by THIS test process, which is demonstrably alive — so the dead-holder reclaim
# path must not fire and the run must be refused.
mkdir -p "$LOCK_ROOT/va"
echo $$ > "$LOCK_ROOT/va/pid"
run_scrape
check "contended: exits EXIT_DO_NOT_RETRY (90)" "90" "$RUN_RC"
check "contended: says why" "yes" \
    "$(grep -q 'OPEN-154' "$RUN_LOG_DIR/scraper.log" && echo yes || echo no)"
# The important pair. A blocked run that writes these would advance the watermark past a window
# it never collected — OPEN-152's bug, arriving by a different route.
# Unchanged, not absent: setup seeds a watermark so the run is incremental. What matters is
# that the blocked run does not ADVANCE it past a window it never collected.
check "contended: does NOT advance the watermark" "2026-01-01T00:00:00" "$(marker va.ts)"
check "contended: writes NO measurement" "<absent>" "$(marker va.imported)"
check "contended: does NOT release the holder's lock" "present" \
    "$([ -d "$LOCK_ROOT/va" ] && echo present || echo gone)"
rm -rf "$LOCK_ROOT/va"
cleanup

echo "== a lock left by a dead process is reclaimed =="

setup
mkdir -p "$LOCK_ROOT/va"
# A pid that cannot be running. Without reclamation a single crashed run would wedge the
# jurisdiction permanently, which is worse than the bug being fixed.
echo "999999" > "$LOCK_ROOT/va/pid"
run_scrape
check "dead holder: run proceeds" "0" "$RUN_RC"
check "dead holder: says it reclaimed" "yes" \
    "$(grep -q 'held by dead pid' "$RUN_LOG_DIR/scraper.log" && echo yes || echo no)"
check "dead holder: writes its marker" "ok:0:0:0:incremental" "$(marker va.imported)"
cleanup

echo "== a lock directory with no pid file does not wedge the jurisdiction forever =="

setup
mkdir -p "$LOCK_ROOT/va"   # no pid file at all — e.g. killed between mkdir and the write
run_scrape
# Documents the CHOSEN behaviour rather than asserting it is ideal: an empty lock dir is
# treated as held, because a pid-less lock is indistinguishable from a holder that has not
# written its pid yet, and wrongly stealing a live lock is the worse error. It self-heals on
# the next run once the real holder exits and removes the directory.
check "no pid file: treated as held (conservative)" "90" "$RUN_RC"
rm -rf "$LOCK_ROOT/va"
cleanup

echo "== the retry wrapper must be told not to retry =="

setup
mkdir -p "$LOCK_ROOT/va"; echo $$ > "$LOCK_ROOT/va/pid"
FLAG="$RUN_ROOT/do-not-retry"
LOG_DIR="$RUN_LOG_DIR" OS_UPDATE_OVERRIDE="$RUN_ROOT/bin/os-update" \
SCRAPED_DATA_DIR_OVERRIDE="$RUN_ROOT/data" CACHE_DIR_OVERRIDE="$RUN_ROOT/cache" \
SUPPRESS_FAILURE_ALERT=1 SKIP_PATCHES=1 DO_NOT_RETRY_FLAG="$FLAG" \
    bash "$SCRIPT_DIR/run-scrape.sh" va > "$RUN_ROOT/run.log" 2>&1
# run-scrape-retrying.sh decides on the FLAG, not the exit code -- its own comment says so.
# Without this the wrapper would re-invoke and collide again on every attempt, which is exactly
# what this ticket exists to stop.
check "contended: sets DO_NOT_RETRY_FLAG" "set" "$([ -f "$FLAG" ] && echo set || echo unset)"
rm -rf "$LOCK_ROOT/va"; cleanup

echo "== a pid-less lock ages out rather than wedging the jurisdiction forever =="

setup
mkdir -p "$LOCK_ROOT/va"
# Backdate past the 24h threshold: a run killed between mkdir and the pid write leaves exactly
# this, and refusing forever would be a permanent outage for the jurisdiction.
touch -t "$(date -v-2d '+%Y%m%d%H%M' 2>/dev/null || date -d '2 days ago' '+%Y%m%d%H%M')" "$LOCK_ROOT/va"
run_scrape
check "abandoned pid-less lock: reclaimed and run proceeds" "0" "$RUN_RC"
check "abandoned pid-less lock: says it reclaimed" "yes" \
    "$(grep -q 'no pid file and is over 24h old' "$RUN_LOG_DIR/scraper.log" && echo yes || echo no)"
rm -rf "$LOCK_ROOT/va"; cleanup

echo "== different jurisdictions never contend =="

setup
mkdir -p "$LOCK_ROOT/ut"; echo $$ > "$LOCK_ROOT/ut/pid"   # UT held by a live process
rm -rf "$LOCK_ROOT/va"
run_scrape                                                # VA must be unaffected
check "va runs while ut is locked" "0" "$RUN_RC"
check "va writes its marker" "ok:0:0:0:incremental" "$(marker va.imported)"
rm -rf "$LOCK_ROOT/ut" "$LOCK_ROOT/va"; cleanup

echo "== a malformed jurisdiction key is refused before any path is built =="

setup
LOG_DIR="$RUN_LOG_DIR" SUPPRESS_FAILURE_ALERT=1 SKIP_PATCHES=1 \
    bash "$SCRIPT_DIR/run-scrape.sh" "../../etc" > "$RUN_ROOT/bad.log" 2>&1
check "traversal key refused" "yes" "$([ $? -ne 0 ] && echo yes || echo no)"
cleanup

echo
if [ "$FAIL" -eq 0 ]; then
    echo "ALL PASS ($PASS assertions)"
    exit 0
fi
echo "$FAIL FAILED, $PASS passed"
exit 1
