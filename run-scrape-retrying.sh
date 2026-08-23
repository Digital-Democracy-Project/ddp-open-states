#!/usr/bin/env bash
# Usage: run-scrape-retrying.sh <state> [session=XXXX]
#
# OPEN-87. A thin bounded-retry wrapper around run-scrape.sh. It adds nothing to a scrape
# except this: if a whole run fails for a reason that might not fail again, run it again, a
# fixed number of times, with a backoff in between -- and alert only once, at the end.
#
# WHY THIS EXISTS WHEN THREE RETRY LAYERS ALREADY DO (this is the fourth, so it has to justify
# itself). The three that already exist all retry *inside* a single run:
#
#   1. run-scrape.sh:363-366 -- one internal `--fastmode` retry per run. Re-reads pages from
#      the local cache instead of the network. It cannot help when the *cache* is the thing
#      that's incomplete, which is exactly the case after a network failure partway through.
#   2. ddp-sync's `should_escalate` (pipelines/openstates_scrape.py) -- does not retry at all.
#      It *notices* that a jurisdiction has been WAF-blocked in N of the last M weekly runs and
#      alerts about the pattern. Detection and escalation, not recovery.
#   3. OPEN-106's UA retry-with-backoff inside UT's `get_session_list()` -- retries one HTTP
#      request. Scoped to one call in one scraper.
#
# None of them can recover from a failure that kills the whole run and whose cause is gone
# minutes later. That is the case this layer is for, and the concrete incident is MA on
# 2026-08-01: a network timeout took down a run that would have succeeded on a re-run. Today
# that costs a week, because these are weekly jobs -- the next attempt is the next scheduled
# run. This wrapper makes the next attempt happen in minutes instead.
#
# WHAT IT MUST NOT RETRY, and why each one is a real incident rather than a hypothetical:
#
#   * A no-op. An incremental run that legitimately finds nothing new is a *success*, and
#     retrying it burns every attempt plus all the backoff on a guaranteed-identical result.
#     Both no-op paths already exit 0, verified against source rather than assumed:
#       - Scraper yields nothing and does not raise EmptyScrape -> openstates-core raises
#         ScrapeError("no objects returned from ...") -> run-scrape.sh's finish_no_op() catches
#         it and `exit 0` (run-scrape.sh:278-287, 370-372).
#       - Scraper raises EmptyScrape explicitly -- which is what OPEN-106 added to UT's
#         bills.py -- and openstates-core's do_scrape() *catches* it, warns "continuing without
#         any results", and returns normally (openstates-core/openstates/scrape/base.py:354-361).
#         os-update exits 0, so run-scrape.sh proceeds to a zero-bill import and exits 0.
#     So "don't retry an EmptyScrape" needs no special case here: exit 0 is success and success
#     is not retried. It needed *checking*, though, because the naive assumption (EmptyScrape
#     is an exception, so it must be a non-zero exit) is wrong.
#
#   * A WAF block. OPEN-53's finding is that a blind retry against a WAF makes a block worse
#     rather than recovering from it -- each attempt is more traffic from an already-suspect
#     client. run-scrape.sh classifies this and signals it via DO_NOT_RETRY_FLAG (see below);
#     it also exits 90, but the flag is what this wrapper decides on. The primary guard is that
#     MI, the jurisdiction this actually happens to, is not opted in at all (ddp-sync's
#     `retry.jurisdictions_excluded`). The flag is the backstop for a WAF block somewhere we
#     didn't expect one.
#
# WHICH JURISDICTIONS GET THIS is not decided here. ddp-sync decides, from
# `openstates_scrape.retry` in config/sync_schedule.yaml, and invokes this script instead of
# run-scrape.sh for the ones opted in (see _retry_eligible() there). There is deliberately no
# `[ "$STATE" = "mi" ]` test in this file -- per-jurisdiction policy lives in that YAML, which
# is where ddp-sync already resolves scrapebot_fallback and OPEN-86's sweep_import from
# (OPEN-124). SCRAPE_RETRY_EXCLUDED_JURISDICTIONS below is the *mechanism* for that policy, not
# the policy; it defaults to empty and ddp-sync fills it in.
#
# ALERTING. run-scrape.sh alerts Slack + CAMS from on_failure() on any failure. Three wrapped
# attempts would therefore fire three alerts for one logical failure. So this script sets
# SUPPRESS_FAILURE_ALERT=1 on every attempt except the last, and leaves it unset on the last --
# so run-scrape.sh itself does the alerting, exactly once, at the point where the failure has
# actually become final. No alerting logic is duplicated here. The one exception is handled
# inside run-scrape.sh: a do-not-retry classification un-suppresses itself, because the wrapper
# is not going to give it a final un-suppressed attempt.
#
# NOT IMPLEMENTED, ON PURPOSE: there is no total time budget (the design's old
# RETRY_TOTAL_BUDGET_SECS). ddp-sync applies SCRAPE_TIMEOUT_S to the whole invocation, i.e. to
# this wrapper and all of its attempts together, so this wrapper can be killed mid-attempt
# regardless of any budget it kept for itself. A budget here would look like a guard while
# guarding nothing. See the PR for the open question.

set -u

STATE="${1:-}"
SESSION_ARG="${2:-}"
if [ -z "$STATE" ]; then
    echo "usage: run-scrape-retrying.sh <state> [session=XXXX]" >&2
    exit 64
fi

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
# Overridable so the decision logic can be exercised against a stub that returns controlled
# exit codes, without running a real scrape. Defaults to the run-scrape.sh sitting next to it.
RUN_SCRAPE="${RUN_SCRAPE:-$SCRIPT_DIR/run-scrape.sh}"
LOG_DIR="${LOG_DIR:-$SCRIPT_DIR/logs}"

# run-scrape.sh's exit code for a do-not-retry failure. Recorded here for readers, but NOT what
# this wrapper decides on -- see DO_NOT_RETRY_FLAG below. It is propagated as this wrapper's own
# exit code when it happens, so the distinction is still visible to ddp-sync and in the logs.
EXIT_DO_NOT_RETRY=90

SCRAPE_RETRY_MAX_ATTEMPTS="${SCRAPE_RETRY_MAX_ATTEMPTS:-3}"
# Seconds to wait before each *re*try, comma-separated: the Nth value is used before attempt
# N+1, and the last value repeats if there are more retries than values. One mechanism
# expresses both candidate shapes -- "900,900" is fixed 15m, "900,1800,3600" is growing
# 15/30/60 -- so the choice is a config edit, not a code change.
#
# PLACEHOLDER VALUE. 3 attempts with 900,1800 covers a 45-minute window. The MA failure this
# wrapper exists to catch only manifested after roughly five hours, so this default would not
# have caught it. That is a real open question about the *shape* (how many attempts, spaced how
# widely), not a formatting preference, and it is flagged for decision in the PR rather than
# quietly settled here.
SCRAPE_RETRY_BACKOFF_SECS="${SCRAPE_RETRY_BACKOFF_SECS:-900,1800}"
# Comma-separated jurisdictions that must never be retried. Empty by default; ddp-sync supplies
# it from sync_schedule.yaml. See the header on why there is no hardcoded state name here.
SCRAPE_RETRY_EXCLUDED_JURISDICTIONS="${SCRAPE_RETRY_EXCLUDED_JURISDICTIONS:-}"

# How run-scrape.sh tells us "do not retry this one". A file, not the exit code: every failure
# path in run-scrape.sh other than the deliberate classification exits with whatever code the
# failing command returned (set -e + ERR trap), so an exit code can be produced by accident. If
# that ever collided with the do-not-retry code, this wrapper would stop retrying AND assume
# run-scrape.sh had alerted -- while suppression meant it hadn't. A silent failure, and worse
# than the duplicate alert it would be avoiding. run-scrape.sh writes this file only inside the
# one branch that deliberately makes the decision, so "present" cannot happen by coincidence.
#
# We own the whole lifecycle: we pick the path, clear it before every attempt, and remove it on
# exit. So there is no staleness, no cleanup left to anyone else, and no shared key to collide
# on between concurrent jurisdictions.
DO_NOT_RETRY_FLAG="${TMPDIR:-/tmp}/ddp-openstates-do-not-retry.$$"
export DO_NOT_RETRY_FLAG
trap 'rm -f "$DO_NOT_RETRY_FLAG"' EXIT

log() {
    local line="[$(date '+%Y-%m-%d %H:%M:%S')] [retry-wrapper] $*"
    if [ -d "$LOG_DIR" ]; then
        echo "$line" | tee -a "$LOG_DIR/scraper.log"
    else
        echo "$line"
    fi
}

# Nth backoff value, last value repeating. bash 3.2 (this fleet's bash -- no associative
# arrays, no $BASHPID), so this is comma word-splitting rather than an array.
backoff_for() {
    local want=$1 i=1 v last=0
    local IFS=,
    for v in $SCRAPE_RETRY_BACKOFF_SECS; do
        case "$v" in ''|*[!0-9]*) continue ;; esac
        last=$v
        if [ "$i" -eq "$want" ]; then echo "$v"; return 0; fi
        i=$((i + 1))
    done
    echo "$last"
}

is_excluded() {
    local v
    local IFS=,
    for v in $SCRAPE_RETRY_EXCLUDED_JURISDICTIONS; do
        [ "$v" = "$STATE" ] && return 0
    done
    return 1
}

MAX_ATTEMPTS="$SCRAPE_RETRY_MAX_ATTEMPTS"
case "$MAX_ATTEMPTS" in ''|*[!0-9]*) MAX_ATTEMPTS=1 ;; esac
[ "$MAX_ATTEMPTS" -lt 1 ] && MAX_ATTEMPTS=1

# An excluded jurisdiction gets exactly one attempt with no suppression, which is
# byte-for-byte the same behaviour as calling run-scrape.sh directly. Same for
# SCRAPE_RETRY_MAX_ATTEMPTS=1 -- the wrapper is a transparent passthrough, not a soft-disabled
# retry loop, so a mistake in the rollout config degrades to today's behaviour.
if is_excluded; then
    log "$STATE is in SCRAPE_RETRY_EXCLUDED_JURISDICTIONS — single attempt, no retry"
    MAX_ATTEMPTS=1
fi

LABEL="$STATE${SESSION_ARG:+ $SESSION_ARG}"
[ "$MAX_ATTEMPTS" -gt 1 ] && log "Starting $LABEL with up to $MAX_ATTEMPTS attempts (backoff: ${SCRAPE_RETRY_BACKOFF_SECS}s)"

attempt=1
while : ; do
    # Suppress run-scrape.sh's own alert on every attempt but the last. The last attempt is
    # left un-suppressed so run-scrape.sh alerts for itself, once, about a failure that is by
    # then genuinely final.
    if [ "$attempt" -lt "$MAX_ATTEMPTS" ]; then
        SUPPRESS="1"
    else
        SUPPRESS="0"
    fi

    [ "$MAX_ATTEMPTS" -gt 1 ] && log "Attempt $attempt/$MAX_ATTEMPTS for $LABEL"

    rc=0
    rm -f "$DO_NOT_RETRY_FLAG"
    # $SESSION_ARG unquoted so an empty session expands to no argument at all, matching how
    # ddp-sync invokes run-scrape.sh today.
    SUPPRESS_FAILURE_ALERT="$SUPPRESS" bash "$RUN_SCRAPE" "$STATE" $SESSION_ARG || rc=$?

    # Success, including both legitimate no-op paths -- see the header. Not retried.
    if [ "$rc" -eq 0 ]; then
        [ "$MAX_ATTEMPTS" -gt 1 ] && log "Attempt $attempt/$MAX_ATTEMPTS for $LABEL succeeded"
        exit 0
    fi

    # Classified by run-scrape.sh as a failure that a retry would make worse, not better.
    # Decided on the flag file, NOT on $rc -- see DO_NOT_RETRY_FLAG above for why an exit code
    # cannot carry this safely. run-scrape.sh has already alerted (it un-suppresses itself for
    # this case), which is only sound because the flag cannot be set by accident.
    if [ -f "$DO_NOT_RETRY_FLAG" ]; then
        log "Attempt $attempt/$MAX_ATTEMPTS for $LABEL failed and was classified do-not-retry — stopping (run-scrape.sh has alerted)"
        exit "$rc"
    fi

    if [ "$attempt" -ge "$MAX_ATTEMPTS" ]; then
        [ "$MAX_ATTEMPTS" -gt 1 ] && log "All $MAX_ATTEMPTS attempts for $LABEL failed (last rc=$rc) — run-scrape.sh has alerted"
        exit "$rc"
    fi

    sleep_secs=$(backoff_for "$attempt")
    # A config with no usable values would otherwise sleep 0 and hammer the source. Retrying
    # immediately is never what anyone wanted here, so floor it rather than trusting the config.
    [ "$sleep_secs" -lt 1 ] && sleep_secs=900
    log "Attempt $attempt/$MAX_ATTEMPTS for $LABEL failed (rc=$rc, alert suppressed) — retrying in ${sleep_secs}s"
    sleep "$sleep_secs"
    attempt=$((attempt + 1))
done
