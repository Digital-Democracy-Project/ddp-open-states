#!/usr/bin/env bash
# test-no-op-side-effects.sh — end-to-end tests for OPEN-152's decision, through run-scrape.sh
#
# test-scrape-outcome.sh covers the matcher in isolation. This covers the thing that actually
# matters, which the matcher tests cannot see: what run-scrape.sh DOES with the answer.
#
# The product requirement is not "classify it as a failure". It is:
#   * a genuine no-op still exits 0, advances the watermark, and records ok:0:0:0
#   * an unreachable site does NOT advance the watermark and does NOT record a measurement,
#     so the window stays eligible for the next run
#
# The second is the whole point of the ticket, and asserting it needs the real script. A stub
# os-update stands in for the scraper; no network, no database, no production paths -- LOG_DIR
# and OS_UPDATE are both redirected, and SUPPRESS_FAILURE_ALERT stops the failure path firing
# real Slack/CAMS alerts.
#
# Deliberately uses MI's unrecognised-page marker rather than a WAF marker: the WAF branch sets
# SUPPRESS_FAILURE_ALERT=0 on purpose (a WAF block must always alert), so a WAF fixture here
# would send real alerts. The unrecognised-page shape is also the actual 2026-08-24 incident.
#
#     bash test-no-op-side-effects.sh

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
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

# SKIP_PATCHES=1 matters: without it run-scrape.sh git-pulls the live nested checkouts, so a
# test run would reach into production state. Found the hard way.
# Builds a throwaway LOG_DIR plus a stub os-update that emits $1 and exits $2, then runs
# run-scrape.sh against them. Echoes the run's exit code; markers are left in $RUN_LOG_DIR.
run_with_stub() {
    local stub_output="$1" stub_exit="$2" seed_ts="${3:-}"
    RUN_ROOT=$(mktemp -d /tmp/no-op-side-effects.XXXXXX)
    RUN_LOG_DIR="$RUN_ROOT/logs"
    mkdir -p "$RUN_LOG_DIR/last-run" "$RUN_ROOT/bin"
    [ -n "$seed_ts" ] && printf '%s' "$seed_ts" > "$RUN_LOG_DIR/last-run/va.ts"

    cat > "$RUN_ROOT/bin/os-update" <<STUB
#!/usr/bin/env bash
# Only the --scrape pass is exercised here; an --import pass would mean the no-op path was not
# taken, which the assertions below would already have caught.
printf '%s\n' "$stub_output"
exit $stub_exit
STUB
    chmod +x "$RUN_ROOT/bin/os-update"

    LOG_DIR="$RUN_LOG_DIR" \
    OS_UPDATE_OVERRIDE="$RUN_ROOT/bin/os-update" \
    SUPPRESS_FAILURE_ALERT=1 \
    SKIP_PATCHES=1 \
    SCRAPED_DATA_DIR_OVERRIDE="$RUN_ROOT/data" \
    CACHE_DIR_OVERRIDE="$RUN_ROOT/cache" \
        bash "$SCRIPT_DIR/run-scrape.sh" va > "$RUN_ROOT/run.log" 2>&1
    RUN_RC=$?
}

marker() { cat "$RUN_LOG_DIR/last-run/$1" 2>/dev/null || echo "<absent>"; }

echo "== a genuine no-op must keep working exactly as before =="

BENIGN="12:00:02 INFO openstates: VA search returned a results page with no matching bills -- genuine empty result for this window
openstates.exceptions.ScrapeError: no objects returned from VaBillScraper scrape"

run_with_stub "$BENIGN" 1 "2026-01-01T00:00:00"; rc=$RUN_RC
check "benign: exits 0" "0" "$rc"
check "benign: records a measured zero" "ok:0:0:0:incremental" "$(marker va.imported)"
if [ "$(marker va.ts)" != "2026-01-01T00:00:00" ] && [ "$(marker va.ts)" != "<absent>" ]; then
    PASS=$((PASS + 1)); echo "  ok   benign: advances the watermark"
else
    FAIL=$((FAIL + 1)); echo "  FAIL benign: watermark not advanced (got $(marker va.ts))"
fi
rm -rf "$RUN_ROOT"

echo "== an unreachable site must not be recorded as a measurement =="

UNREACHABLE="12:00:01 INFO scrapelib: GET - 'https://example.gov/Search'
12:00:02 WARNING openstates: VA search response is neither a results page nor a usable bill page (no tableScrollWrapper and no h1#BillHeading) -- treating as no results, but this is probably a site change or an unrecognised block page
openstates.exceptions.ScrapeError: no objects returned from VaBillScraper scrape"

run_with_stub "$UNREACHABLE" 1 "2026-01-01T00:00:00"; rc=$RUN_RC
check "unreachable: exits non-zero" "yes" "$([ "$rc" != "0" ] && echo yes || echo "no (rc=$rc)")"
# THE point of the ticket. If this regresses, a blocked run silently skips a window forever.
check "unreachable: watermark NOT advanced" "2026-01-01T00:00:00" "$(marker va.ts)"
check "unreachable: no measurement recorded" "<absent>" "$(marker va.imported)"
check "unreachable: says why in the log" "yes" \
    "$(grep -q 'OPEN-152' "$RUN_LOG_DIR/scraper.log" && echo yes || echo no)"
rm -rf "$RUN_ROOT"

echo "== an unreachable site with no prior watermark must not create one =="

run_with_stub "$UNREACHABLE" 1 ""; rc=$RUN_RC
check "unreachable, first run: no watermark created" "<absent>" "$(marker va.ts)"
check "unreachable, first run: no measurement" "<absent>" "$(marker va.imported)"
rm -rf "$RUN_ROOT"

echo
if [ "$FAIL" -eq 0 ]; then
    echo "ALL PASS ($PASS assertions)"
    exit 0
fi
echo "$FAIL FAILED, $PASS passed"
exit 1
