#!/usr/bin/env bash
# test-scraper-memory.sh — OPEN-181's external per-source memory, both the helper's own logic and
# what run-scrape.sh does with it.
#
# The acceptance question is not "does it upload a file". It is:
#
#   * a run whose local markers have been DELETED still runs incrementally, because its memory
#     came from somewhere else. That is the whole ticket.
#   * a store that cannot be read makes the run REFUSE, not assume a first-ever run. Guessing
#     "absent" there converts an S3 blip into a ~3,900-request full walk of Michigan.
#   * §3's semantics survive: unreachable must not advance the stored memory, unparsed must.
#   * Michigan's 3,924-entry baseline round-trips, and it is found by name rather than by a
#     template -- production runs MI with no session argument, so the wrapper cannot build it.
#
# A stub stands in for the S3 wrapper; no network, no database, no production paths.
#
#     bash test-scraper-memory.sh

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

ROOT=$(mktemp -d /tmp/scraper-memory.XXXXXX)
trap 'rm -rf "$ROOT"' EXIT

# A stand-in for ddp-prod-s3-openstates-backups, backed by a directory. It reproduces the two
# behaviours the helper actually depends on, both verified against the real wrapper on
# 2026-08-27: `get` on a missing key exits non-zero with "An error occurred (404) ... Not Found"
# and writes no destination file, and `ls` on an empty prefix exits non-zero with no output.
# FAKE_S3_FAIL=1 simulates the store being unreachable, which is the case that must never be
# mistaken for "absent".
mkdir -p "$ROOT/bin" "$ROOT/bucket"
cat > "$ROOT/bin/fake-s3" <<'STUB'
#!/usr/bin/env bash
BUCKET="${FAKE_S3_ROOT:?}"
if [ "${FAKE_S3_FAIL:-0}" = "1" ]; then
    echo "Could not connect to the endpoint URL: \"https://s3.amazonaws.com/\"" >&2
    exit 1
fi
case "$1" in
    put)
        mkdir -p "$(dirname "$BUCKET/$3")"
        cp "$2" "$BUCKET/$3"
        ;;
    get)
        if [ -f "$BUCKET/$2" ]; then
            cp "$BUCKET/$2" "$3"
        else
            echo "download failed: An error occurred (404) when calling the HeadObject operation: Not Found" >&2
            exit 1
        fi
        ;;
    ls)
        found=0
        while IFS= read -r f; do
            [ -n "$f" ] || continue
            found=1
            printf '2026-08-27 12:00:00 %10d %s\n' "$(wc -c < "$f" | tr -d ' ')" "${f#$BUCKET/}"
        done <<< "$(find "$BUCKET/${2:-}" -type f 2>/dev/null | sort)"
        [ "$found" = "1" ] || exit 1
        ;;
    info)
        [ -f "$BUCKET/$2" ] || { echo "aws: [ERROR]: An error occurred (404) ... Not Found" >&2; exit 254; }
        ;;
    *) exit 2 ;;
esac
STUB
chmod +x "$ROOT/bin/fake-s3"
export FAKE_S3_ROOT="$ROOT/bucket"

# ------------------------------------------------------------------ the helper's own behaviour

echo "== the store is off unless it is switched on =="

( unset SCRAPER_MEMORY_BACKEND SCRAPER_MEMORY_PREFIX
  . "$SCRIPT_DIR/scraper-memory.sh"
  scraper_memory_enabled && exit 1
  scraper_memory_check_config >/dev/null || exit 1
  # Every operation must be a silent no-op, not an error, when the backend is local.
  scraper_memory_hydrate_markers va va /nonexistent || exit 1
  scraper_memory_persist_markers va va /nonexistent || exit 1
  exit 0 )
check "local backend: disabled, valid, and every operation a no-op" "0" "$?"

echo "== a namespace is required, because an object key has no checkout to follow =="

msg=$( SCRAPER_MEMORY_BACKEND=s3 SCRAPER_MEMORY_PREFIX="" \
       bash -c '. "$0/scraper-memory.sh"; scraper_memory_check_config' "$SCRIPT_DIR" )
check "s3 backend with no prefix: refuses" "yes" \
    "$(echo "$msg" | grep -q 'requires SCRAPER_MEMORY_PREFIX' && echo yes || echo no)"

msg=$( SCRAPER_MEMORY_BACKEND=s3 SCRAPER_MEMORY_PREFIX='../../etc' \
       bash -c '. "$0/scraper-memory.sh"; scraper_memory_check_config' "$SCRIPT_DIR" )
check "s3 backend with a nonsense prefix: refuses" "yes" \
    "$(echo "$msg" | grep -q 'do not belong in an object key' && echo yes || echo no)"

echo "== absent and unreadable are different answers, and that is the point =="

helper() {  # run a snippet with the helper sourced and the stub wired in
    SCRAPER_MEMORY_BACKEND=s3 SCRAPER_MEMORY_PREFIX=testns \
    SCRAPER_MEMORY_S3_CMD="$ROOT/bin/fake-s3" \
        bash -c ". \"$SCRIPT_DIR/scraper-memory.sh\"; $1" 2>/dev/null
}

printf 'stored-content' > "$ROOT/seed.txt"
helper 'scraper_memory_store '"$ROOT"'/seed.txt testns/va/va/va.ts'
check "store: the object lands" "stored-content" "$(cat "$ROOT/bucket/testns/va/va/va.ts" 2>/dev/null)"

helper 'scraper_memory_fetch testns/va/va/va.ts '"$ROOT"'/got.txt; echo $?' > "$ROOT/rc"
check "fetch present: returns 0"      "0" "$(cat "$ROOT/rc")"
check "fetch present: content arrives" "stored-content" "$(cat "$ROOT/got.txt" 2>/dev/null)"

helper 'scraper_memory_fetch testns/va/va/absent.ts '"$ROOT"'/nope.txt; echo $?' > "$ROOT/rc"
check "fetch absent: returns 1 (genuinely not there)" "1" "$(cat "$ROOT/rc")"
check "fetch absent: writes no file" "no" \
    "$([ -f "$ROOT/nope.txt" ] && echo yes || echo no)"

rc=$( FAKE_S3_FAIL=1 SCRAPER_MEMORY_BACKEND=s3 SCRAPER_MEMORY_PREFIX=testns \
      SCRAPER_MEMORY_S3_CMD="$ROOT/bin/fake-s3" \
      bash -c ". \"$SCRIPT_DIR/scraper-memory.sh\"; scraper_memory_fetch testns/va/va/va.ts $ROOT/x; echo \$?" 2>/dev/null )
# THE distinction this function exists for. A store that did not answer is not an empty store.
check "fetch during an outage: returns 2, NOT 1" "2" "$rc"

echo "== Michigan's baseline is found by name, not built from a template =="

check "mi declares a memory file"      "mi_last_actions_*.json" "$(helper 'scraper_memory_cache_glob mi')"
check "ut declares none"               ""                       "$(helper 'scraper_memory_cache_glob ut')"

# Production runs MI with NO session argument, so its scrape key is a bare `mi` and the session
# appears only inside the filename. A template would have produced `mi_last_actions_.json`.
mkdir -p "$ROOT/cache"
python3 -c "
import json
json.dump({'HB%04d' % i: 'referred to committee' for i in range(1, 3925)}, open('$ROOT/cache/mi_last_actions_2025-2026.json', 'w'))
"
BASELINE_MD5=$(md5 -q "$ROOT/cache/mi_last_actions_2025-2026.json")
BASELINE_ENTRIES=$(python3 -c "import json; print(len(json.load(open('$ROOT/cache/mi_last_actions_2025-2026.json'))))")
check "baseline fixture is full size" "3924" "$BASELINE_ENTRIES"

helper 'scraper_memory_persist_cache mi mi '"$ROOT"'/cache'
check "persist_cache: the baseline is stored under its own name" "yes" \
    "$([ -f "$ROOT/bucket/testns/mi/mi/mi_last_actions_2025-2026.json" ] && echo yes || echo no)"

# Something else living under the same prefix must not be pulled into $CACHE_DIR.
printf 'not memory' > "$ROOT/decoy.txt"
helper 'scraper_memory_store '"$ROOT"'/decoy.txt testns/mi/mi/unrelated-object.txt'
rm -rf "$ROOT/cache2"; mkdir -p "$ROOT/cache2"
helper 'scraper_memory_hydrate_cache mi mi '"$ROOT"'/cache2'
check "hydrate_cache: round-trips at full size, byte for byte" "$BASELINE_MD5" \
    "$(md5 -q "$ROOT/cache2/mi_last_actions_2025-2026.json" 2>/dev/null)"
check "hydrate_cache: ignores objects that are not this jurisdiction's memory" "no" \
    "$([ -f "$ROOT/cache2/unrelated-object.txt" ] && echo yes || echo no)"

echo "== hydration leaves a local file alone when the store has nothing =="

mkdir -p "$ROOT/lr"
printf '2026-01-01T00:00:00' > "$ROOT/lr/az.ts"
helper 'scraper_memory_hydrate_markers az az '"$ROOT"'/lr'
# This is what makes the cutover seamless: the first run under the new backend finds an empty
# store, keeps using the watermark it has always used, and persists it at the end.
check "hydrate: an empty store does not erase local memory" "2026-01-01T00:00:00" "$(cat "$ROOT/lr/az.ts")"

# ------------------------------------------------------------------ through the real script

echo "== end to end: a run with NO local memory still knows where it left off =="

RUN_ROOT=$(mktemp -d /tmp/scraper-memory-e2e.XXXXXX)
RUN_LOG_DIR="$RUN_ROOT/logs"
mkdir -p "$RUN_LOG_DIR/last-run" "$RUN_ROOT/bin" "$RUN_ROOT/data/va" "$RUN_ROOT/cache"
cat > "$RUN_ROOT/bin/os-update" <<STUB
#!/usr/bin/env bash
for a in "\$@"; do
    if [ "\$a" = "--import" ]; then
        echo "import:"
        echo "  bill: 1 new 0 updated 0 noop"
        exit 0
    fi
done
printf '{}' > "$RUN_ROOT/data/va/bill_stub1.json"
echo "scraped fine"
STUB
chmod +x "$RUN_ROOT/bin/os-update"

e2e() {  # $1 extra env assignments, evaluated; echoes exit code into RUN_RC
    env LOG_DIR="$RUN_LOG_DIR" OS_UPDATE_OVERRIDE="$RUN_ROOT/bin/os-update" \
        SUPPRESS_FAILURE_ALERT=1 SKIP_PATCHES=1 \
        SCRAPED_DATA_DIR_OVERRIDE="$RUN_ROOT/data" CACHE_DIR_OVERRIDE="$RUN_ROOT/cache" \
        SCRAPER_MEMORY_BACKEND=s3 SCRAPER_MEMORY_PREFIX=e2ens \
        SCRAPER_MEMORY_S3_CMD="$ROOT/bin/fake-s3" FAKE_S3_ROOT="$ROOT/bucket" \
        $1 \
        bash "$SCRIPT_DIR/run-scrape.sh" va > "$RUN_ROOT/stdout.log" 2> "$RUN_ROOT/stderr.log"
    RUN_RC=$?
}
status() { tail -1 "$RUN_ROOT/stdout.log" | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])' 2>/dev/null || echo "<none>"; }
mode()   { tail -1 "$RUN_ROOT/stdout.log" | python3 -c 'import json,sys; print(json.load(sys.stdin)["mode"])'   2>/dev/null || echo "<none>"; }
stored() { cat "$ROOT/bucket/e2ens/va/va/va.ts" 2>/dev/null || echo "<absent>"; }

e2e ""
check "first run: full, because neither disk nor store remembers anything" "full" "$(mode)"
check "first run: succeeds" "ok" "$(status)"
check "first run: memory is now in the store" "yes" \
    "$([ "$(stored)" != "<absent>" ] && echo yes || echo no)"
FIRST_WATERMARK="$(stored)"

# THE acceptance criterion. Everything this machine knew is deleted; the only surviving copy of
# the watermark is the object in the store.
rm -f "$RUN_LOG_DIR/last-run"/va.*
e2e ""
check "local memory deleted: the run is STILL incremental" "incremental" "$(mode)"
check "local memory deleted: it read the cutoff from the store" "yes" \
    "$(grep -q "cutoff=" "$RUN_LOG_DIR/scraper.log" && echo yes || echo no)"
check "second run: the store advanced" "yes" \
    "$([ "$(stored)" != "$FIRST_WATERMARK" ] && echo yes || echo no)"

echo "== a store that will not answer must stop the run, not start a full collection =="

ADVANCED_WATERMARK="$(stored)"
rm -f "$RUN_LOG_DIR/last-run"/va.*
e2e "FAKE_S3_FAIL=1"
check "store unreachable: exits non-zero" "yes" "$([ "$RUN_RC" != "0" ] && echo yes || echo no)"
check "store unreachable: reports failed" "failed" "$(status)"
# The failure this guards against: assuming "no memory" and walking the whole source.
check "store unreachable: did NOT fall back to a full collection" "yes" \
    "$(grep -q 'refusing to run rather than assuming a first-ever run' "$RUN_LOG_DIR/scraper.log" && echo yes || echo no)"
check "store unreachable: stored memory untouched" "$ADVANCED_WATERMARK" "$(stored)"
check "store unreachable: no local markers written" "no" \
    "$([ -f "$RUN_LOG_DIR/last-run/va.ts" ] && echo yes || echo no)"

echo "== §3's memory semantics survive the move to an external store =="

# unreachable: nothing was measured, so the stored watermark must not move.
BEFORE="$(stored)"
cat > "$RUN_ROOT/bin/os-update" <<'STUB'
#!/usr/bin/env bash
echo "WARNING openstates: VA search response is neither a results page nor a usable bill page -- unrecognised block page"
echo "openstates.exceptions.ScrapeError: no objects returned from VaBillScraper scrape"
exit 1
STUB
chmod +x "$RUN_ROOT/bin/os-update"
e2e ""
check "unreachable: status"                     "unreachable" "$(status)"
check "unreachable: stored watermark NOT advanced" "$BEFORE"  "$(stored)"

# unparsed: the collection and load both worked, only the counting failed -- §3 says it advances.
cat > "$RUN_ROOT/bin/os-update" <<STUB
#!/usr/bin/env bash
for a in "\$@"; do
    if [ "\$a" = "--import" ]; then echo "import: (nothing countable)"; exit 0; fi
done
echo "scraped fine"
STUB
chmod +x "$RUN_ROOT/bin/os-update"
e2e ""
check "unparsed: status"                        "unparsed" "$(status)"
check "unparsed: stored watermark DID advance"  "yes" \
    "$([ "$(stored)" != "$BEFORE" ] && echo yes || echo no)"

rm -rf "$RUN_ROOT"

echo
if [ "$FAIL" -eq 0 ]; then
    echo "ALL PASS ($PASS assertions)"
    exit 0
fi
echo "$FAIL FAILED, $PASS passed"
exit 1
