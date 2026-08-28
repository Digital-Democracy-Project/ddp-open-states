#!/usr/bin/env bash
# migrate-scraper-memory.sh — copy this checkout's existing scraper memory into the external
# store, so a cutover to SCRAPER_MEMORY_BACKEND=s3 starts from what is already known rather than
# giving every jurisdiction one gratuitous full collection (OPEN-181).
#
# Dry run by default. Nothing is uploaded without --commit.
#
#     bash migrate-scraper-memory.sh --prefix scraper-memory/production
#     bash migrate-scraper-memory.sh --prefix scraper-memory/production --commit
#
# WHAT IT MOVES, which is the ticket's "all three kinds, not just the watermarks":
#
#   * the watermark markers  logs/last-run/<key>.{ts,count,imported}
#   * the per-jurisdiction cache-resident memory  $CACHE_DIR/mi_last_actions_<session>.json
#
# WHAT IT DOES NOT MOVE: the ~105k-entry / 2.8 GB scrapelib HTTP cache. That decision, and what
# it costs on the first cloud run, is written down at the bottom of scraper-memory.sh.
#
# It is safe to re-run: put overwrites the object with the same content.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/scraper-memory.sh"

COMMIT=0
PREFIX=""
while [ $# -gt 0 ]; do
    case "$1" in
        --commit)  COMMIT=1; shift ;;
        --prefix)  PREFIX="${2:-}"; shift 2 ;;
        *) echo "unknown argument: $1" >&2; exit 2 ;;
    esac
done

if [ -z "$PREFIX" ]; then
    echo "--prefix is required. There is no default on purpose: an unnamespaced key would let a" >&2
    echo "dev checkout's markers overwrite production's memory, which is OPEN-159 with an object" >&2
    echo "key instead of a file path." >&2
    exit 2
fi

# Exported so the sourced helper's functions use them, exactly as run-scrape.sh sets them.
export SCRAPER_MEMORY_BACKEND=s3
export SCRAPER_MEMORY_PREFIX="$PREFIX"

if ! err=$(scraper_memory_check_config); then
    echo "ERROR: $err" >&2
    exit 1
fi

# The checkout's own paths, same rule as run-scrape.sh: never production's by absolute path.
LOG_DIR="${LOG_DIR:-$SCRIPT_DIR/logs}"
LAST_RUN_DIR="$LOG_DIR/last-run"
CACHE_DIR="${CACHE_DIR:-$SCRIPT_DIR/openstates-scrapers/_cache}"

echo "checkout:  $SCRIPT_DIR"
echo "markers:   $LAST_RUN_DIR"
echo "cache:     $CACHE_DIR"
echo "prefix:    $PREFIX"
[ "$COMMIT" = "1" ] && echo "mode:      COMMIT (uploading)" || echo "mode:      dry run (nothing will be uploaded)"
echo

UPLOADED=0
SKIPPED=0
FAILED=0

upload() {  # <local-file> <object-key>
    local src="$1" key="$2"
    if [ "$COMMIT" != "1" ]; then
        echo "  would upload  $(basename "$src")  ->  $key"
        UPLOADED=$((UPLOADED + 1))
        return 0
    fi
    if scraper_memory_store "$src" "$key"; then
        echo "  uploaded      $(basename "$src")  ->  $key"
        UPLOADED=$((UPLOADED + 1))
    else
        echo "  FAILED        $(basename "$src")  ->  $key" >&2
        FAILED=$((FAILED + 1))
    fi
}

echo "== watermark markers =="
for f in "$LAST_RUN_DIR"/*.ts "$LAST_RUN_DIR"/*.count "$LAST_RUN_DIR"/*.imported; do
    [ -e "$f" ] || continue
    name=$(basename "$f")
    # Backups and the one junk key left by a mis-invocation are memory of nothing. Uploading a
    # `.bak-pre-full-rescrape-20260728` would put a deliberately-superseded watermark into the
    # store under a key that looks live.
    case "$name" in
        *.bak-*|--help.*) SKIPPED=$((SKIPPED + 1)); continue ;;
    esac
    # <scrape-key>.<ext>, and the state is the first segment of the scrape key -- `fl_session_2026`
    # is fl, `usa_session_119_chamber_lower` is usa, a bare `az` is az.
    key="${name%.*}"
    state="${key%%_*}"
    upload "$f" "$(scraper_memory_key "$state" "$key" "$name")"
done

echo
echo "== cache-resident memory =="
# Driven off the marker inventory rather than a hardcoded list, so this stays correct if a second
# jurisdiction ever gets an entry in SCRAPER_MEMORY_CACHE_FILES. The file names itself -- see the
# comment on that variable for why a template cannot work here.
for f in "$LAST_RUN_DIR"/*.ts; do
    [ -e "$f" ] || continue
    name=$(basename "$f")
    case "$name" in *.bak-*|--help.*) continue ;; esac
    key="${name%.ts}"
    state="${key%%_*}"
    glob=$(scraper_memory_cache_glob "$state")
    [ -n "$glob" ] || continue
    found=0
    for c in "$CACHE_DIR"/$glob; do
        [ -f "$c" ] || continue
        found=1
        upload "$c" "$(scraper_memory_key "$state" "$key" "$(basename "$c")")"
    done
    if [ "$found" = "0" ]; then
        echo "  absent        $glob (nothing to migrate for $key)"
        SKIPPED=$((SKIPPED + 1))
    fi
done

echo
echo "=== MEMORY MIGRATION SUMMARY: uploaded=$UPLOADED skipped=$SKIPPED failed=$FAILED prefix=$PREFIX ==="
[ "$FAILED" -eq 0 ]
