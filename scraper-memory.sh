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
    if ! command -v "$SCRAPER_MEMORY_S3_CMD" >/dev/null 2>&1 && [ ! -x "$SCRAPER_MEMORY_S3_CMD" ]; then
        echo "SCRAPER_MEMORY_BACKEND=s3 but '$SCRAPER_MEMORY_S3_CMD' is not executable"
        return 1
    fi
    # OPEN-187: the shared lock is mandatory whenever memory is externalised, not a separate
    # opt-in -- a jurisdiction reachable from S3 is a jurisdiction reachable from both runners,
    # and running without the lock is worse than not externalising memory at all (OPEN-201's
    # coexistence is exactly the situation it exists to protect). See
    # OPEN-187-scraper-lock-wrapper-setup.md for how to install it.
    if ! command -v "$SCRAPER_LOCK_S3_CMD" >/dev/null 2>&1 && [ ! -x "$SCRAPER_LOCK_S3_CMD" ]; then
        echo "SCRAPER_MEMORY_BACKEND=s3 but '$SCRAPER_LOCK_S3_CMD' is not executable -- see OPEN-187-scraper-lock-wrapper-setup.md"
        return 1
    fi
    return 0
}

# scraper_memory_cache_key <source> <filename>
# Where cache-resident memory lives: `<prefix>/<source>/_cache/<filename>`, keyed on the SOURCE
# and not on the scrape key. §4 requires the key to include every parameter whose change
# invalidates the memory, and for these files the filename already carries it -- Michigan's
# baseline is `mi_last_actions_<session>.json`, so the session is in the name.
#
# Keying it on the scrape key as well was the first version and it was fragile in a way worth
# recording: production invokes Michigan with no session argument, so the key is a bare `mi`,
# and a one-off manual run with an explicit session would have written its baseline to a
# different prefix -- where the next scheduled run would not find it, and MI would refuse to run
# incrementally for a reason nobody could see. The scrape key adds nothing here and takes that
# away.
scraper_memory_cache_key() {
    echo "${SCRAPER_MEMORY_PREFIX}/${1}/_cache/${2}"
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
# Absence is therefore matched POSITIVELY and NARROWLY, on the shapes the store actually emits
# for a missing key: the `(404)` of a HeadObject miss, or an explicit NoSuchKey (verified
# 2026-08-27 -- `get` on a missing key exits 1 with "An error occurred (404) when calling the
# HeadObject operation: Not Found"). A bare "Not Found" is deliberately NOT matched: it is
# ordinary English that a proxy, a VPN captive page or a future wrapper message could easily
# contain, and reading one of those as "this source has no memory" is the expensive direction to
# be wrong in. Anything unrecognised -- a timeout, a credential failure, a refused connection --
# falls through to 2.
#
# The fetch lands in a temporary file and is renamed over the destination only on success, so a
# failed or interrupted download CANNOT damage the copy already on disk. The real wrapper happens
# to do this internally too, but relying on that would make the safety of this function a
# property of a script in ~/bin that this repo does not own.
scraper_memory_fetch() {
    local key="$1" dest="$2" tmp="${2}.fetch.$$" out rc
    out=$("$SCRAPER_MEMORY_S3_CMD" get "$key" "$tmp" 2>&1); rc=$?
    if [ "$rc" -eq 0 ]; then
        mv "$tmp" "$dest" && return 0
        rm -f "$tmp"
        echo "fetched $key but could not move it into place at $dest" >&2
        return 2
    fi
    rm -f "$tmp"
    case "$out" in
        *"(404)"*|*NoSuchKey*) return 1 ;;
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
# Same three-way discipline as scraper_memory_fetch, and the same reason. Empty is recognised
# only as the EXACT shape the wrapper produces for a prefix that holds nothing -- exit 1 with no
# output (verified 2026-08-27; a prefix that does hold something exits 0). Any other non-zero
# status is unreadable, including the 128+N of a signalled process: a wrapper killed mid-list
# also produces no output, and "the process was killed" must not read as "this source has no
# memory".
scraper_memory_list() {
    local prefix="$1" out rc
    out=$("$SCRAPER_MEMORY_S3_CMD" ls "$prefix" 2>&1); rc=$?
    if [ "$rc" -ne 0 ] && { [ -n "$out" ] || [ "$rc" -ne 1 ]; }; then
        [ -n "$out" ] && echo "$out" >&2
        [ -n "$out" ] || echo "listing $prefix exited $rc with no output" >&2
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
# Non-zero as soon as anything that exists locally could not be stored.
#
# THE ORDER IS THE SAFETY PROPERTY, AND IT IS NOT ATOMICITY. The wrapper offers put/get/ls/info
# and nothing else -- no transaction, no conditional put, no delete -- so several objects cannot
# be published together and a failure part way through cannot be rolled back. What can be
# arranged is WHICH object is exposed last, and that turns a partial failure from dangerous into
# merely wasteful:
#
#   * `.ts` is the authorising object. Its presence is what makes the next run incremental, and
#     an incremental run skips everything before its cutoff. So it goes LAST, after the two
#     reporting markers, and this function returns at the first failure rather than pressing on.
#     A partial publication therefore leaves the watermark where it was, and the next run
#     re-collects a window that was already collected -- duplicated work, never skipped bills.
#   * Cache-resident memory (Michigan's baseline) is published EARLIER STILL, by
#     run-scrape.sh calling scraper_memory_persist_cache first. The baseline is what makes an
#     incremental run SAFE, and the combination to avoid is a new cutoff sitting beside an old
#     baseline: MI would then run incrementally, compare against stale actions, and silently skip
#     bills that had moved. Publishing the baseline before the watermark makes that combination
#     unreachable -- if the baseline fails to store, the watermark never advances at all.
#
# So the claim this file makes is precise: publication is ordered, not atomic, and every failure
# mode it leaves behind is one where a window gets re-collected rather than skipped.
scraper_memory_persist_markers() {
    local state="$1" key="$2" dir="$3" name
    scraper_memory_enabled || return 0
    for name in "${key}.count" "${key}.imported" "${key}.ts"; do
        [ -f "$dir/$name" ] || continue
        scraper_memory_store "$dir/$name" "$(scraper_memory_key "$state" "$key" "$name")" || return 1
    done
    return 0
}

# scraper_memory_hydrate_cache <state> <cache-dir>
# The per-jurisdiction memory file that lives in $CACHE_DIR -- today only Michigan's last-action
# baseline. 0 = done (including "this jurisdiction has none"), 2 = the store could not be read.
#
# Handled HERE, in the runner, rather than by teaching the scraper to read S3. Two reasons, and
# the second is the one that decides it: the contract puts the completion record and the memory
# store on the runner's side of the line, and openstates-scrapers is a fork of a public project
# DDP does not control, so an S3 client inside mi/bills.py is a permanent merge conflict against
# every future upstream pull. The scraper keeps reading the same path it always has.
scraper_memory_hydrate_cache() {
    local state="$1" cache_dir="$2" glob objkey base listing rc=0
    scraper_memory_enabled || return 0
    glob=$(scraper_memory_cache_glob "$state")
    [ -n "$glob" ] || return 0
    listing=$(scraper_memory_list "$(scraper_memory_cache_key "$state" "")") || return 2
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

# scraper_memory_persist_cache <state> <cache-dir>
# Called BEFORE the watermark is published -- see the ordering note on
# scraper_memory_persist_markers, which is where the reasoning lives.
scraper_memory_persist_cache() {
    local state="$1" cache_dir="$2" glob f
    scraper_memory_enabled || return 0
    glob=$(scraper_memory_cache_glob "$state")
    [ -n "$glob" ] || return 0
    for f in "$cache_dir"/$glob; do
        [ -f "$f" ] || continue
        scraper_memory_store "$f" "$(scraper_memory_cache_key "$state" "$(basename "$f")")" || return 1
    done
    return 0
}

# --- OPEN-187: the shared, cross-machine scrape lock -----------------------------------------
#
# run-scrape.sh's existing per-source lock (OPEN-154) is a `mkdir` on THIS machine's /tmp --
# invisible to a Fargate task, and a Fargate task's own lock (cloud_collector.py's SourceLock)
# is invisible here. Once a jurisdiction can run on either path (OPEN-201's coexistence), that
# silently stopped protecting against a double collection.
#
# A SEPARATE command from SCRAPER_MEMORY_S3_CMD, deliberately: the existing wrapper
# (ddp-prod-s3-openstates-backups) has a plain put/get/ls/info contract with no conditional-write
# support, and its bucket (ddp-openstates-backups) is the one OPEN-200/OPEN-183 found carries an
# unrelated 30-day deletion rule -- not where this belongs even if the wrapper could do it.
# SCRAPER_LOCK_S3_CMD talks to ddp-openstates-scraper-memory instead, through a new,
# narrowly-scoped wrapper exposing exactly the three operations locking needs. See
# OPEN-187-scraper-lock-wrapper-setup.md for the wrapper's exact contract and the script to
# install it -- an operator (root/sudo) action this repo cannot do for itself, same as
# ddp-prod-s3-openstates-backups's own setup.
SCRAPER_LOCK_S3_CMD="${SCRAPER_LOCK_S3_CMD:-ddp-prod-s3-scraper-memory}"

# Matches OPEN-154's own existing dead-holder threshold, for the same reason it was chosen
# there: deliberately far longer than any real scrape (MA's full walk measured 8.2h), so a lock
# only ever gets reclaimed once it is genuinely abandoned, never while a slow but healthy run is
# still in progress.
SCRAPER_LOCK_TTL_SECONDS=86400

# scraper_memory_lock_key <source>
# Keyed on SOURCE ALONE, matching OPEN-154's own local lock exactly, and for the identical
# reason: the hazard is the shared data directory openstates-core wipes at scrape start, and
# FL's several sessions share one -- a per-scrape-key lock would let them race each other.
scraper_memory_lock_key() {
    echo "${SCRAPER_MEMORY_PREFIX}/${1}/_lock"
}

# scraper_memory_acquire_lock <source> <holder-id>
# 0 = acquired (including reclaiming a stale lock), 1 = another live holder has it,
# 2 = could not tell. Same three-way discipline as scraper_memory_fetch/list and the same
# reason: a lock this function cannot confirm is free must never be treated as free.
#
# Age-based expiry only, not liveness -- there is no pid to check across a Mac and a Fargate
# task, so "the holder is gone" can only ever mean "past its own stated expiry". Mirrors
# cloud_collector.py's SourceLock exactly (same TTL, same reclaim-via-conditional-write shape)
# so the two clients agree on what a lock object means, even though this one shells out to a
# sudo-gated wrapper rather than calling boto3 directly.
scraper_memory_acquire_lock() {
    local source="$1" holder="$2" key body_file now expires_at out rc etag existing_expires
    key=$(scraper_memory_lock_key "$source")
    now=$(date +%s)
    expires_at=$((now + SCRAPER_LOCK_TTL_SECONDS))
    body_file=$(mktemp)
    printf '{"holder":"%s","acquired_at":%s,"expires_at":%s}' "$holder" "$now" "$expires_at" > "$body_file"

    out=$("$SCRAPER_LOCK_S3_CMD" lock-acquire "$key" "$body_file" 2>&1); rc=$?
    if [ "$rc" -eq 0 ]; then
        rm -f "$body_file"
        return 0
    fi
    case "$out" in
        *PreconditionFailed*|*"(412)"*) ;;  # someone holds it -- check whether it is stale
        *)
            rm -f "$body_file"
            echo "$out" >&2
            return 2
            ;;
    esac

    out=$("$SCRAPER_LOCK_S3_CMD" lock-read "$key" 2>&1); rc=$?
    if [ "$rc" -ne 0 ]; then
        rm -f "$body_file"
        case "$out" in
            # Raced a release/expiry between our failed acquire and this read -- the key that
            # just refused us is now gone. One retry, not a loop: a second miss here means
            # something is actively churning this key, and guessing would be exactly the
            # mistake this function exists to avoid.
            *"(404)"*|*NoSuchKey*)
                body_file=$(mktemp)
                printf '{"holder":"%s","acquired_at":%s,"expires_at":%s}' "$holder" "$now" "$expires_at" > "$body_file"
                out=$("$SCRAPER_LOCK_S3_CMD" lock-acquire "$key" "$body_file" 2>&1); rc=$?
                rm -f "$body_file"
                [ "$rc" -eq 0 ] && return 0
                return 1
                ;;
        esac
        echo "$out" >&2
        return 2
    fi
    etag=$(printf '%s' "$out" | cut -f1)
    # [[:space:]]* between the colon and the digits: cloud_collector.py's SourceLock writes
    # this same JSON via json.dumps(), which inserts a space after every colon by default --
    # this parser has to read a lock either side ever wrote, not just its own bash-printf'd
    # (space-free) format. Missing this was a real bug, not a style nit: a stale python-written
    # lock parsed to an empty expires_at, which happened to still reclaim correctly (empty
    # fails the liveness check too), but a LIVE python-written lock parsed the same empty value
    # and was wrongly reclaimed instead of refused -- caught by this file's own test suite.
    existing_expires=$(printf '%s' "$out" | cut -f2- | sed -n 's/.*"expires_at":[[:space:]]*\([0-9][0-9]*\).*/\1/p')

    if [ -n "$existing_expires" ] && [ "$now" -le "$existing_expires" ]; then
        rm -f "$body_file"
        return 1  # a live holder
    fi

    out=$("$SCRAPER_LOCK_S3_CMD" lock-reclaim "$key" "$body_file" "$etag" 2>&1); rc=$?
    rm -f "$body_file"
    [ "$rc" -eq 0 ] && return 0
    case "$out" in
        *PreconditionFailed*|*"(412)"*) return 1 ;;  # someone else reclaimed it first
        *) echo "$out" >&2; return 2 ;;
    esac
}

# scraper_memory_release_lock <source> <holder-id>
# Marks the lock immediately expired rather than deleting it -- so the wrapper's credential
# never needs delete permission at all (OPEN-187-scraper-lock-wrapper-setup.md's IAM policy has
# none). Best-effort: a release that fails to land costs nothing beyond the lock living out its
# TTL, the same outcome as today's genuinely-abandoned case.
scraper_memory_release_lock() {
    local source="$1" holder="$2" key body_file now out etag
    key=$(scraper_memory_lock_key "$source")
    now=$(date +%s)
    out=$("$SCRAPER_LOCK_S3_CMD" lock-read "$key" 2>/dev/null) || return 0
    etag=$(printf '%s' "$out" | cut -f1)
    body_file=$(mktemp)
    printf '{"holder":"%s","acquired_at":%s,"expires_at":%s}' "$holder" "$now" "$((now - 1))" > "$body_file"
    "$SCRAPER_LOCK_S3_CMD" lock-reclaim "$key" "$body_file" "$etag" >/dev/null 2>&1 || true
    rm -f "$body_file"
    return 0
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
