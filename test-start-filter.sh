#!/usr/bin/env bash
# test-start-filter.sh — OPEN-501 follow-up: run-scrape.sh reads `scrape.start_filter` from
# jurisdictions.yaml, the same way cloud_collector.py does (it calls that file's
# scraper_takes_start()), so a hand run on the Mac with a watermark present never hands `start=` to
# a bills scraper that has no start parameter (Alabama's crash, 2026-11-16).
#
# Same harness as test-no-op-side-effects.sh: a stub os-update records the arguments it was given;
# LOG_DIR, OS_UPDATE and the data/cache dirs are redirected; SUPPRESS_FAILURE_ALERT and
# SKIP_PATCHES keep it away from Slack, CAMS and the live nested checkouts. No network, no database.
#
#     bash test-start-filter.sh

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PASS=0
FAIL=0
WATERMARK="2026-01-01T00:00:00"

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

# run_state <state> [manifest] -- seeds a watermark for <state>, runs run-scrape.sh with a stub
# os-update that appends its arguments to $RUN_ROOT/args, and leaves the run's files in $RUN_ROOT.
run_state() {
    local state="$1" manifest="${2:-}"
    RUN_ROOT=$(mktemp -d /tmp/start-filter-test.XXXXXX)
    mkdir -p "$RUN_ROOT/logs/last-run" "$RUN_ROOT/bin"
    printf '%s' "$WATERMARK" > "$RUN_ROOT/logs/last-run/${state}.ts"

    cat > "$RUN_ROOT/bin/os-update" <<STUB
#!/usr/bin/env bash
echo "\$*" >> "$RUN_ROOT/args"
echo "openstates.exceptions.ScrapeError: no objects returned from XxBillScraper scrape"
exit 1
STUB
    chmod +x "$RUN_ROOT/bin/os-update"

    ( [ -n "$manifest" ] && export JURISDICTIONS_YAML="$manifest"
      LOG_DIR="$RUN_ROOT/logs" \
      OS_UPDATE_OVERRIDE="$RUN_ROOT/bin/os-update" \
      SUPPRESS_FAILURE_ALERT=1 \
      SKIP_PATCHES=1 \
      SCRAPED_DATA_DIR_OVERRIDE="$RUN_ROOT/data" \
      CACHE_DIR_OVERRIDE="$RUN_ROOT/cache" \
          bash "$SCRIPT_DIR/run-scrape.sh" "$state" > "$RUN_ROOT/run.log" 2>&1 )
    RUN_RC=$?
}

scrape_args() { grep -- "--scrape" "$RUN_ROOT/args" 2>/dev/null | head -1; }
has_start() { scrape_args | grep -q "start=" && echo yes || echo no; }
started_mode() {  # the mode the "Starting scrape" line reports
    grep -o "Starting scrape: .*" "$RUN_ROOT/logs/scraper.log" | head -1 \
        | grep -o "(incremental\|(full" | tr -d '('
}

echo "== start_filter: false (al, nc) runs full even with a watermark =="
for st in al nc; do
    run_state "$st"
    check "$st: os-update was called" "yes" "$([ -s "$RUN_ROOT/args" ] && echo yes || echo no)"
    check "$st: no start= handed to the scraper" "no" "$(has_start)"
    check "$st: run starts in full mode" "full" "$(started_mode)"
    check "$st: the log says why (OPEN-501)" "yes" \
        "$(grep -q "start_filter is false" "$RUN_ROOT/logs/scraper.log" && echo yes || echo no)"
    rm -rf "$RUN_ROOT"
done

echo "== start_filter: true (va) is unchanged: incremental with start= =="
run_state va
check "va: start= handed to the scraper" "yes" "$(has_start)"
check "va: start= is the watermark less one hour" "yes" \
    "$(scrape_args | grep -q "start=2025-12-31T23:00:00" && echo yes || echo no)"
check "va: run starts in incremental mode" "incremental" "$(started_mode)"
rm -rf "$RUN_ROOT"

# The answer comes from the manifest, not from a list in the script: flip va to false in a copy.
MANIFESTS=$(mktemp -d /tmp/start-filter-manifests.XXXXXX)
trap 'rm -rf "$MANIFESTS"' EXIT
# copy_with_va_start_filter <value> <dest>: the real manifest with only va's start_filter changed
copy_with_va_start_filter() {
    python3 - "$SCRIPT_DIR/jurisdictions.yaml" "$2" "$1" <<'PY'
import sys
src, dst, value = sys.argv[1], sys.argv[2], sys.argv[3]
text = open(src).read()
start = text.index("\nva:\n")
end = text.index("start_filter: true", start)
open(dst, "w").write(text[:end] + "start_filter: " + value + text[end + len("start_filter: true"):])
PY
}
copy_with_va_start_filter false "$MANIFESTS/va-false.yaml"

echo "== the manifest decides: va flipped to false in a copy of the manifest =="
run_state va "$MANIFESTS/va-false.yaml"
check "va (manifest copy says false): no start=" "no" "$(has_start)"
check "va (manifest copy says false): full mode" "full" "$(started_mode)"
rm -rf "$RUN_ROOT"

echo "== a manifest that cannot be read stops the run before scraping =="
# Only va's start_filter is broken; every other field (allow_duplicates included) stays readable, so
# nothing later in run-scrape.sh stops the run -- only the OPEN-501 refusal can.
copy_with_va_start_filter '"maybe"' "$MANIFESTS/broken.yaml"
run_state va "$MANIFESTS/broken.yaml"
check "broken manifest: exits non-zero" "yes" "$([ "$RUN_RC" != "0" ] && echo yes || echo "no (rc=$RUN_RC)")"
check "broken manifest: os-update never called" "no" "$([ -s "$RUN_ROOT/args" ] && echo yes || echo no)"
check "broken manifest: says why in the log" "yes" \
    "$(grep -q "cannot read scrape.start_filter" "$RUN_ROOT/logs/scraper.log" && echo yes || echo no)"
check "broken manifest: watermark untouched" "$WATERMARK" "$(cat "$RUN_ROOT/logs/last-run/va.ts")"
rm -rf "$RUN_ROOT"

echo
if [ "$FAIL" -eq 0 ]; then
    echo "ALL PASS ($PASS assertions)"
    exit 0
fi
echo "$FAIL FAILED, $PASS passed"
exit 1
