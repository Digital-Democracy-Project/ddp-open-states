#!/usr/bin/env bash
# test-completion-record.sh — end-to-end tests for OPEN-182's JSON completion record, through
# the real run-scrape.sh.
#
# What this has to prove is not "the JSON parses". It is the two properties contract §2 rests on:
#
#   * EVERY handled outcome emits exactly one record, on the last line of stdout. A caller is
#     told to read a missing record as a dead runner, so an exit path that emits nothing would
#     report a working run as a crash.
#   * The record REPORTS the status the run decided; it never recomputes one. `unparsed` is a
#     success that advances the watermark, `unreachable` is a failure that must not -- if the
#     JSON and the marker file ever disagree about which happened, the record is worse than
#     useless because it is the one a machine reads.
#
# So each case asserts the record and the `.imported` marker together, and the last case runs a
# path that exits before run-scrape.sh has finished setting itself up at all.
#
# Same shape as test-no-op-side-effects.sh: a stub os-update, no network, no database, no
# production paths. SKIP_PATCHES=1 is not optional -- without it run-scrape.sh git-pulls the
# live nested checkouts before scraping a real legislature site.
#
#     bash test-completion-record.sh

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

# Builds a throwaway LOG_DIR plus a stub os-update, runs run-scrape.sh against them, and leaves
# stdout and stderr in SEPARATE files. Separate on purpose: §2 specifies the last line of
# *stdout*, and merging the two the way the sibling tests do would let a stray stderr line land
# after the record and still pass.
#
#   $1 scrape output  $2 scrape exit  $3 import output  $4 bill files to write  $5 seed ts
#   $6 session argument (optional)
run_with_stub() {
    local scrape_output="$1" scrape_exit="$2" import_output="$3" bill_files="$4" seed_ts="${5:-}"
    RUN_ROOT=$(mktemp -d /tmp/completion-record.XXXXXX)
    RUN_LOG_DIR="$RUN_ROOT/logs"
    mkdir -p "$RUN_LOG_DIR/last-run" "$RUN_ROOT/bin" "$RUN_ROOT/data/va"
    [ -n "$seed_ts" ] && printf '%s' "$seed_ts" > "$RUN_LOG_DIR/last-run/va.ts"

    # Distinguishes the two passes the way run-scrape.sh actually invokes them: the scrape pass
    # carries --scrape, the import pass carries --import.
    cat > "$RUN_ROOT/bin/os-update" <<STUB
#!/usr/bin/env bash
for a in "\$@"; do
    if [ "\$a" = "--import" ]; then
        printf '%s\n' "$import_output"
        exit 0
    fi
done
n=$bill_files
i=0
while [ "\$i" -lt "\$n" ]; do
    i=\$((i + 1))
    printf '{}' > "$RUN_ROOT/data/va/bill_stub\$i.json"
done
printf '%s\n' "$scrape_output"
exit $scrape_exit
STUB
    chmod +x "$RUN_ROOT/bin/os-update"

    LOG_DIR="$RUN_LOG_DIR" \
    OS_UPDATE_OVERRIDE="$RUN_ROOT/bin/os-update" \
    SUPPRESS_FAILURE_ALERT=1 \
    SKIP_PATCHES=1 \
    SCRAPED_DATA_DIR_OVERRIDE="$RUN_ROOT/data" \
    CACHE_DIR_OVERRIDE="$RUN_ROOT/cache" \
        bash "$SCRIPT_DIR/run-scrape.sh" va ${6:-} \
            > "$RUN_ROOT/stdout.log" 2> "$RUN_ROOT/stderr.log"
    RUN_RC=$?
}

# The record, by definition: the last line of stdout.
record() { tail -1 "$RUN_ROOT/stdout.log"; }

# Reads one field out of it. Prints <missing> for an absent key and <not-json> if the last line
# is not a JSON object at all -- both are failures worth telling apart in the output.
field() {
    tail -1 "$RUN_ROOT/stdout.log" | python3 -c '
import json, sys
raw = sys.stdin.read().strip()
try:
    rec = json.loads(raw)
    if not isinstance(rec, dict):
        raise ValueError
except Exception:
    print("<not-json>"); sys.exit(0)
print(rec.get(sys.argv[1], "<missing>"))
' "$1"
}

records_on_stdout() { grep -c '^{".*}$' "$RUN_ROOT/stdout.log" | tr -d ' '; }
marker() { cat "$RUN_LOG_DIR/last-run/$1" 2>/dev/null || echo "<absent>"; }

OK_IMPORT="import:
  bill: 2 new 1 updated 4 noop
  jurisdiction: 0 new 0 updated 1 noop"

UNREACHABLE="12:00:02 WARNING openstates: VA search response is neither a results page nor a usable bill page (no tableScrollWrapper and no h1#BillHeading) -- treating as no results, but this is probably a site change or an unrecognised block page
openstates.exceptions.ScrapeError: no objects returned from VaBillScraper scrape"

BENIGN="12:00:02 INFO openstates: VA search returned a results page with no matching bills -- genuine empty result for this window
openstates.exceptions.ScrapeError: no objects returned from VaBillScraper scrape"

echo "== a measured run reports ok, with the counts the import actually printed =="

run_with_stub "scraped fine" 0 "$OK_IMPORT" 3 ""
check "ok: exits 0"                     "0"  "$RUN_RC"
check "ok: status"                      "ok" "$(field status)"
check "ok: source"                      "va" "$(field source)"
check "ok: mode is full on a first run" "full" "$(field mode)"
check "ok: new"                         "2"  "$(field new)"
check "ok: updated"                     "1"  "$(field updated)"
check "ok: noop"                        "4"  "$(field noop)"
check "ok: found counts the scraped files" "3" "$(field found)"
check "ok: carries a run_id"             "yes" \
    "$([ -n "$(field run_id)" ] && [ "$(field run_id)" != "<missing>" ] && echo yes || echo no)"
check "ok: reports a duration"           "yes" \
    "$([ "$(field duration_s)" != "<missing>" ] && echo yes || echo no)"
# The record and the marker file are two statements about one run. They must agree.
check "ok: agrees with the .imported marker" "ok:2:1:4:full" "$(marker va.imported)"
check "ok: exactly one record on stdout"  "1" "$(records_on_stdout)"
# No session was passed, so the field must be absent rather than empty -- an empty string would
# read as a real session named "".
check "ok: no session field when none given" "<missing>" "$(field session)"
rm -rf "$RUN_ROOT"

echo "== the session is carried when there is one =="

run_with_stub "scraped fine" 0 "$OK_IMPORT" 1 "" "session=2026"
check "session: reported"  "session=2026" "$(field session)"
# The run id has to distinguish two runs of the same jurisdiction -- `usa lower` and `usa upper`
# share a $STATE, and so do FL's eight sessions -- so it is keyed on the scrape key, not $STATE.
check "session: run_id is keyed on it too" "yes" \
    "$(field run_id | grep -q '^va_session_2026-' && echo yes || echo no)"
rm -rf "$RUN_ROOT"

echo "== an import whose counts cannot be read is unparsed, not failed =="

run_with_stub "scraped fine" 0 "import: (nothing countable here)" 2 ""
check "unparsed: exits 0"        "0"          "$RUN_RC"
check "unparsed: status"         "unparsed"   "$(field status)"
check "unparsed: agrees with the marker" "unparsed::::full" "$(marker va.imported)"
# §2 requires new/updated/noop only for ok. Emitting zeros here would assert a measurement that
# was never made -- which is the exact confusion the status enum exists to remove.
check "unparsed: no fabricated new count" "<missing>" "$(field new)"
check "unparsed: still reports found"     "2"         "$(field found)"
rm -rf "$RUN_ROOT"

echo "== an unreachable site reports unreachable, in both modes =="

run_with_stub "$UNREACHABLE" 1 "" 0 "2026-01-01T00:00:00"
check "unreachable (incremental): exits non-zero" "yes" \
    "$([ "$RUN_RC" != "0" ] && echo yes || echo "no (rc=$RUN_RC)")"
check "unreachable (incremental): status" "unreachable" "$(field status)"
check "unreachable (incremental): mode"   "incremental" "$(field mode)"
# The property the record must not break: no measurement was made, so none is recorded anywhere.
check "unreachable (incremental): watermark not advanced" "2026-01-01T00:00:00" "$(marker va.ts)"
check "unreachable (incremental): no marker written"      "<absent>" "$(marker va.imported)"
rm -rf "$RUN_ROOT"

# A FULL run never reaches the no-op branch that consults the matcher, so before this change the
# same blocked site produced a bare failure. The record asks the matcher directly, which is why
# this case reports unreachable too -- and it is the case that proves the record is reading the
# run's own matcher rather than the branch it happened to be in.
run_with_stub "$UNREACHABLE" 1 "" 0 ""
check "unreachable (full): status" "unreachable" "$(field status)"
check "unreachable (full): mode"   "full"        "$(field mode)"
rm -rf "$RUN_ROOT"

echo "== an ordinary scrape failure is failed, not unreachable =="

run_with_stub "ValueError: something broke while parsing bill HB 1" 1 "" 0 ""
check "failed: exits non-zero" "yes" "$([ "$RUN_RC" != "0" ] && echo yes || echo "no (rc=$RUN_RC)")"
check "failed: status"         "failed"   "$(field status)"
check "failed: no marker written" "<absent>" "$(marker va.imported)"
check "failed: exactly one record" "1" "$(records_on_stdout)"
rm -rf "$RUN_ROOT"

echo "== a genuine no-op is a measured zero =="

run_with_stub "$BENIGN" 1 "" 0 "2026-01-01T00:00:00"
check "no-op: exits 0"   "0"  "$RUN_RC"
check "no-op: status"    "ok" "$(field status)"
check "no-op: new is a real zero"  "0" "$(field new)"
check "no-op: noop is a real zero" "0" "$(field noop)"
check "no-op: agrees with the marker" "ok:0:0:0:incremental" "$(marker va.imported)"
rm -rf "$RUN_ROOT"

echo "== a failing import is failed, never unparsed =="

# The stub exits 0 for --import above, so this one overrides the whole stub to fail that pass.
RUN_ROOT=$(mktemp -d /tmp/completion-record.XXXXXX)
RUN_LOG_DIR="$RUN_ROOT/logs"
mkdir -p "$RUN_LOG_DIR/last-run" "$RUN_ROOT/bin" "$RUN_ROOT/data/va"
cat > "$RUN_ROOT/bin/os-update" <<STUB
#!/usr/bin/env bash
for a in "\$@"; do
    if [ "\$a" = "--import" ]; then
        echo "psycopg2.OperationalError: could not connect to server"
        exit 1
    fi
done
printf '{}' > "$RUN_ROOT/data/va/bill_stub1.json"
echo "scraped fine"
STUB
chmod +x "$RUN_ROOT/bin/os-update"
LOG_DIR="$RUN_LOG_DIR" OS_UPDATE_OVERRIDE="$RUN_ROOT/bin/os-update" SUPPRESS_FAILURE_ALERT=1 \
SKIP_PATCHES=1 SCRAPED_DATA_DIR_OVERRIDE="$RUN_ROOT/data" CACHE_DIR_OVERRIDE="$RUN_ROOT/cache" \
    bash "$SCRIPT_DIR/run-scrape.sh" va > "$RUN_ROOT/stdout.log" 2> "$RUN_ROOT/stderr.log"
RUN_RC=$?
check "import failure: exits non-zero" "yes" "$([ "$RUN_RC" != "0" ] && echo yes || echo no)"
check "import failure: status" "failed" "$(field status)"
check "import failure: no marker written" "<absent>" "$(marker va.imported)"
rm -rf "$RUN_ROOT"

echo "== a refusal that fires before the script is fully set up still emits a record =="

# This is the structural case. run-scrape.sh registers a minimal EXIT trap early and REPLACES it
# later with the fuller one that also cleans up locks and markers; if the second registration
# ever stops calling emit_completion_record, or the first one is dropped, every exit before the
# lock section goes silent. OPEN-159's non-production-checkout refusal is the one such path that
# can be exercised safely, because it exits before anything is scraped or imported.
#
# It only fires from a checkout that is not production, and it is skipped by design when
# OS_UPDATE_OVERRIDE is set -- so this case runs the script with NO stub. Guarded on the checkout
# for exactly that reason: from the production checkout the refusal does not fire and the run
# would proceed to scrape a real legislature site.
PRODUCTION_CHECKOUT="/Users/agentsmith/Developer/repos/ddp-open-states"
if [ "$(cd "$SCRIPT_DIR" && pwd -P)" = "$(cd "$PRODUCTION_CHECKOUT" 2>/dev/null && pwd -P || echo "$PRODUCTION_CHECKOUT")" ]; then
    echo "  skip production checkout: the refusal under test cannot fire here"
else
    RUN_ROOT=$(mktemp -d /tmp/completion-record.XXXXXX)
    RUN_LOG_DIR="$RUN_ROOT/logs"
    mkdir -p "$RUN_LOG_DIR/last-run"
    LOG_DIR="$RUN_LOG_DIR" SKIP_PATCHES=1 \
        bash "$SCRIPT_DIR/run-scrape.sh" va > "$RUN_ROOT/stdout.log" 2> "$RUN_ROOT/stderr.log"
    RUN_RC=$?
    check "early refusal: exits 90"  "90"       "$RUN_RC"
    check "early refusal: status"    "failed"   "$(field status)"
    check "early refusal: source"    "va"       "$(field source)"
    check "early refusal: still reports a mode" "full" "$(field mode)"
    check "early refusal: exactly one record"   "1"    "$(records_on_stdout)"
    rm -rf "$RUN_ROOT"
fi

echo
if [ "$FAIL" -eq 0 ]; then
    echo "ALL PASS ($PASS assertions)"
    exit 0
fi
echo "$FAIL FAILED, $PASS passed"
exit 1
