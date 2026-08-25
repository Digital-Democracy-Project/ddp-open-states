#!/usr/bin/env bash
# Usage: run-scrape.sh <state> [session=XXXX]
set -e

STATE=$1
SESSION_ARG=${2:-""}
LOG_DIR="${LOG_DIR:-/Users/agentsmith/Developer/repos/ddp-open-states/logs}"
OS_UPDATE="${OS_UPDATE:-/Users/agentsmith/Developer/repos/ddp-open-states/.venv/bin/os-update}"

# OPEN-152: remember any caller-supplied overrides before `source activate.sh` below, which
# unconditionally `export`s OS_UPDATE, SCRAPED_DATA_DIR and CACHE_DIR and would otherwise
# silently discard them. Restored immediately after that source.
#
# This exists so the no-op-versus-unreachable decision can be tested against a stub instead of
# only reasoned about — and the need is not hypothetical. Writing that test is what revealed
# this shadowing at all: the first attempt set OS_UPDATE, watched activate.sh overwrite it, and
# ran a real Virginia scrape against the live site. An untestable script is how this file
# accumulated three separate silent-failure bugs (OPEN-152, OPEN-154, OPEN-155).
#
# Production sets none of these, so `${VAR:-}` is empty and nothing is restored: behaviour is
# byte-for-byte what it was.
_OVERRIDE_OS_UPDATE="${OS_UPDATE_OVERRIDE:-}"
_OVERRIDE_DATA_DIR="${SCRAPED_DATA_DIR_OVERRIDE:-}"
_OVERRIDE_CACHE_DIR="${CACHE_DIR_OVERRIDE:-}"

# OPEN-139: import-report parsing and the stuck-run detector. Sourced from this script's own
# directory rather than an absolute path so a worktree/checkout runs its own copy, not the deploy
# checkout's. Hard failure if absent, deliberately: the alternative is a run that silently stops
# recording filing activity, which is the exact class of silence this ticket exists to remove.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=import-summary.sh
. "$SCRIPT_DIR/import-summary.sh"

LAST_RUN_DIR="$LOG_DIR/last-run"
SCRAPE_KEY=$(echo "${STATE}${SESSION_ARG:+ $SESSION_ARG}" | tr ' =' '__')
TS_FILE="$LAST_RUN_DIR/${SCRAPE_KEY}.ts"
COUNT_FILE="$LAST_RUN_DIR/${SCRAPE_KEY}.count"
# OPEN-139: how many bills the IMPORT actually treated as new/changed, as opposed to how many
# JSON files the scrape wrote (.count above). These are not the same number and the difference
# is the whole point: AZ ran 14 days dead writing 895 files a night while the import reported
# "0 new 0 updated 895 noop" every time. The file count said healthy; only the import knew.
# Format: new:updated:noop:mode
IMPORTED_FILE="$LAST_RUN_DIR/${SCRAPE_KEY}.imported"

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

# OPEN-152: restore the caller's overrides, which activate.sh has just clobbered. Empty in
# production, so this is a no-op there. See the block near the top for why it exists.
[ -n "$_OVERRIDE_OS_UPDATE" ] && OS_UPDATE="$_OVERRIDE_OS_UPDATE"
[ -n "$_OVERRIDE_DATA_DIR" ] && export SCRAPED_DATA_DIR="$_OVERRIDE_DATA_DIR"
[ -n "$_OVERRIDE_CACHE_DIR" ] && export CACHE_DIR="$_OVERRIDE_CACHE_DIR"

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

# Exit code meaning "this failed, and retrying it would make things worse rather than better."
# run-scrape-retrying.sh (OPEN-87) checks for exactly this code and stops instead of retrying.
# Deliberately not 1 or 2: this script runs under `set -e` with an ERR trap, so an unclassified
# failure exits with whatever code the failing command returned, and the low codes are the ones
# that collide with that.
EXIT_DO_NOT_RETRY=90

on_failure() {
    log "ERROR: scrape/import failed for $STATE"
    # OPEN-87: the one suppression guard for run-scrape-retrying.sh. That wrapper may invoke
    # this script up to N times for a single logical failure, and without this each attempt
    # would fire its own Slack + CAMS alert — so a transient blip that recovered on attempt 2
    # would still page someone twice about a run that ultimately succeeded. The wrapper sets
    # this on every attempt but the last, and leaves it off for the last, so exactly one alert
    # fires and only once the failure is actually final.
    #
    # It suppresses the *alert*, not the failure. This function is reached both directly and via
    # the ERR trap under `set -e`; returning 0 here changes nothing about that. The failing
    # command's non-zero status still propagates, the script still exits non-zero, and the
    # wrapper still sees the failure and decides what to do with it. Detection is untouched —
    # the only thing skipped is telling a human about a failure that isn't final yet.
    if [ "${SUPPRESS_FAILURE_ALERT:-0}" = "1" ]; then
        log "SUPPRESS_FAILURE_ALERT=1 — skipping Slack/CAMS alert (retry wrapper will alert if attempts are exhausted)"
        return 0
    fi
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
# MA has it too (OPEN-55, confirmed 2026-08-09 via DuplicateItemError on H 5280
# during OPEN-42's session=194th full backfill) — MA rarely gets a full,
# non-incremental scrape, which is why it took until then to surface.
# --allow_duplicates keeps the first instance and silently skips the rest.
# See: https://github.com/openstates/openstates-scrapers/issues/5697
#
# Flat comma list rather than a chained conditional, per OPEN-124's rule (see PRIMITIVES.md,
# "Per-jurisdiction configuration"). Not cosmetic: the chained form had been extended four times
# and `ma` was silently missing until OPEN-55, which cost a completed 9,496-bill MA scrape its
# entire import. A one-line list can be checked at a glance; a four-term chain can't.
#
# Same list-plus-comma-wrapped-`case` pattern as ARCHIVE_ENABLED_STATES — defined in activate.sh:55,
# consumed at run-archive.sh:77 — so this repo has one matching style, not two.
#
# `case` returns 0 when nothing matches, so unlike a naive `if` rewrite this cannot trip `set -e`
# and the ERR trap, which would turn every non-listed jurisdiction's scrape into a spurious
# failure alert. (The old AND-OR form was safe too, but only incidentally.)
#
# Substring matching means a $STATE that is itself a comma-joined list ("mi,fl") matches, where the
# chained form did not. $STATE is $1, one jurisdiction abbreviation from ddp-sync, so that cannot
# occur; run-archive.sh has the same property. Noted, not guarded.
ALLOW_DUPLICATES_STATES="mi,fl,va,ma"
IMPORT_FLAGS=""
case ",$ALLOW_DUPLICATES_STATES," in
    *",$STATE,"*) IMPORT_FLAGS="--allow_duplicates" ;;
esac

# OPEN-50: ten jurisdictions (ct ia ks ma md mn nm or pr tx) register a SEPARATE `votes`
# scraper that has to be asked for by name; everywhere else votes are yielded from inside
# `bills`. Until now this script only ever ran `--scrape bills`, so onboarding one of those
# ten would have looked completely successful and silently produced no vote data.
#
# Ask the scraper what it registers rather than keeping a list of states here. A list would
# have to be hand-maintained across all 50 states, and the --allow_duplicates list directly
# above is the cautionary tale: `ma` was missing from it until OPEN-55, which cost a
# completed 9,496-bill backfill its entire import.
#
# This probe is load-bearing, not an optimisation: do_update() raises
# CommandError("no such scraper: ...") and fails the whole run if `votes` is requested for a
# jurisdiction that doesn't have one, so "just always pass votes" would break every
# currently-tracked state.
#
# stderr is captured to a separate file, NOT merged into the value: importing a jurisdiction
# emits FutureWarnings and a DEBUG line, and folding those into $VOTES_SCRAPER would splice
# several lines of warning text onto the os-update command line as positional arguments.
VOTES_SCRAPER=""
VOTES_PROBE_ERR=$(mktemp)
if ! VOTES_SCRAPER=$("$OS_VENV/bin/python" - "$STATE" 2>"$VOTES_PROBE_ERR" <<'PY'
import sys
from openstates.cli.update import get_jurisdiction
juris, _ = get_jurisdiction(sys.argv[1])
print("votes" if "votes" in juris.scrapers else "", end="")
PY
); then
    # Fail loudly rather than falling back to bills-only. A probe failure means we don't know
    # whether this jurisdiction's votes are being collected, which is the exact blind spot
    # OPEN-50 exists to close — silently guessing "no" would recreate it.
    PROBE_TAIL=$(tail -3 "$VOTES_PROBE_ERR" | tr '\n' ' ')
    rm -f "$VOTES_PROBE_ERR"
    log "ERROR: could not determine which scrapers $STATE registers: $PROBE_TAIL"
    FAILURE_ERROR_TYPE="ScraperProbeFailure"
    FAILURE_MESSAGE="could not import jurisdiction $STATE to check for a votes scraper: $PROBE_TAIL"
    trap - ERR
    on_failure
    exit 1
fi
rm -f "$VOTES_PROBE_ERR"
# Only "" or "votes" is a valid answer. Anything else means something wrote to stdout during
# the import, and $VOTES_SCRAPER is deliberately unquoted at the call site (it has to expand to
# either one word or none), so stray output would be word-split into extra positional args for
# os-update. Fail rather than guess — the stderr-merge bug this replaced was exactly this shape.
if [ -n "$VOTES_SCRAPER" ] && [ "$VOTES_SCRAPER" != "votes" ]; then
    log "ERROR: unexpected scraper-probe output for $STATE: '$VOTES_SCRAPER'"
    FAILURE_ERROR_TYPE="ScraperProbeFailure"
    FAILURE_MESSAGE="scraper probe for $STATE returned unexpected output: '$VOTES_SCRAPER'"
    trap - ERR
    on_failure
    exit 1
fi
[ -n "$VOTES_SCRAPER" ] && log "$STATE registers a separate votes scraper; scraping bills and votes"

# Import-as-you-go (PLAN-incremental-scraping.md, "Reopened 2026-07-30", approved for
# implementation) — off by default. When enabled, a killed scrape no longer loses everything:
# a periodic sweep imports scraped JSON into Postgres throughout the run instead of in one
# all-or-nothing transaction at the very end, and a pre-scrape recovery import saves any
# un-imported JSON from a previous interrupted run before --scrape wipes it. Roll out per
# jurisdiction (canary on VA/UT first) via SWEEP_IMPORT_ENABLED=1 in the calling environment.
SWEEP_IMPORT_ENABLED="${SWEEP_IMPORT_ENABLED:-0}"
STATE_DATADIR="$SCRAPED_DATA_DIR/$STATE"
# Keyed by $SCRAPE_KEY (state+session+chamber, same key the .ts/.count markers already use),
# NOT bare $STATE. Found live 2026-07-31: USA lower and upper both have STATE=usa, so a
# lock/staging path keyed on $STATE alone is shared between them -- one sweep cycle's
# `rm -rf "$SWEEP_STAGING_DIR"` deleted the staging dir out from under the other's concurrent
# read (FileNotFoundError), and both competed for the same import lock. Handled gracefully at
# the time (the excluded-from-staging retry logic caught it, nothing crashed or was lost), but
# the fix is to not let unrelated invocations share a path at all. $STATE_DATADIR itself stays
# keyed by bare $STATE on purpose -- that's openstates-core's own directory (do_scrape()/
# do_import() resolve it from args.module, which is always the bare state), not something this
# script can namespace further; lower/upper genuinely do share that one, which is exactly why
# production runs them sequentially rather than concurrently.
IMPORT_LOCK_DIR="/tmp/ddp-openstates-import-locks/$SCRAPE_KEY"
SWEEP_STAGING_DIR="/tmp/ddp-openstates-sweep-staging/$SCRAPE_KEY"
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

# Bill-document archiving used to run here, at the end of every scrape, gating the .ts/.count
# marker write below on the archive step finishing too (PLAN-bill-document-provenance.md, Phase
# 1). Split out to run-archive.sh (2026-07-31) — see PLAN-open-states.md's incremental-scraping
# section for why: archiving to DDP-HOT is slower and less reliable than scrape+import, and
# coupling the incremental cutoff to it created a compounding failure mode. A run whose archive
# step ran long or died left the cutoff stuck at its old value; the next run then had to treat
# more bills as "changed since cutoff," making that run slower too, more likely to also miss its
# archive window, and so on — observed live: a WA run still archiving 1h45m+ after scrape+import
# had already finished cleanly. The scraper and the archiver are now fully independent processes
# with independent schedules; this script no longer touches archiving at all.

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
# OPEN-139: the import's stdout/stderr, captured per run so its bill counts can be read without
# racing the other jurisdictions writing into the shared scraper.log. Removed on every exit path
# that can be reached after this point -- note on_failure() only alerts, it does not clean up, so
# each early-exit site removes its own temp files explicitly (same convention as SCRAPE_OUT).
IMPORT_OUT=$(mktemp)
scrape_attempt() {  # $1 = extra flags (e.g. --fastmode). Streams to scraper.log AND captures
                    # to SCRAPE_OUT; returns os-update's real exit code (not tee's).
    # $VOTES_SCRAPER is "votes" or empty (see OPEN-50 probe above). Its position here is
    # load-bearing and must stay AFTER $SESSION_ARG/$INCREMENTAL_FLAG: do_update() walks the
    # positional args left to right and attaches each k=v to the most recently named scraper
    # (openstates-core/openstates/cli/update.py:390-403). Moving `votes` before them would
    # hand `session=`/`start=` to the votes scraper — which accepts no `start=` at all — and
    # would simultaneously strip the incremental cutoff off `bills`, turning every run into a
    # full scrape. Both failures are silent.
    $OS_UPDATE "$STATE" --scrape bills $SESSION_ARG $INCREMENTAL_FLAG $VOTES_SCRAPER $1 $DIR_FLAGS 2>&1 \
        | tee "$SCRAPE_OUT" >> "$LOG_DIR/scraper.log"
    return "${PIPESTATUS[0]}"
}

# An incremental run that legitimately finds nothing changed since the cutoff makes
# os-update raise "no objects returned" and exit non-zero. That is a clean no-op, not a
# failure — record it and skip the import instead of firing the failure alert.
#
# The `exit 0` below is load-bearing for run-scrape-retrying.sh (OPEN-87): a no-op must look
# like success to the wrapper, or every no-op run would burn all its retry attempts and all
# the backoff between them on a guaranteed-identical result. Note that a scraper raising
# EmptyScrape explicitly (OPEN-106's change to UT) does NOT come through here at all —
# openstates-core catches EmptyScrape in do_scrape() and returns normally, so os-update exits
# 0 and this script runs a zero-bill import and exits 0 on the happy path. Both no-op shapes
# end at exit 0; only one of them is this function.
finish_no_op() {
    log "=== SCRAPE SUMMARY: $STATE ${SESSION_ARG} | mode=incremental | bills_scraped=0 | no changes since cutoff (no-op) ==="
    log "No new bills for $STATE ${SESSION_ARG} since cutoff; skipping import."

    mkdir -p "$LAST_RUN_DIR"
    date -u +%Y-%m-%dT%H:%M:%S > "$TS_FILE"
    echo "0:incremental" > "$COUNT_FILE"
    # OPEN-139: no import ran because nothing changed since the cutoff, so genuinely zero new
    # bills — an `ok` measurement of zero, not a failure to measure. Recorded rather than skipped
    # so the series has no holes; see import-summary.sh for the file's format and guarantees.
    echo "ok:0:0:0:incremental" > "$IMPORTED_FILE"
    rm -f "$SCRAPE_OUT" "$SCRAPE_MARKER" "$IMPORT_OUT"
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
    #
    # OPEN-152: "no objects returned" is necessary but NOT sufficient for that conclusion.
    # openstates-core raises it whenever a scraper yields nothing, which covers both "nothing
    # changed" and "I could not read the site". Taking the no-op path for the second case is
    # what let a WAF-blocked MI run record `ok:0:0:0` on 2026-08-24 -- and, worse, advance
    # $TS_FILE past a window whose bills were never examined, so no later incremental run would
    # revisit it. Ask the scrape's own output which case this is before deciding.
    if [ "$MODE" = "incremental" ] && grep -q "no objects returned from" "$SCRAPE_OUT"; then
        if scrape_output_shows_unreachable_site "$SCRAPE_OUT"; then
            # Fall through to the failure path below deliberately. That path alerts via
            # on_failure(), classifies a WAF block as terminal, and -- the point of this
            # ticket -- writes neither the watermark nor the `.imported` marker, so the window
            # stays eligible for the next run instead of being silently skipped.
            log "$STATE ${SESSION_ARG} returned no objects AND its output indicates the site could not be read — treating as a failure, not a no-op (OPEN-152). The watermark will NOT advance."
        else
            finish_no_op
        fi
    fi
    # Genuine failure — pull the actual Python exception line out of the scrape
    # output (before it's removed below) so the CAMS report carries a real
    # error_type/message instead of the generic fallback in report_failure_to_cams.
    FAILURE_MESSAGE=$(grep -E '^[A-Za-z_][A-Za-z0-9_.]*(Error|Exception): ' "$SCRAPE_OUT" 2>/dev/null | tail -1)
    FAILURE_ERROR_TYPE=$(echo "$FAILURE_MESSAGE" | grep -oE '^[A-Za-z_][A-Za-z0-9_.]*(Error|Exception)')
    # OPEN-87: is this a WAF block? If so it is terminal, because OPEN-53 established that a
    # blind retry against a WAF worsens the block rather than recovering from it — each attempt
    # is more traffic from an already-suspect client.
    #
    # This check belongs here specifically, and nowhere else. $SCRAPE_OUT is the *only* place
    # the WAF marker is visible: MI's circuit breaker raises it into the scrape's own output,
    # which this script tees into scraper.log. ddp-sync's classify_failure_reason() sees only
    # the external stderr tail, which is why its own comment records that a real MI WAF block
    # always misclassified as nonzero_exit_other and its reactive fallback never once fired.
    # Classifying at the one point that can actually see the text avoids repeating that.
    #
    # Marker text matches scrapers/mi/_waf_circuit_breaker.py ("WAF block detected even after
    # cookie re-warm ... consecutive blocks: N"). It is duplicated from ddp-sync's
    # WAF_BLOCK_MARKERS rather than shared, because the two live in different repos and
    # languages; called out in the PR so the operator can decide whether that's worth fixing.
    SCRAPE_EXIT_CODE=1
    if grep -qiE 'waf block detected|consecutive waf blocks' "$SCRAPE_OUT" 2>/dev/null; then
        log "Failure for $STATE classified as a WAF block — terminal, will not be retried (OPEN-53)"
        SCRAPE_EXIT_CODE=$EXIT_DO_NOT_RETRY
        # Positively signal the classification, rather than leaving the wrapper to infer it from
        # the exit code alone. The exit code cannot carry this safely: every *other* failure path
        # in this script exits with whatever code the failing command returned (set -e + ERR
        # trap), so if any of them ever returned 90 by coincidence, a wrapper trusting the code
        # would stop retrying AND assume this script had alerted — while suppression meant it
        # hadn't. That is a silent failure, and it is worse than the duplicate alert it would be
        # trying to avoid. The flag is only ever written here, in the one branch that deliberately
        # makes this decision, so "flag present" cannot happen by accident.
        #
        # The wrapper owns the file's whole lifecycle (it picks the path, clears it before every
        # attempt, and deletes it on exit), so there is no staleness or cleanup problem here and
        # no key to collide on. Absent when run-scrape.sh is invoked directly, which is why this
        # is guarded rather than unconditional.
        [ -n "${DO_NOT_RETRY_FLAG:-}" ] && : > "$DO_NOT_RETRY_FLAG"
        # Alert even under a retry wrapper: suppression exists so intermediate failures stay
        # quiet until a *final* attempt alerts, and this failure is already final. Leaving it
        # suppressed would make a WAF block the one failure class that silently never alerts.
        SUPPRESS_FAILURE_ALERT=0
    fi
    # Alert once (disable the ERR trap so it can't double-fire) and stop.
    rm -f "$SCRAPE_OUT" "$SCRAPE_MARKER" "$IMPORT_OUT"
    trap - ERR
    on_failure
    exit "$SCRAPE_EXIT_CODE"
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
    # OPEN-139 removed the <20%-of-previous-run warning that used to sit here. It compared this
    # run's bills_scraped against the last run's, and it could not have caught the failure it was
    # meant to catch: AZ scraped 895 files a night for 14 nights, so every comparison was 895 vs
    # 895 -- a flat line, no drop, no warning, while the import was reporting 0 new 0 updated the
    # whole time. Two problems with the number itself, not the threshold:
    #
    #   * bills_scraped counts JSON files written, which includes re-writing bills that haven't
    #     changed. A stuck cutoff therefore reads as perfectly healthy.
    #   * this block runs BEFORE the import, so the only figure available here is the one that
    #     cannot distinguish new work from repeated work.
    #
    # The replacement lives after the import, keyed on the count of genuinely new bills, and
    # explicitly flags the scraped-files>0 / new+updated=0 shape AZ was stuck in. Deliberately
    # not reimplemented here as well -- one check, in the one place that can see the real number.
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
    require_import_lock "\$OS_UPDATE $STATE --import $IMPORT_FLAGS $DIR_FLAGS > \"$IMPORT_OUT\" 2>&1" \
        || IMPORT_RC=$?
else
    $OS_UPDATE "$STATE" --import $IMPORT_FLAGS $DIR_FLAGS \
        > "$IMPORT_OUT" 2>&1 || IMPORT_RC=$?
fi

# OPEN-139: the import's own output lands in a per-run file first, then gets appended to
# scraper.log verbatim. Two reasons it is not read back out of scraper.log instead:
#
#   1. scraper.log is shared. The secondary job fans its five jurisdictions out with
#      asyncio.gather (confirmed live 2026-08-22: VA and UT both started at 22:00:00), so
#      several imports interleave their lines into the same file. Any offset- or tail-based
#      read of that shared log would attribute another jurisdiction's counts to this one.
#   2. A redirect keeps the import's real exit status intact. Piping to `tee` would make $? the
#      status of tee, and inside require_import_lock's `eval` there is no clean place to recover
#      ${PIPESTATUS[0]} -- see scrape_attempt() above, which needs exactly that dance.
#
# `|| IMPORT_RC=$?` on both branches is load-bearing, and is why the failure handling below is
# written out by hand instead of left to the ERR trap. A failing command inside an AND-OR list is
# exempt from `set -e`, so the append below always runs -- pm-review caught that the first version
# of this change lost the import's stderr from scraper.log on exactly the runs that need it, since
# `set -e` aborted before reaching the append and the failure alert says "check scraper.log".
# Confirmed by reproducing it: with a bare redirect, a non-zero import never reaches this line.
#
# Tradeoff, stated plainly: the import's output no longer streams into scraper.log while it
# runs, it appears when the import finishes. Imports are the short half of a run (AZ's 895-bill
# import took 32s on 2026-08-22 against a 95-minute scrape), so this costs little visibility.
cat "$IMPORT_OUT" >> "$LOG_DIR/scraper.log"

if [ "${IMPORT_RC:-0}" -ne 0 ]; then
    # Same shape as the scrape-failure path above: disable the ERR trap so it cannot double-fire,
    # alert once, and exit with the import's real status.
    rm -f "$IMPORT_OUT"
    trap - ERR
    on_failure
    exit "$IMPORT_RC"
fi

log "Import done: $STATE."

# OPEN-139: read the PREVIOUS run's new-bill count before this run's marker overwrites it. See
# import-summary.sh for the .imported file's format and its three guarantees.
PREV_NEW=""
PREV_IMPORTED_MODE=""
if [ -f "$IMPORTED_FILE" ]; then
    if [ "$(cut -d: -f1 "$IMPORTED_FILE")" = "ok" ]; then
        PREV_NEW=$(cut -d: -f2 "$IMPORTED_FILE")
        PREV_IMPORTED_MODE=$(cut -d: -f5 "$IMPORTED_FILE")
    fi
fi

IMPORT_COUNTS=$(parse_import_bill_counts "$IMPORT_OUT")
rm -f "$IMPORT_OUT"

mkdir -p "$LAST_RUN_DIR"
if [ -n "$IMPORT_COUNTS" ]; then
    NEW_BILLS=$(echo "$IMPORT_COUNTS" | cut -d: -f1)
    UPDATED_BILLS=$(echo "$IMPORT_COUNTS" | cut -d: -f2)
    NOOP_BILLS=$(echo "$IMPORT_COUNTS" | cut -d: -f3)
    log "=== IMPORT SUMMARY: $STATE ${SESSION_ARG} | mode=$MODE | bills_new=$NEW_BILLS | bills_updated=$UPDATED_BILLS | bills_noop=$NOOP_BILLS ==="
    echo "ok:${IMPORT_COUNTS}:${MODE}" > "$IMPORTED_FILE"

    if import_looks_stuck "$MODE" "${SCRAPED_BILLS:-0}" "$NEW_BILLS" "$UPDATED_BILLS"; then
        log "WARNING: $STATE ${SESSION_ARG} scraped $SCRAPED_BILLS bill files but the import found 0 new and 0 updated — the incremental cutoff is probably stuck re-scraping one frozen window (OPEN-139)"
    fi

    # The rewired replacement for the <20%-of-previous warning removed above, now comparing the
    # count that can actually see a collapse.
    if [ -n "$PREV_NEW" ] && new_bills_collapsed "$MODE" "$PREV_IMPORTED_MODE" "$PREV_NEW" "$NEW_BILLS"; then
        log "WARNING: $STATE ${SESSION_ARG} imported $NEW_BILLS new bills, under 20% of the previous incremental run's $PREV_NEW — possible over-filtering or a broken change signal (OPEN-139)"
    fi
else
    # Written, not skipped. Leaving the previous run's counts in place would make a stale figure
    # look current to anything building a series from this file, and a fabricated 0 would make a
    # measurement failure look like a quiet week. Neither is acceptable; `unparsed` says which.
    log "WARNING: could not parse an import bill-count line for $STATE ${SESSION_ARG} — recording this run as unmeasured (OPEN-139)"
    echo "unparsed::::${MODE}" > "$IMPORTED_FILE"
fi

date -u +%Y-%m-%dT%H:%M:%S > "$TS_FILE"
echo "${SCRAPED_BILLS}:${MODE}" > "$COUNT_FILE"
