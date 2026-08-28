#!/usr/bin/env bash
# scraper-memory.sh — per-source scraper memory, kept somewhere a disposable runner can reach.
#
# Sourced by run-scrape.sh. Nothing here runs on its own.
#
# WHAT "MEMORY" IS. Three things live on this machine's disk that a scrape needs in order to run
# incrementally, and `PLAN-scraper-execution-contract.md` §4 is the only one of its six clauses
# recorded as "does not conform":
#
#   1. Watermarks -- logs/last-run/<key>.ts plus the .count and .imported markers beside it.
#      Small, one set per source+session.
#   2. Michigan's last-action baseline -- _cache/mi_last_actions_<session>.json, 3,924 entries,
#      202 KB. NOT an optimisation: the scraper refuses to run incrementally without it.
#   3. The HTTP cache -- ~105k entries, 2.8 GB, which --fastmode reads.
#
# This file externalises (1) and (2). (3) is deliberately NOT migrated; see "THE HTTP CACHE" at
# the bottom, which states what that costs rather than leaving it silent.
#
# THE SHAPE, WHICH IS §4's AND NOT THIS FILE'S CHOICE. Keyed by source AND by whatever parameters
# scope the state -- never source alone. Michigan's baseline is per-session because bill numbers
# restart, so a shared record would let a new session's HB 4001 inherit the old one's history.
# $SCRAPE_KEY is already exactly that key (state + session + chamber), which is why the object
# layout below is built on it rather than on $STATE.
#
# THE VENDOR, WHICH IS THIS TICKET's CHOICE (OPEN-181). S3, through the existing
# `ddp-prod-s3-openstates-backups` wrapper. Not much of a contest: that bucket is already
# readable STANDARD_IA with put/get/ls/info and its own scoped IAM user, and it is the only cloud
# store reachable from this machine at all -- ~/.aws is root-owned with no readable credentials,
# and the wrapper's one sudo entry is allowlisted while general sudo is not. The obvious
# alternative, the openstates Postgres, is wrong by construction: it is ON the machine the
# scrapes are being moved off, and it does not move until Phase 2, after collection has already
# gone (Phase 1).
#
# OFF BY DEFAULT. SCRAPER_MEMORY_BACKEND is `local` unless set, and `local` makes every function
# here a no-op, so run-scrape.sh behaves exactly as it did. That is the ticket's rollback
# criterion -- a failed cutover is a config change back, not a revert.

# `local` (default; the local files stay authoritative and nothing here does anything) or `s3`.
SCRAPER_MEMORY_BACKEND="${SCRAPER_MEMORY_BACKEND:-local}"

# The command that talks to the bucket. Overridable ONLY so the test suite can stub it -- the
# alternative is a memory layer whose failure handling can never be exercised, and the failure
# handling is the part of this file most worth testing.
SCRAPER_MEMORY_S3_CMD="${SCRAPER_MEMORY_S3_CMD:-ddp-prod-s3-openstates-backups}"

# Object-key namespace. There is deliberately NO default, and a run refuses to start rather than
# invent one. This is OPEN-159/OPEN-172's lesson applied before it can bite: those tickets were
# about a dev checkout silently reading and then WRITING production's watermark files, because a
# path defaulted to production. An object key has no checkout to follow, so the same mistake here
# would be a dev run overwriting production's memory in a shared bucket -- with no local
# filesystem clue that it happened. Making it explicit costs one environment variable on a
# feature that is off by default.
SCRAPER_MEMORY_PREFIX="${SCRAPER_MEMORY_PREFIX:-}"

# Extra per-jurisdiction memory files that live in $CACHE_DIR rather than in logs/last-run.
# Flat comma-separated `<state>:<filename-glob>` list -- the shape OPEN-124 settled on for
# wrapper-local jurisdiction facts, rather than a chained `[ "$STATE" = "mi" ]` conditional. It is
# wrapper-local and not scheduler-owned by that rule's own test: it holds every time the wrapper
# runs, and it is a property of Michigan's data rather than of any rollout.
#
# A GLOB, not a name this file can construct, and that is not a stylistic choice. Michigan's
# baseline is `mi_last_actions_<session>.json`, but PRODUCTION RUNS MICHIGAN WITH NO SESSION
# ARGUMENT -- its markers are a bare `mi.ts` -- so the session in that filename is the SCRAPER's
# notion of the current session (mi/bills.py derives it), not anything the wrapper was told.
# Building the name here would mean duplicating that derivation and getting it wrong the day it
# changes. Found by dry-running migrate-scraper-memory.sh against production's real inventory,
# where a template produced `mi_last_actions_.json` and matched nothing.
#
# So the file names itself, and the store is asked what it holds. The session lives in the
# filename, which is why the object key does not need to carry it separately.
SCRAPER_MEMORY_CACHE_FILES="${SCRAPER_MEMORY_CACHE_FILES:-mi:mi_last_actions_*.json}"

# True when the external store is in use at all.
scraper_memory_enabled() { [ "$SCRAPER_MEMORY_BACKEND" = "s3" ]; }

# scraper_memory_check_config
# Non-zero, with a reason on stdout, when the backend is on but unusable. Called once by
# run-scrape.sh before anything else, so a misconfiguration fails the run at the start rather
# than halfway through.
scraper_memory_check_config() {
    scraper_memory_enabled || return 0
    if [ -z "$SCRAPER_MEMORY_PREFIX" ]; then
        echo "SCRAPER_MEMORY_BACKEND=s3 requires SCRAPER_MEMORY_PREFIX (no default: an unnamespaced key would let this run overwrite another checkout's memory)"
        return 1
    fi
    case "$SCRAPER_MEMORY_PREFIX" in
        *[!a-zA-Z0-9_/-]*)
            echo "SCRAPER_MEMORY_PREFIX contains characters that do not belong in an object key: '$SCRAPER_MEMORY_PREFIX'"
            return 1
            ;;
    esac
    command -v "$SCRAPER_MEMORY_S3_CMD" >/dev/null 2>&1 && return 0
    [ -x "$SCRAPER_MEMORY_S3_CMD" ] && return 0
    echo "SCRAPER_MEMORY_BACKEND=s3 but '$SCRAPER_MEMORY_S3_CMD' is not executable"
    return 1
}

# scraper_memory_key <source> <scrape-key> <filename>
# The object layout. Keyed on the scrape key, not the bare source, for the §4 reason above --
# `usa` runs lower and upper separately and FL runs eight sessions, and their memories are not
# interchangeable. The source segment is there so `ls <prefix>/mi/` answers "what does Michigan
# remember", which is the question an operator actually asks.
scraper_memory_key() {
    echo "${SCRAPER_MEMORY_PREFIX}/${1}/${2}/${3}"
}

# scraper_memory_fetch <object-key> <destination-path>
#
# 0 = fetched, 1 = the object is genuinely not there, 2 = could not tell.
#
# THE THREE-WAY RETURN IS THE WHOLE POINT OF THIS FUNCTION. §4 says absent memory means a full
# collection, and for Michigan it means refusing to run at all. So collapsing "the store did not
# answer" into "absent" would convert a momentary S3 blip into a ~3,900-request full walk of the
# fleet's most block-sensitive site -- precisely the self-inflicted outage §4 warns about. The
# caller fails the run on 2 instead, which writes no markers and leaves the window eligible.
#
# Absence is therefore matched POSITIVELY, on the 404 the wrapper reports for a missing key
# (verified 2026-08-27: `get` on a missing key exits 1 with "An error occurred (404) ... Not
# Found" and leaves no destination file). Anything else -- a timeout, a credential failure, a
# refused connection -- falls through to 2.
scraper_memory_fetch() {
    local key="$1" dest="$2" out rc
    out=$("$SCRAPER_MEMORY_S3_CMD" get "$key" "$dest" 2>&1); rc=$?
    [ "$rc" -eq 0 ] && return 0
    case "$out" in
        *"(404)"*|*"Not Found"*|*"NoSuchKey"*) return 1 ;;
    esac
    echo "$out" >&2
    return 2
}

# scraper_memory_store <local-path> <object-key>
# Non-zero on any failure, with the store's own message on stderr. The caller decides what that
# means; this function does not swallow it, because a silent failure to persist memory means the
# NEXT run does a full collection without anyone knowing why.
scraper_memory_store() {
    local src="$1" key="$2" out rc
    [ -f "$src" ] || return 0
    out=$("$SCRAPER_MEMORY_S3_CMD" put "$src" "$key" 2>&1); rc=$?
    [ "$rc" -eq 0 ] && return 0
    echo "$out" >&2
    return 1
}

# scraper_memory_cache_glob <state>
# The filename glob for the extra memory this jurisdiction keeps in $CACHE_DIR, or nothing.
scraper_memory_cache_glob() {
    local state="$1" entry
    local IFS=,
    for entry in $SCRAPER_MEMORY_CACHE_FILES; do
        case "$entry" in
            "$state":*) echo "${entry#*:}"; return 0 ;;
        esac
    done
    return 0
}

# scraper_memory_list <object-prefix>
# The object keys under a prefix, one per line. 0 = listed (possibly empty), 2 = could not tell.
#
# Same three-way discipline as scraper_memory_fetch, and the same reason. The wrapper exits
# non-zero with NO output for a prefix that holds nothing (verified 2026-08-27), so an empty
# failure is "nothing there" and a failure that said something is a failure.
scraper_memory_list() {
    local prefix="$1" out rc
    out=$("$SCRAPER_MEMORY_S3_CMD" ls "$prefix" 2>&1); rc=$?
    if [ "$rc" -ne 0 ] && [ -n "$out" ]; then
        echo "$out" >&2
        return 2
    fi
    # `ls` prints `<date> <time> <size> <key>`; the key is the last field.
    echo "$out" | awk 'NF { print $NF }'
    return 0
}

# scraper_memory_hydrate_markers <state> <scrape-key> <last-run-dir>
# 0 = the local marker files now reflect the store, 2 = the store could not be read.
#
# An object that is absent leaves any existing local file ALONE rather than deleting it. That is
# what makes the cutover seamless -- the first run under this backend finds nothing in the store,
# runs incrementally off the local watermark it has always used, and persists it at the end, so
# no jurisdiction gets one gratuitous full collection on the day the switch is flipped.
#
# The cost of that choice, named rather than left to be discovered: deleting an object from the
# store does NOT by itself force a full collection on this machine, because the local file is
# still there and still wins. Forcing one means removing both, or using migrate-scraper-memory.sh
# to put the store back in a known state.
scraper_memory_hydrate_markers() {
    local state="$1" key="$2" dir="$3" name rc
    scraper_memory_enabled || return 0
    for name in "${key}.ts" "${key}.count" "${key}.imported"; do
        rc=0
        scraper_memory_fetch "$(scraper_memory_key "$state" "$key" "$name")" "$dir/$name" || rc=$?
        [ "$rc" -eq 2 ] && return 2
    done
    return 0
}

# scraper_memory_persist_markers <state> <scrape-key> <last-run-dir>
# Non-zero if anything that exists locally could not be stored.
scraper_memory_persist_markers() {
    local state="$1" key="$2" dir="$3" name failed=0
    scraper_memory_enabled || return 0
    for name in "${key}.ts" "${key}.count" "${key}.imported"; do
        [ -f "$dir/$name" ] || continue
        scraper_memory_store "$dir/$name" "$(scraper_memory_key "$state" "$key" "$name")" || failed=1
    done
    return "$failed"
}

# scraper_memory_hydrate_cache <state> <scrape-key> <cache-dir>
# The per-jurisdiction memory file that lives in $CACHE_DIR -- today only Michigan's last-action
# baseline. 0 = done (including "this jurisdiction has none"), 2 = the store could not be read.
#
# Handled HERE, in the runner, rather than by teaching the scraper to read S3. Two reasons, and
# the second is the one that decides it: the contract puts the completion record and the memory
# store on the runner's side of the line, and openstates-scrapers is a fork of a public project
# DDP does not control, so an S3 client inside mi/bills.py is a permanent merge conflict against
# every future upstream pull. The scraper keeps reading the same path it always has.
scraper_memory_hydrate_cache() {
    local state="$1" key="$2" cache_dir="$3" glob objkey base listing rc=0
    scraper_memory_enabled || return 0
    glob=$(scraper_memory_cache_glob "$state")
    [ -n "$glob" ] || return 0
    listing=$(scraper_memory_list "$(scraper_memory_key "$state" "$key" "")") || return 2
    mkdir -p "$cache_dir"
    for objkey in $listing; do
        base=$(basename "$objkey")
        # Only what this jurisdiction declares as memory. The same prefix could later hold
        # something else, and fetching it into $CACHE_DIR would be silently wrong.
        case "$base" in
            $glob) ;;
            *) continue ;;
        esac
        rc=0
        scraper_memory_fetch "$objkey" "$cache_dir/$base" || rc=$?
        [ "$rc" -eq 2 ] && return 2
    done
    return 0
}

# scraper_memory_persist_cache <state> <scrape-key> <cache-dir>
scraper_memory_persist_cache() {
    local state="$1" key="$2" cache_dir="$3" glob f failed=0
    scraper_memory_enabled || return 0
    glob=$(scraper_memory_cache_glob "$state")
    [ -n "$glob" ] || return 0
    for f in "$cache_dir"/$glob; do
        [ -f "$f" ] || continue
        scraper_memory_store "$f" "$(scraper_memory_key "$state" "$key" "$(basename "$f")")" || failed=1
    done
    return "$failed"
}

# THE HTTP CACHE -- decided, not forgotten (OPEN-181 acceptance criterion).
#
# The ~105k-entry / 2.8 GB scrapelib cache is NOT migrated, and is NOT part of memory as this
# file defines it. Three reasons, in order of weight:
#
#   1. It is not memory. Nothing about correctness depends on it: a run without it collects the
#      same bills, and §4's semantics (absent => full, present => incremental) are carried
#      entirely by the watermarks and Michigan's baseline, both of which ARE migrated. The cache
#      only makes `--fastmode` -- the retry-from-disk path after a failed scrape -- possible.
#   2. What it costs is a real number and it is small: at STANDARD_IA rates 2.8 GB is roughly
#      $0.04/month plus about a dollar of one-time upload. The reason not to move it is not the
#      bill.
#   3. It is not durable state, so a copy of it would be stale on arrival. It is a cache of other
#      people's web pages, rebuilt continuously by every run.
#
# WHAT THAT COSTS, STATED SO THE FIRST CLOUD RUN IS NOT A MYSTERY: a disposable runner starts
# with an empty cache, so `--fastmode` -- the automatic second attempt run-scrape.sh makes after a
# failed scrape -- has nothing to read and will not rescue a failed run the way it does here. The
# first run on any new runner therefore fetches everything from the source site. That matters
# most for Michigan, whose full walk is ~3,900 fetches against a hard 10 requests/minute cap, so
# roughly 6.5 hours. It is a throughput cost on cutover, not a correctness one, and it is the
# thing that would otherwise make the first cloud run look pathologically slow for a reason
# nobody wrote down.
