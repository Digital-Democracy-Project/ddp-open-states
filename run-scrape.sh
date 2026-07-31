#!/usr/bin/env bash
# Usage: run-scrape.sh <state> [session=XXXX]
set -e

STATE=$1
SESSION_ARG=${2:-""}
LOG_DIR=/Users/agentsmith/Developer/repos/ddp-open-states/logs
OS_UPDATE=/Users/agentsmith/Developer/repos/ddp-open-states/.venv/bin/os-update

LAST_RUN_DIR="$LOG_DIR/last-run"
SCRAPE_KEY=$(echo "${STATE}${SESSION_ARG:+ $SESSION_ARG}" | tr ' =' '__')
TS_FILE="$LAST_RUN_DIR/${SCRAPE_KEY}.ts"
COUNT_FILE="$LAST_RUN_DIR/${SCRAPE_KEY}.count"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_DIR/scraper.log"; }

# App-managed log rotation (mirrors the CAMS/broker convention — no newsyslog/logrotate, no sudo).
# scraper.log is written by concurrent run-scrape.sh processes, so we copy-then-truncate IN PLACE
# (same inode) at 50 MB so in-flight tee/>> appenders keep writing safely; keep 7 gzipped archives.
# No lock needed: copy-then-truncate + keep-N is race-tolerant (worst case a duplicate archive).
rotate_scraper_log() {
    local f="$LOG_DIR/scraper.log" max=$((50 * 1024 * 1024))
    [ -f "$f" ] || return 0
    local size; size=$(stat -f%z "$f" 2>/dev/null || echo 0)
    [ "$size" -gt "$max" ] || return 0
    gzip -c "$f" > "$f.$(date -u +%Y%m%dT%H%M%SZ).gz" 2>/dev/null && : > "$f"
    ls -1t "$f".*.gz 2>/dev/null | tail -n +8 | xargs rm -f 2>/dev/null || true
}
rotate_scraper_log

INCREMENTAL_FLAG=""
if [ -f "$TS_FILE" ]; then
    LAST_RUN=$(cat "$TS_FILE")
    START_ARG=$(python3 -c "
import datetime, sys
try:
    dt = datetime.datetime.strptime('$LAST_RUN', '%Y-%m-%dT%H:%M:%S')
    print((dt - datetime.timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%S'))
except Exception:
    sys.exit(0)
" 2>/dev/null)
    if [ -n "$START_ARG" ]; then
        INCREMENTAL_FLAG="start=$START_ARG"
    fi
fi

source /Users/agentsmith/Developer/repos/ddp-open-states/activate.sh

# Slack alert on any scrape/import failure
SLACK_TOKEN=$(grep -E '^SLACK_BOT_TOKEN=' /Users/agentsmith/Developer/repos/ddp-agents/.env \
    2>/dev/null | head -1 | cut -d'=' -f2- | tr -d '"'"'" | awk '{print $1}')

# CAMS's CodeBot failure listener (PLAN-failure-to-codebot) — a real, repeated
# scrape bug should reach Agent Smith triage, not just the Slack alert below.
# Found 2026-07-23: the FL 2024 backfill failed 3 days running on the same
# ValueError (fl/bills.py's vote-count check) and nothing ever told CAMS,
# because nothing here called it.
CAMS_TOKEN=$(grep -E '^CAMS_API_TOKEN=' /Users/agentsmith/Developer/repos/ddp-agents/.env \
    2>/dev/null | head -1 | cut -d'=' -f2- | tr -d '"'"'" | awk '{print $1}')
CAMS_URL="${CAMS_URL:-http://localhost:8000}"

on_failure() {
    log "ERROR: scrape/import failed for $STATE"
    [ -n "$SLACK_TOKEN" ] && curl -sf --max-time 10 \
        -X POST https://slack.com/api/chat.postMessage \
        -H "Authorization: Bearer $SLACK_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"channel\": \"#automation-errors\", \"text\": \"⚠️ *OpenStates scrape failed: $STATE* — check ~/Developer/repos/ddp-open-states/logs/scraper.log\"}" \
        >/dev/null || true
    report_failure_to_cams
}

# Best-effort POST to CAMS's `/api/v1/failures` (service="ddp-open-states",
# matching config/codebot_allowlist.yaml's OPEN-project services list) so a
# genuine scrape/import bug can get triaged into a Jira ticket. FAILURE_ERROR_TYPE
# / FAILURE_MESSAGE are set by the caller when a real exception was parsed out of
# the scrape output; otherwise this reports a generic failure (still useful —
# CAMS/Agent Smith decides whether it's code-bug-shaped or not). curl -sf + || true
# throughout: a reporting failure (CAMS down, bad token, network) must never fail
# the scrape script itself or mask the real error above.
report_failure_to_cams() {
    [ -n "$CAMS_TOKEN" ] || return 0
    local error_type="${FAILURE_ERROR_TYPE:-ScrapeOrImportFailure}"
    local message="${FAILURE_MESSAGE:-scrape/import failed for $STATE ${SESSION_ARG} (see logs/scraper.log)}"
    python3 -c '
import json, sys
print(json.dumps({
    "v": 1,
    "service": "ddp-open-states",
    "error_type": sys.argv[1],
    "message": sys.argv[2],
    "metadata": {"state": sys.argv[3], "session": sys.argv[4]},
}))
' "$error_type" "$message" "$STATE" "$SESSION_ARG" 2>/dev/null | \
        curl -sf --max-time 10 -X POST "$CAMS_URL/api/v1/failures" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $CAMS_TOKEN" \
            -d @- >/dev/null || true
}
trap 'on_failure' ERR

# Apply local patches — skipped when SKIP_PATCHES=1 (managed by ddp-sync scheduler)
if [ "${SKIP_PATCHES:-}" != "1" ]; then
    bash /Users/agentsmith/Developer/repos/ddp-open-states/apply-local-patches.sh \
        >> "$LOG_DIR/scraper.log" 2>&1
fi

# Worktree lock (READER) — drop a PID marker so apply-local-patches.sh won't rebuild the scraper
# tree while this scrape reads it. Per-PID file → concurrent secondary-state scrapes coexist
# (each its own marker). Created AFTER the patch step above (so this run's own patch step isn't
# blocked by it) and removed on any exit.
SCRAPE_MARKER_DIR=/tmp/ddp-openstates-scrapes
mkdir -p "$SCRAPE_MARKER_DIR"
READER_MARKER="$SCRAPE_MARKER_DIR/$$"
touch "$READER_MARKER"
# Single EXIT trap for the whole script — bash keeps only the last one registered for a given
# signal, so the sweep-loop cleanup below is folded in here rather than set again later (which
# would silently drop this READER_MARKER cleanup). $SWEEP_PID is a harmless no-op when
# SWEEP_IMPORT_ENABLED=0 (never set). $IMPORT_LOCK_HELD tracks, in THIS process's own memory,
# whether it currently holds the import lock — correct without needing to compare PIDs at all:
# the backgrounded sweep loop has its own separate copy of this variable in its own process
# memory, so this trap (which runs in the main script, on the main script's exit) can only ever
# see this process's own true "do I currently hold it" state, never the sweep's.
trap 'rm -f "$READER_MARKER"; kill "$SWEEP_PID" 2>/dev/null || true; wait "$SWEEP_PID" 2>/dev/null || true;
      [ "$IMPORT_LOCK_HELD" = "1" ] && rm -rf "$IMPORT_LOCK_DIR"' EXIT

MODE="full"
[ -n "$INCREMENTAL_FLAG" ] && MODE="incremental"
log "Starting scrape: $STATE $SESSION_ARG ($MODE${INCREMENTAL_FLAG:+ cutoff=${INCREMENTAL_FLAG#start=}})"

# Pass cache/data dirs explicitly so os-update doesn't fall back to
# os.getcwd()/_cache — which resolves to /_cache (read-only) under launchd.
DIR_FLAGS="--cachedir $CACHE_DIR --datadir $SCRAPED_DATA_DIR"

# MI has a pagination overlap that produces duplicate bill JSON files.
# VA has the same issue (confirmed 2026-06-29 via DuplicateItemError on HB 1054).
# --allow_duplicates keeps the first instance and silently skips the rest.
# See: https://github.com/openstates/openstates-scrapers/issues/5697
IMPORT_FLAGS=""
[ "$STATE" = "mi" ] || [ "$STATE" = "fl" ] || [ "$STATE" = "va" ] && IMPORT_FLAGS="--allow_duplicates"

# Import-as-you-go (PLAN-incremental-scraping.md, "Reopened 2026-07-30", approved for
# implementation) — off by default. When enabled, a killed scrape no longer loses everything:
# a periodic sweep imports scraped JSON into Postgres throughout the run instead of in one
# all-or-nothing transaction at the very end, and a pre-scrape recovery import saves any
# un-imported JSON from a previous interrupted run before --scrape wipes it. Roll out per
# jurisdiction (canary on VA/UT first) via SWEEP_IMPORT_ENABLED=1 in the calling environment.
SWEEP_IMPORT_ENABLED="${SWEEP_IMPORT_ENABLED:-0}"
STATE_DATADIR="$SCRAPED_DATA_DIR/$STATE"
IMPORT_LOCK_DIR="/tmp/ddp-openstates-import-locks/$STATE"
SWEEP_STAGING_DIR="/tmp/ddp-openstates-sweep-staging/$STATE"
SWEEP_INTERVAL_SECS="${SWEEP_INTERVAL_SECS:-120}"
LOCK_WAIT_TIMEOUT_SECS="${LOCK_WAIT_TIMEOUT_SECS:-180}"
IMPORT_LOCK_HELD=0

# mkdir is atomic — either it succeeds (we now own the lock) or it fails (someone else does).
#
# Records the holder's real PID via a direct `sh -c 'echo $PPID' > file` redirect — NOT
# `$BASHPID` (bash 4+ only; this fleet's bash is 3.2, verified: `echo $BASHPID` is empty) and
# NOT `$$` (verified empirically: inside a backgrounded function, bash 3.2's `$$` still reports
# the *top-level script's* PID, not the background job's own — it can't tell "the sweep loop
# holds this" from "the main script holds this"). Running `sh -c '...'` as a *direct* child
# (redirected straight to a file, not through `$(...)` — command substitution forks an extra
# subshell layer that changes whose PID `$PPID` reports) gets the calling process's own real
# PID correctly in either context; verified against `$!` in both the main script and a
# backgrounded function. This is what lets a stale lock left by a hard-killed process (SIGKILL,
# no trap runs) be detected and reclaimed, rather than blocking every future import for this
# $STATE forever.
acquire_import_lock() {
    if mkdir "$IMPORT_LOCK_DIR" 2>/dev/null; then
        sh -c 'echo $PPID' > "$IMPORT_LOCK_DIR/pid"
        IMPORT_LOCK_HELD=1
        return 0
    fi
    local holder; holder=$(cat "$IMPORT_LOCK_DIR/pid" 2>/dev/null)
    if [ -n "$holder" ] && ! kill -0 "$holder" 2>/dev/null; then
        log "Import lock for $STATE held by dead pid $holder — reclaiming"
        rm -rf "$IMPORT_LOCK_DIR"
        if mkdir "$IMPORT_LOCK_DIR" 2>/dev/null; then
            sh -c 'echo $PPID' > "$IMPORT_LOCK_DIR/pid"
            IMPORT_LOCK_HELD=1
            return 0
        fi
    fi
    return 1
}
release_import_lock() {
    [ "$IMPORT_LOCK_HELD" = "1" ] || return 0
    rm -rf "$IMPORT_LOCK_DIR"
    IMPORT_LOCK_HELD=0
}
# Best-effort — used by the periodic sweep. Returns 2 (distinct from the wrapped command's own
# exit code) when the lock is busy, which the caller treats as "try again next cycle," not a
# failure.
try_import_lock() {
    acquire_import_lock || return 2
    eval "$1"; local rc=$?
    release_import_lock
    return $rc
}
# Blocking — used by recovery/final import, which must never silently "succeed" by skipping.
# Waits up to LOCK_WAIT_TIMEOUT_SECS for the lock, then fails loudly (same as any other
# scrape/import failure — set -e + the ERR trap below catches a bare nonzero return from this).
require_import_lock() {
    local waited=0
    until acquire_import_lock; do
        if [ "$waited" -ge "$LOCK_WAIT_TIMEOUT_SECS" ]; then
            log "ERROR: timed out after ${LOCK_WAIT_TIMEOUT_SECS}s waiting for import lock for $STATE (held by pid $(cat "$IMPORT_LOCK_DIR/pid" 2>/dev/null))"
            return 1
        fi
        sleep 5; waited=$((waited + 5))
    done
    eval "$1"; local rc=$?
    release_import_lock
    return $rc
}

# Permanent bill-document archive (PLAN-bill-document-provenance.md, Phase 1). Gated per-
# jurisdiction via ARCHIVE_ENABLED_STATES (activate.sh) so a new jurisdiction's first-ever run
# (a full historical backfill, not an incremental update) only happens once explicitly enabled.
#
# Failure handling is explicit here, not left to the ambient `set -e` + `trap ... ERR` above.
# Found 2026-07-26: when this function is called from finish_no_op() (the incremental-no-op
# path), which is itself invoked from inside an `if [ "$rc" -ne 0 ]; then ... fi` block, a
# failing command inside archive_if_enabled() still halts the script via set -e (confirmed:
# nothing after the crash ever runs) but the ERR trap never fires -- a real bash quirk, verified
# with an isolated repro, not assumed. That's exactly the class of failure this alerting exists
# to catch, and it went completely unreported: no Slack message, no CAMS failure report, despite
# both tokens being configured. Explicit handling here doesn't depend on which branch called this
# function. Same single-fire discipline as the main scrape/import failure path below
# ("Alert once (disable the ERR trap so it can't double-fire)") -- this only ever runs once per
# invocation: os-text-extract archive dies on its first unhandled exception rather than looping
# through remaining bills (confirmed from the 2026-07-25/26 incident's traceback), and this
# function itself is only ever called once per script run (from finish_no_op() OR the main flow,
# never both).
archive_if_enabled() {
    case ",${ARCHIVE_ENABLED_STATES:-}," in
        *",$STATE,"*)
            log "Archiving bill documents: $STATE..."
            ARCHIVE_OUT=$(mktemp)
            $OS_TEXT_EXTRACT archive "$STATE" 2>&1 | tee "$ARCHIVE_OUT" >> "$LOG_DIR/scraper.log"
            archive_rc="${PIPESTATUS[0]}"  # tee's own exit code, not os-text-extract's, would mask a real failure
            if [ "$archive_rc" -ne 0 ]; then
                FAILURE_MESSAGE=$(grep -E '^[A-Za-z_][A-Za-z0-9_.]*(Error|Exception): ' "$ARCHIVE_OUT" 2>/dev/null | tail -1)
                FAILURE_ERROR_TYPE=$(echo "$FAILURE_MESSAGE" | grep -oE '^[A-Za-z_][A-Za-z0-9_.]*(Error|Exception)')
                FAILURE_ERROR_TYPE="${FAILURE_ERROR_TYPE:-ArchiveFailure}"
                FAILURE_MESSAGE="${FAILURE_MESSAGE:-bill-document archive failed for $STATE (see logs/scraper.log)}"
                rm -f "$ARCHIVE_OUT"
                trap - ERR  # alert once, can't double-fire
                on_failure
                exit 1
            fi
            rm -f "$ARCHIVE_OUT"
            log "Archiving done: $STATE."
            ;;
        *)
            : # not yet enabled for this jurisdiction
            ;;
    esac
}

if [ "$SWEEP_IMPORT_ENABLED" = "1" ]; then
    mkdir -p "$(dirname "$IMPORT_LOCK_DIR")"

    # Recover any un-imported JSON left behind by a previous run that never reached its own
    # import step — the --scrape call below wipes $STATE_DATADIR unconditionally
    # (openstates-core's do_scrape()), so anything sitting there now is the only copy of that
    # work. Blocks and alerts on failure rather than proceeding to the wipe underneath it — a
    # warn-and-continue here would defeat the point of recovering the data at all.
    if compgen -G "$STATE_DATADIR/bill_*.json" > /dev/null 2>&1; then
        log "Found un-imported JSON from a previous run in $STATE_DATADIR — importing before rescrape"
        if ! require_import_lock "\$OS_UPDATE $STATE --import $IMPORT_FLAGS $DIR_FLAGS >> \"$LOG_DIR/scraper.log\" 2>&1"; then
            FAILURE_MESSAGE="Recovery import failed for $STATE — refusing to rescrape (would wipe the only copy of this data)"
            trap - ERR
            on_failure
            exit 1
        fi
    fi
fi

# Marker file so we can count only files written by this scrape, not leftovers.
SCRAPE_MARKER=$(mktemp)

# First attempt: normal scrape.
# On failure, retry with --fastmode which reads previously fetched pages from
# _cache/ instead of re-hitting the legislature website. The cache persists
# across runs even when _data/{state}/ is wiped, so a mid-run interruption
# still benefits from whatever was fetched before the failure.
SCRAPE_OUT=$(mktemp)
scrape_attempt() {  # $1 = extra flags (e.g. --fastmode). Streams to scraper.log AND captures
                    # to SCRAPE_OUT; returns os-update's real exit code (not tee's).
    $OS_UPDATE "$STATE" --scrape bills $SESSION_ARG $INCREMENTAL_FLAG $1 $DIR_FLAGS 2>&1 \
        | tee "$SCRAPE_OUT" >> "$LOG_DIR/scraper.log"
    return "${PIPESTATUS[0]}"
}

# An incremental run that legitimately finds nothing changed since the cutoff makes
# os-update raise "no objects returned" and exit non-zero. That is a clean no-op, not a
# failure — record it and skip the import instead of firing the failure alert.
finish_no_op() {
    log "=== SCRAPE SUMMARY: $STATE ${SESSION_ARG} | mode=incremental | bills_scraped=0 | no changes since cutoff (no-op) ==="
    log "No new bills for $STATE ${SESSION_ARG} since cutoff; skipping import."

    # Still archive, even on a no-op scrape — the natural-key skip check is cheap to run
    # every time regardless of whether anything new was scraped, and this function used to
    # `exit 0` before ever reaching an archive step, which would otherwise skip archiving on
    # any night with zero new activity for a jurisdiction.
    archive_if_enabled

    mkdir -p "$LAST_RUN_DIR"
    date -u +%Y-%m-%dT%H:%M:%S > "$TS_FILE"
    echo "0:incremental" > "$COUNT_FILE"
    rm -f "$SCRAPE_OUT" "$SCRAPE_MARKER"
    exit 0
}

# FASTMODE_ONLY=1 skips the network attempt entirely and scrapes from the local
# cache only — for re-running a session that already has most pages cached from
# a prior run (e.g. one that died partway through on an unrelated bug).
FIRST_ATTEMPT_FLAGS=""
if [ "${FASTMODE_ONLY:-}" = "1" ]; then
    FIRST_ATTEMPT_FLAGS="--fastmode"
    log "FASTMODE_ONLY=1: starting with --fastmode (cache-only, no network)"
fi

# Periodic import sweep — imports scraped JSON into Postgres throughout the scrape instead of
# only once at the end, so a run that dies mid-scrape has already gotten most of its bills into
# Postgres via earlier sweeps rather than losing everything. Best-effort: a failed sweep just
# excludes the suspected file from staging for the rest of this run and retries next cycle —
# it never touches $STATE_DATADIR, so a wrong guess costs one extra retry, not a lost bill. A
# file that's genuinely bad gets a real attempt (and alerts) at the final import below, same as
# an unfixed bad file would fail a scrape today.
if [ "$SWEEP_IMPORT_ENABLED" = "1" ]; then
    sweep_import() {
        # Disable set -e and the inherited ERR trap for this backgrounded loop specifically —
        # verified empirically that a background job inherits both, so an incidental failure in
        # this loop's OWN bookkeeping (mkdir, cp, a vanished file between the existence check and
        # the stat) would otherwise kill the entire loop after its first occurrence, silently, for
        # the rest of a multi-hour run — not just fail one sweep cycle. The one call whose failure
        # actually matters ($OS_UPDATE via try_import_lock) is already explicitly captured via
        # `|| rc=$?` below, independent of this.
        set +e; trap - ERR

        # Comma-delimited basenames, not an associative array — this fleet's bash is 3.2
        # (verified: `declare -A` errors out with "invalid option"; associative arrays are a
        # bash 4+ feature). In-memory, this process's lifetime only.
        EXCLUDED_FROM_STAGING=","
        SWEEP_FAILURES=0
        while true; do
            sleep "$SWEEP_INTERVAL_SECS"
            [ -d "$STATE_DATADIR" ] || continue

            rm -rf "$SWEEP_STAGING_DIR"; mkdir -p "$SWEEP_STAGING_DIR/$STATE"
            local cutoff=$(( $(date +%s) - 5 ))  # skip files touched in the last 5s — cheap
                                                  # insurance against a bill file the scraper is
                                                  # still mid-write on (single open/dump/close,
                                                  # not write-then-rename)
            for f in "$STATE_DATADIR"/*.json; do
                [ -e "$f" ] || continue
                case "$EXCLUDED_FROM_STAGING" in *",$(basename "$f"),"*) continue ;; esac
                local mtime; mtime=$(stat -f %m "$f" 2>/dev/null || stat -c %Y "$f" 2>/dev/null)
                [ -n "$mtime" ] && [ "$mtime" -lt "$cutoff" ] && cp "$f" "$SWEEP_STAGING_DIR/$STATE/"
            done

            local rc=0
            try_import_lock "\$OS_UPDATE $STATE --import $IMPORT_FLAGS --datadir $SWEEP_STAGING_DIR --cachedir \$CACHE_DIR >> \"$LOG_DIR/scraper.log\" 2>&1" || rc=$?
            if [ "$rc" = 2 ]; then
                log "Import already in progress for $STATE — skipping this sweep cycle"
            elif [ "$rc" != 0 ]; then
                SWEEP_FAILURES=$((SWEEP_FAILURES + 1))
                local bad_staged; bad_staged=$(grep -oE "$SWEEP_STAGING_DIR/$STATE/[A-Za-z_]+_[0-9a-f-]+\.json" "$LOG_DIR/scraper.log" | tail -1)
                [ -n "$bad_staged" ] && EXCLUDED_FROM_STAGING="$EXCLUDED_FROM_STAGING$(basename "$bad_staged"),"
                log "WARNING: periodic import sweep failed for $STATE — excluding ${bad_staged:-unknown file} from staging until final import"
                # 3 in a row is a systemic problem (DB down, disk full), not one bad record —
                # escalate through the normal alert path rather than retrying silently forever.
                if [ "$SWEEP_FAILURES" -ge 3 ]; then
                    FAILURE_MESSAGE="3 consecutive periodic import sweeps failed for $STATE — possible systemic issue (DB down, disk full)"
                    on_failure
                    SWEEP_FAILURES=0
                fi
            else
                SWEEP_FAILURES=0
            fi
        done
    }
    sweep_import &
    SWEEP_PID=$!
    # Cleanup on exit is handled by the single EXIT trap set alongside READER_MARKER above.
fi

rc=0; scrape_attempt "$FIRST_ATTEMPT_FLAGS" || rc=$?
if [ "$rc" -ne 0 ] && [ "$FIRST_ATTEMPT_FLAGS" != "--fastmode" ]; then
    log "Scrape failed, retrying with --fastmode (using local cache)..."
    rc=0; scrape_attempt "--fastmode" || rc=$?
fi
if [ "$rc" -ne 0 ]; then
    # Benign: incremental run with nothing new since the cutoff.
    if [ "$MODE" = "incremental" ] && grep -q "no objects returned from" "$SCRAPE_OUT"; then
        finish_no_op
    fi
    # Genuine failure — pull the actual Python exception line out of the scrape
    # output (before it's removed below) so the CAMS report carries a real
    # error_type/message instead of the generic fallback in report_failure_to_cams.
    FAILURE_MESSAGE=$(grep -E '^[A-Za-z_][A-Za-z0-9_.]*(Error|Exception): ' "$SCRAPE_OUT" 2>/dev/null | tail -1)
    FAILURE_ERROR_TYPE=$(echo "$FAILURE_MESSAGE" | grep -oE '^[A-Za-z_][A-Za-z0-9_.]*(Error|Exception)')
    # Alert once (disable the ERR trap so it can't double-fire) and stop.
    rm -f "$SCRAPE_OUT" "$SCRAPE_MARKER"
    trap - ERR
    on_failure
    exit 1
fi
rm -f "$SCRAPE_OUT"

# Count bill JSON files written during this scrape (excludes leftovers from prior runs).
SCRAPED_BILLS=$(find "$SCRAPED_DATA_DIR/$STATE" -name "bill_*.json" -newer "$SCRAPE_MARKER" 2>/dev/null | wc -l | tr -d ' ')
rm -f "$SCRAPE_MARKER"

# Emit a clearly-visible summary line and warn on suspicious drops.
if [ -f "$COUNT_FILE" ]; then
    PREV_BILLS=$(cut -d: -f1 "$COUNT_FILE")
    PREV_MODE=$(cut -d: -f2 "$COUNT_FILE")
    log "=== SCRAPE SUMMARY: $STATE ${SESSION_ARG} | mode=$MODE | bills_scraped=$SCRAPED_BILLS | prev_run=${PREV_BILLS} (${PREV_MODE}) ==="
    # Warn if two consecutive incremental runs diverge by more than 80%.
    if [ "$MODE" = "incremental" ] && [ "$PREV_MODE" = "incremental" ] && [ "${PREV_BILLS:-0}" -gt 10 ]; then
        THRESHOLD=$(python3 -c "print(max(1, int($PREV_BILLS * 0.2)))")
        if [ "$SCRAPED_BILLS" -lt "$THRESHOLD" ]; then
            log "WARNING: bills_scraped ($SCRAPED_BILLS) is <20% of previous incremental run ($PREV_BILLS) — possible over-filtering for $STATE ${SESSION_ARG}"
        fi
    fi
else
    log "=== SCRAPE SUMMARY: $STATE ${SESSION_ARG} | mode=$MODE | bills_scraped=$SCRAPED_BILLS | prev_run=none (first run) ==="
fi

log "Scrape done: $STATE. Starting import..."

if [ "$SWEEP_IMPORT_ENABLED" = "1" ]; then
    # There's no writer left once scrape_attempt() has returned, so this reads $STATE_DATADIR
    # directly (no staging/age-filter needed — that's only for protecting against a concurrent
    # write, which can't happen here). Blocks (doesn't skip) if a sweep is still finishing its
    # own import; a lock-wait timeout or the import itself failing both hit the same
    # set -e + ERR trap -> on_failure path as any other import failure below.
    #
    # `|| true` on both: confirmed live (2026-07-30, FL 2026F test run) that `wait` on a job you
    # just `kill`ed reports that job's signal-terminated exit status (143, not 0) — under set -e,
    # that alone aborted the script right here, before require_import_lock ever ran, with no
    # actual import failure at all. The two-line difference between "cleanly stopped a background
    # loop" and "a real failure" matters: only require_import_lock's own result should ever
    # trigger on_failure below.
    kill "$SWEEP_PID" 2>/dev/null || true; wait "$SWEEP_PID" 2>/dev/null || true
    require_import_lock "\$OS_UPDATE $STATE --import $IMPORT_FLAGS $DIR_FLAGS >> \"$LOG_DIR/scraper.log\" 2>&1"
else
    $OS_UPDATE "$STATE" --import $IMPORT_FLAGS $DIR_FLAGS \
        >> "$LOG_DIR/scraper.log" 2>&1
fi

log "Import done: $STATE."

# Permanently archive every not-yet-captured bill version + document (PLAN-bill-document-
# provenance.md, Phase 1). Runs across the whole jurisdiction, not scoped to $SESSION_ARG — the
# natural-key skip check makes already-archived versions a cheap DB check, not a re-fetch. A
# failure here is treated the same as a scrape/import failure by the `trap ERR` above.
archive_if_enabled

mkdir -p "$LAST_RUN_DIR"
date -u +%Y-%m-%dT%H:%M:%S > "$TS_FILE"
echo "${SCRAPED_BILLS}:${MODE}" > "$COUNT_FILE"
