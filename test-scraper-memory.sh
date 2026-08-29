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
        # Targeted failure, so a PARTIAL publication can be exercised.
        case "$3" in
            *${FAKE_S3_FAIL_PUT_MATCH:-__never__}*)
                echo "An error occurred (SlowDown) when calling the PutObject operation" >&2
                exit 1 ;;
        esac
        mkdir -p "$(dirname "$BUCKET/$3")"
        cp "$2" "$BUCKET/$3"
        ;;
    get)
        if [ -f "$BUCKET/$2" ]; then
            cp "$BUCKET/$2" "$3"
        else
            # A failing download that WRITES TO ITS DESTINATION FIRST. The real wrapper does not
            # do this, but scraper_memory_fetch must not depend on that -- it is a property of a
            # script in ~/bin that this repo does not own.
            [ "${FAKE_S3_GET_CORRUPTS:-0}" = "1" ] && printf 'HALF A FIL' > "$3"
            if [ "${FAKE_S3_GET_VAGUE_404:-0}" = "1" ]; then
                # No "(404)", just the words. A proxy or captive portal can produce this, and
                # reading it as "no memory" is the expensive direction to be wrong in.
                echo "<html><title>404 Not Found</title></html>" >&2
            else
                echo "download failed: An error occurred (404) when calling the HeadObject operation: Not Found" >&2
            fi
            exit 1
        fi
        ;;
    ls)
        # 137 is what a SIGKILLed wrapper looks like: non-zero, and silent.
        [ -n "${FAKE_S3_LS_EXIT:-}" ] && exit "$FAKE_S3_LS_EXIT"
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

# A stand-in for the new ddp-prod-s3-scraper-memory wrapper's three lock-specific subcommands
# (OPEN-187; see OPEN-187-scraper-lock-wrapper-setup.md for the real contract). Etags are a
# simple incrementing counter, sidecar'd next to each object -- enough to exercise the
# conditional-write semantics scraper_memory_acquire_lock/release_lock actually depend on,
# without needing S3. Created here, ahead of the e2e harness below, since run-scrape.sh's
# scraper_memory_check_config now requires this command whenever SCRAPER_MEMORY_BACKEND=s3
# (OPEN-187: the lock is mandatory alongside externalised memory, not a separate opt-in).
mkdir -p "$ROOT/lockbucket"
cat > "$ROOT/bin/fake-lock" <<'STUB'
#!/usr/bin/env bash
BUCKET="$FAKE_LOCK_ROOT"
key_path() { echo "$BUCKET/$1"; }
etag_path() { echo "$BUCKET/$1.etag"; }
case "$1" in
    lock-acquire)
        f=$(key_path "$2")
        if [ -f "$f" ]; then
            echo "An error occurred (PreconditionFailed) when calling the PutObject operation" >&2
            exit 1
        fi
        mkdir -p "$(dirname "$f")"
        cp "$3" "$f"
        n=$(( $(cat "$(etag_path "$2")" 2>/dev/null || echo 0) + 1 ))
        echo "$n" > "$(etag_path "$2")"
        echo "\"etag-$n\""
        ;;
    lock-read)
        f=$(key_path "$2")
        if [ ! -f "$f" ]; then
            echo "An error occurred (404) when calling the HeadObject operation: Not Found" >&2
            exit 1
        fi
        printf '"etag-%s"\t%s\n' "$(cat "$(etag_path "$2")")" "$(cat "$f")"
        ;;
    lock-reclaim)
        f=$(key_path "$2"); e=$(etag_path "$2")
        current="\"etag-$(cat "$e" 2>/dev/null || echo 0)\""
        if [ ! -f "$f" ] || [ "$current" != "$4" ]; then
            echo "An error occurred (PreconditionFailed) when calling the PutObject operation" >&2
            exit 1
        fi
        cp "$3" "$f"
        n=$(( $(cat "$e") + 1 ))
        echo "$n" > "$e"
        echo "\"etag-$n\""
        ;;
    *) exit 2 ;;
esac
STUB
chmod +x "$ROOT/bin/fake-lock"
export FAKE_LOCK_ROOT="$ROOT/lockbucket"

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

helper 'scraper_memory_persist_cache mi '"$ROOT"'/cache'
check "persist_cache: the baseline is stored under its own name" "yes" \
    "$([ -f "$ROOT/bucket/testns/mi/_cache/mi_last_actions_2025-2026.json" ] && echo yes || echo no)"

# Something else living under the same prefix must not be pulled into $CACHE_DIR.
printf 'not memory' > "$ROOT/decoy.txt"
helper 'scraper_memory_store '"$ROOT"'/decoy.txt testns/mi/_cache/unrelated-object.txt'
rm -rf "$ROOT/cache2"; mkdir -p "$ROOT/cache2"
helper 'scraper_memory_hydrate_cache mi '"$ROOT"'/cache2'
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

echo "== a failed download must not damage the copy already on disk =="

mkdir -p "$ROOT/keep"
printf 'GOOD-EXISTING-MEMORY' > "$ROOT/keep/va.ts"
rc=$( FAKE_S3_GET_CORRUPTS=1 SCRAPER_MEMORY_BACKEND=s3 SCRAPER_MEMORY_PREFIX=testns \
      SCRAPER_MEMORY_S3_CMD="$ROOT/bin/fake-s3" \
      bash -c ". \"$SCRIPT_DIR/scraper-memory.sh\"; scraper_memory_fetch testns/va/va/gone.ts $ROOT/keep/va.ts; echo \$?" 2>/dev/null )
check "failed get: still reports absent" "1" "$rc"
# The store wrote to the destination and then failed. The local copy must be untouched, because
# the fetch lands in a temporary file and is renamed only on success.
check "failed get: the existing local copy is intact" "GOOD-EXISTING-MEMORY" "$(cat "$ROOT/keep/va.ts")"
check "failed get: no temporary file left behind" "0" \
    "$(find "$ROOT/keep" -name 'va.ts.fetch.*' | wc -l | tr -d ' ')"

echo "== absence is recognised narrowly, and silence is never absence =="

rc=$( FAKE_S3_GET_VAGUE_404=1 SCRAPER_MEMORY_BACKEND=s3 SCRAPER_MEMORY_PREFIX=testns \
      SCRAPER_MEMORY_S3_CMD="$ROOT/bin/fake-s3" \
      bash -c ". \"$SCRIPT_DIR/scraper-memory.sh\"; scraper_memory_fetch testns/va/va/gone.ts $ROOT/x2; echo \$?" 2>/dev/null )
# A page that merely says "404 Not Found" in prose is not the store telling us the key is absent.
check "a vague 'Not Found' is unreadable (2), not absent (1)" "2" "$rc"

rc=$( FAKE_S3_LS_EXIT=137 SCRAPER_MEMORY_BACKEND=s3 SCRAPER_MEMORY_PREFIX=testns \
      SCRAPER_MEMORY_S3_CMD="$ROOT/bin/fake-s3" \
      bash -c ". \"$SCRIPT_DIR/scraper-memory.sh\"; scraper_memory_list testns/mi/_cache/ >/dev/null; echo \$?" 2>/dev/null )
# A killed wrapper is also non-zero and silent. Only the verified empty-prefix shape (exit 1,
# no output) may be read as "nothing there".
check "a killed listing (137, silent) is unreadable, not empty" "2" "$rc"

rc=$( FAKE_S3_LS_EXIT=1 SCRAPER_MEMORY_BACKEND=s3 SCRAPER_MEMORY_PREFIX=testns \
      SCRAPER_MEMORY_S3_CMD="$ROOT/bin/fake-s3" \
      bash -c ". \"$SCRIPT_DIR/scraper-memory.sh\"; scraper_memory_list testns/mi/_cache/ >/dev/null; echo \$?" 2>/dev/null )
check "the verified empty-prefix shape (1, silent) is still empty" "0" "$rc"

echo "== a partial publication must never leave the watermark ahead =="

# The wrapper has no transaction, so several objects cannot be published together. What IS
# arranged is the order: the reporting markers first, the authorising watermark last, stopping at
# the first failure. So a partial publication leaves the cutoff where it was and the next run
# re-collects -- wasteful, never skipped bills.
rm -rf "$ROOT/bucket/ordering"; mkdir -p "$ROOT/lr2" "$ROOT/bucket/ordering/va/va"
# A PRE-EXISTING stored watermark, so this asserts the real production state -- the previous
# run's cutoff surviving a failed publication -- rather than merely the absence of a new object
# on an empty prefix.
printf 'PREVIOUS-RUN-WATERMARK' > "$ROOT/bucket/ordering/va/va/va.ts"
printf 'OLD-WATERMARK'   > "$ROOT/lr2/va.ts"
printf '5:full'          > "$ROOT/lr2/va.count"
printf 'ok:5:0:0:full'   > "$ROOT/lr2/va.imported"
ordering() {
    env FAKE_S3_FAIL_PUT_MATCH="$1" SCRAPER_MEMORY_BACKEND=s3 SCRAPER_MEMORY_PREFIX=ordering \
        SCRAPER_MEMORY_S3_CMD="$ROOT/bin/fake-s3" FAKE_S3_ROOT="$ROOT/bucket" \
        bash -c ". \"$SCRIPT_DIR/scraper-memory.sh\"; $2; echo \$?" 2>/dev/null
}
stored_ordering() { cat "$ROOT/bucket/ordering/va/va/va.ts" 2>/dev/null || echo "<absent>"; }

check "persist stops at the first failure" "1" "$(ordering '.count' 'scraper_memory_persist_markers va va '"$ROOT"'/lr2')"
check "a failure on .count leaves the PREVIOUS cutoff in place" "PREVIOUS-RUN-WATERMARK" "$(stored_ordering)"

rm -rf "$ROOT/bucket/ordering"; mkdir -p "$ROOT/bucket/ordering/va/va"
printf 'PREVIOUS-RUN-WATERMARK' > "$ROOT/bucket/ordering/va/va/va.ts"
check "a failure on .ts itself also fails the publication" "1" "$(ordering '.ts' 'scraper_memory_persist_markers va va '"$ROOT"'/lr2')"
check "  ... while the reporting markers did land" "yes" "$([ -f "$ROOT/bucket/ordering/va/va/va.count" ] && echo yes || echo no)"
check "  ... and the cutoff is still the previous run's" "PREVIOUS-RUN-WATERMARK" "$(stored_ordering)"

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
        SCRAPER_LOCK_S3_CMD="$ROOT/bin/fake-lock" FAKE_LOCK_ROOT="$ROOT/lockbucket" \
        $1 \
        bash "$SCRIPT_DIR/run-scrape.sh" va > "$RUN_ROOT/stdout.log" 2> "$RUN_ROOT/stderr.log"
    RUN_RC=$?
}
status() { tail -1 "$RUN_ROOT/stdout.log" | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])' 2>/dev/null || echo "<none>"; }
mode()   { tail -1 "$RUN_ROOT/stdout.log" | python3 -c 'import json,sys; print(json.load(sys.stdin)["mode"])'   2>/dev/null || echo "<none>"; }
stored()       { cat "$ROOT/bucket/e2ens/va/va/va.ts" 2>/dev/null || echo "<absent>"; }
# CONTENTS, not the list of paths. A path listing is unchanged when an object is overwritten in
# place, which is exactly the regression these assertions exist to catch.
store_snapshot() {
    find "$ROOT/bucket/e2ens" -type f 2>/dev/null | sort | while read -r f; do
        printf '%s %s\n' "${f#$ROOT/bucket/}" "$(md5 -q "$f")"
    done | md5
}
stored_count() { cat "$ROOT/bucket/e2ens/va/va/va.count" 2>/dev/null || echo "<absent>"; }

e2e ""
check "first run: full, because neither disk nor store remembers anything" "full" "$(mode)"
check "first run: succeeds" "ok" "$(status)"
check "first run: memory is now in the store" "yes" \
    "$([ "$(stored)" != "<absent>" ] && echo yes || echo no)"
check "first run: the stored count records a full run" "1:full" "$(stored_count)"

# THE acceptance criterion. Everything this machine knew is deleted; the only surviving copy of
# the watermark is the object in the store.
rm -f "$RUN_LOG_DIR/last-run"/va.*
e2e ""
check "local memory deleted: the run is STILL incremental" "incremental" "$(mode)"
check "local memory deleted: it read the cutoff from the store" "yes" \
    "$(grep -q "cutoff=" "$RUN_LOG_DIR/scraper.log" && echo yes || echo no)"
# Asserted on the count rather than the timestamp: with a stub scraper both runs finish inside
# the same second, and the watermark has one-second resolution, so comparing timestamps would be
# a coin flip. The mode in the count changes deterministically and says the same thing -- the
# store now holds THIS run's memory, not the previous one's.
check "second run: the store now holds the second run's memory" "1:incremental" "$(stored_count)"

echo "== nothing is published at all unless the import succeeded =="

# The invariant that makes publishing the baseline BEFORE the watermark safe, and the one worth
# pinning down. Michigan builds its fetch set by comparing the site against the baseline, so a
# bill already recorded there is not re-fetched -- which is only sound if a baseline can never
# reach the store describing bills that were not loaded into the database. Both persist calls
# sit after the import's exit status is checked, so a failed import publishes NOTHING.
# Seed the exact cache key with KNOWN OLD BYTES, so an in-place overwrite is detectable rather
# than invisible. $SCRAPER_MEMORY_CACHE_FILES is pointed at va for these cases -- the mechanism
# is jurisdiction-agnostic and the e2e harness drives va.
mkdir -p "$ROOT/bucket/e2ens/va/_cache"
printf 'OLD-BASELINE-BYTES' > "$ROOT/bucket/e2ens/va/_cache/va_baseline_2026.json"
printf 'NEW-BASELINE-BYTES' > "$RUN_ROOT/cache/va_baseline_2026.json"
STORE_BEFORE=$(store_snapshot)
cat > "$RUN_ROOT/bin/os-update" <<STUB
#!/usr/bin/env bash
for a in "\$@"; do
    if [ "\$a" = "--import" ]; then
        echo "psycopg2.OperationalError: could not connect to server"
        exit 1
    fi
done
printf '{}' > "$RUN_ROOT/data/va/bill_stub9.json"
echo "scraped fine"
STUB
chmod +x "$RUN_ROOT/bin/os-update"
e2e ""
check "import failed: the run fails" "failed" "$(status)"
check "import failed: NOTHING was published, byte for byte" "$STORE_BEFORE" "$(store_snapshot)"
check "import failed: the old baseline was not overwritten" "OLD-BASELINE-BYTES" \
    "$(cat "$ROOT/bucket/e2ens/va/_cache/va_baseline_2026.json")"

echo "== a cache-publication failure must block every marker write =="

# Fail-closed, not merely ordered: run-scrape.sh guards the cache call with `if ! ...; then exit`,
# so a failure there returns before any marker can advance. Without that guard, ordering alone
# would still permit the one pairing that loses bills.
# The stub rewrites the baseline during its scrape pass, which is what the real scraper does --
# and it has to, because hydration legitimately pulls the stored copy down over any local one
# before the scrape runs. Without this the "new baseline" under test would be the old one.
cat > "$RUN_ROOT/bin/os-update" <<STUB
#!/usr/bin/env bash
for a in "\$@"; do
    if [ "\$a" = "--import" ]; then echo "import:"; echo "  bill: 1 new 0 updated 0 noop"; exit 0; fi
done
printf '{}' > "$RUN_ROOT/data/va/bill_stub7.json"
printf 'NEW-BASELINE-BYTES' > "$RUN_ROOT/cache/va_baseline_2026.json"
echo "scraped fine"
STUB
chmod +x "$RUN_ROOT/bin/os-update"
MARKERS_BEFORE=$(store_snapshot)
e2e "FAKE_S3_FAIL_PUT_MATCH=_cache SCRAPER_MEMORY_CACHE_FILES=va:va_baseline_*.json"
check "cache put fails: the run fails"  "failed" "$(status)"
check "cache put fails: NO marker advanced, byte for byte" "$MARKERS_BEFORE" "$(store_snapshot)"

echo "== the reachable partial state is the safe pairing, not the unsafe one =="

# Cache publication succeeds and the watermark write then fails. This IS reachable, and it is the
# state the ordering deliberately chooses: a NEW baseline beside the PREVIOUS cutoff. Safe,
# because the run that wrote that baseline had already scraped and imported successfully -- so
# the next run re-collects a wider window rather than skipping anything.
OLD_TS="$(stored)"
e2e "FAKE_S3_FAIL_PUT_MATCH=va.ts SCRAPER_MEMORY_CACHE_FILES=va:va_baseline_*.json"
check "watermark put fails: the run fails" "failed" "$(status)"
check "watermark put fails: the NEW baseline did land" "NEW-BASELINE-BYTES" \
    "$(cat "$ROOT/bucket/e2ens/va/_cache/va_baseline_2026.json")"
check "watermark put fails: the cutoff is still the previous run's" "$OLD_TS" "$(stored)"

rm -f "$RUN_ROOT/cache/va_baseline_2026.json"

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
# One second of real time so the watermark, which has one-second resolution, must visibly tick.
sleep 1
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

echo "== OPEN-187: the shared cross-machine lock =="

lock_helper() {
    SCRAPER_MEMORY_PREFIX=testns SCRAPER_LOCK_S3_CMD="$ROOT/bin/fake-lock" \
        bash -c ". \"$SCRIPT_DIR/scraper-memory.sh\"; $1" 2>/dev/null
}

check "lock key is scoped by source alone, not a scrape key" "testns/mi/_lock" \
    "$(lock_helper 'scraper_memory_lock_key mi')"

rc=$(lock_helper 'scraper_memory_acquire_lock mi run-a; echo $?')
check "acquire: a free lock succeeds" "0" "$rc"

rc=$( SCRAPER_MEMORY_PREFIX=testns SCRAPER_LOCK_S3_CMD="$ROOT/bin/fake-lock" \
      bash -c ". \"$SCRIPT_DIR/scraper-memory.sh\";
                scraper_memory_acquire_lock mi run-a >/dev/null;
                scraper_memory_acquire_lock mi run-b; echo \$?" 2>/dev/null )
check "acquire: a second run is refused (1), not told it is free" "1" "$rc"

rc=$( SCRAPER_MEMORY_PREFIX=testns SCRAPER_LOCK_S3_CMD="$ROOT/bin/fake-lock" \
      bash -c ". \"$SCRIPT_DIR/scraper-memory.sh\";
                scraper_memory_acquire_lock mi run-a >/dev/null;
                scraper_memory_release_lock mi run-a;
                scraper_memory_acquire_lock mi run-b; echo \$?" 2>/dev/null )
check "release then acquire: the next run succeeds" "0" "$rc"

# A stale lock (expires_at already in the past) must be RECLAIMED, not treated as live -- there
# is no pid to check across machines, so age is the only signal a dead holder ever leaves.
python3 -c "
import json
open('$ROOT/lockbucket/testns/mi/_lock', 'w').write(json.dumps({'holder': 'dead-run', 'acquired_at': 0, 'expires_at': 1}))
"
echo 1 > "$ROOT/lockbucket/testns/mi/_lock.etag"
rc=$(lock_helper 'scraper_memory_acquire_lock mi run-b; echo $?')
check "acquire: a stale lock is reclaimed (0), not refused" "0" "$rc"

# A live lock (expires_at in the future) must NOT be reclaimed just because it is being asked.
python3 -c "
import json, time
open('$ROOT/lockbucket/testns/mi/_lock', 'w').write(json.dumps({'holder': 'live-run', 'acquired_at': time.time(), 'expires_at': time.time() + 3600}))
"
rc=$(lock_helper 'scraper_memory_acquire_lock mi run-c; echo $?')
check "acquire: a live lock is refused (1), not reclaimed" "1" "$rc"

# "Could not tell" must never be mistaken for "acquired" or "refused" -- same three-way
# discipline as scraper_memory_fetch, and the same reason: a genuinely unreadable store here
# would otherwise let two runs believe they both hold the same jurisdiction's lock.
cat > "$ROOT/bin/fake-lock-broken" <<'STUB'
#!/usr/bin/env bash
echo "Could not connect to the endpoint URL" >&2
exit 1
STUB
chmod +x "$ROOT/bin/fake-lock-broken"
rc=$( SCRAPER_MEMORY_PREFIX=testns SCRAPER_LOCK_S3_CMD="$ROOT/bin/fake-lock-broken" \
      bash -c ". \"$SCRIPT_DIR/scraper-memory.sh\"; scraper_memory_acquire_lock mi run-a; echo \$?" 2>/dev/null )
check "acquire during an outage: returns 2, not 0 or 1" "2" "$rc"

echo
if [ "$FAIL" -eq 0 ]; then
    echo "ALL PASS ($PASS assertions)"
    exit 0
fi
echo "$FAIL FAILED, $PASS passed"
exit 1
