#!/usr/bin/env bash
# check-replica-health.sh — scheduled health check + alerting for the RDS -> Mac logical replica
# (OPEN-312, follow-on to OPEN-269/274/277).
#
# WHY THIS EXISTS. The Mac Studio's `openstates_rds_repl_*` database is a logical replica of the RDS
# ddp-openstates database, and LegBot reads it. Two scripts already assess it --
# ops/postgres-replica/local/replica-status.sh (worker state, lag, retained WAL, CAMS heartbeat) and
# compare-schema.sh (table set + column agreement) -- but nothing ever RAN them. On 2026-09-27 the
# publisher refused connections for ~3h50m and the subscription crash-looped every 5 s unnoticed.
# This script is only the missing glue: run the two assessors, and turn a *persistent* bad verdict
# into one Slack message (plus a recovery message). It assesses nothing itself.
#
# HOW IT RUNS. Meant to be invoked every 5 minutes from the same one-line hook mechanism as
# check-scrape-staleness.sh (ddp-agents/deployment/scripts/health-check-slack.sh, under the
# com.ddp.health-monitor LaunchDaemon):
#     bash /Users/agentsmith/Developer/repos/ddp-open-states/check-replica-health.sh >/dev/null 2>&1 || true
# Always exits 0, so a bug here can never break the monitor it runs under.
#
# TWO STAGES, DIFFERENT PRICE:
#   1. replica-status.sh every run. Credential-free locally: catches "no apply worker" and "no message
#      from the publisher for RECEIPT_STALE_S" (the 2026-09-27 outage, and the crash loop a schema
#      mismatch causes). If RDS_MONITORING_DATABASE_URL is in the environment it also checks lag and
#      retained WAL on RDS.
#   2. compare-schema.sh at most every SCHEMA_EVERY_S (default 6 h), and ONLY when RDS_HOST and
#      RDS_REPLICATION_PASSWORD are in the environment. This is what catches a table added to the
#      publication but never refreshed into the subscription (silent: no error, the table just never
#      arrives) and column drift. Without the credential the stage is skipped, not failed -- how the
#      scheduled hook obtains the RDS credential is a deploy question (ddp-sync resolves it in Python
#      via Secrets Manager; a shell hook cannot), deliberately not invented here.
#
# ALERTING. One Slack message to #automation-errors when a check has been bad for CONSECUTIVE runs in
# a row (default 2: one blip never pages), a reminder every REMIND_S (default 6 h) while it stays bad,
# and a recovery message. State is one small file per check under logs/last-run/, and it advances only
# when Slack answers "ok":true (a rejected message or missing token is retried, not recorded as sent). This is the Slack
# block PRIMITIVES.md tells new scripts to copy (token read from ddp-agents/.env, fail open). It
# deliberately does not post to CAMS /api/v1/failures: that feeds CodeBot code triage, which can do
# nothing about a network outage or a forgotten REFRESH PUBLICATION. Extracting the shared Slack
# helper is OPEN-43; this is one more reason to do it, not a reason to do it here.
#
# Test seams (production sets none): REPLICA_LAST_RUN_DIR, REPLICA_LOG_FILE, REPLICA_DRY_RUN=1 (print
# "DRY_RUN slack: ..." instead of posting), REPLICA_NOW_EPOCH, REPLICA_STATUS_CMD, REPLICA_COMPARE_CMD,
# REPLICA_DB. bash 3.2 compatible (this Mac's /bin/bash): no associative arrays, no ${var,,}.

set -uo pipefail

REPO_DIR=/Users/agentsmith/Developer/repos/ddp-open-states
LAST_RUN_DIR="${REPLICA_LAST_RUN_DIR:-$REPO_DIR/logs/last-run}"
LOG_FILE="${REPLICA_LOG_FILE:-$REPO_DIR/logs/replica-check.log}"
DRY_RUN="${REPLICA_DRY_RUN:-0}"
NOW_EPOCH="${REPLICA_NOW_EPOCH:-$(date +%s)}"
STATUS_CMD="${REPLICA_STATUS_CMD:-$REPO_DIR/ops/postgres-replica/local/replica-status.sh}"
COMPARE_CMD="${REPLICA_COMPARE_CMD:-$REPO_DIR/ops/postgres-replica/local/compare-schema.sh}"
PG_CONTAINER="${PG_CONTAINER:-ddp-openstates-postgres-1}"
PG_USER="${PG_USER:-openstates}"
SUBSCRIPTION="${SUBSCRIPTION:-ddp_legbot_subscription}"
CONSECUTIVE="${REPLICA_CONSECUTIVE:-2}"
REMIND_S="${REPLICA_REMIND_S:-21600}"
SCHEMA_EVERY_S="${REPLICA_SCHEMA_EVERY_S:-21600}"

# Same local-time log() shape as the rest of this repo; own file so a quiet 5-minute job does not
# clutter scraper.log. Quiet runs (all healthy) log nothing.
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

# The daemon this runs under (com.ddp.health-monitor) gets launchd's bare environment: PATH is only
# /usr/bin:/bin:/usr/sbin:/sbin and HOME is UNSET (verified with `launchctl print`, 2026-10-01).
# Without the two lines below this script aborted silently on its first `$HOME` under `set -u` and
# could not have found `docker` (it lives in /opt/homebrew/bin) even if it had not. Children
# (replica-status.sh, compare-schema.sh) inherit both.
export PATH="$PATH:/opt/homebrew/bin:/usr/local/bin"   # appended: a caller's own PATH (and test stubs) still win

# A root LaunchDaemon has no GUI docker context: reach Colima's socket directly, exactly as
# start-os-api.sh does.
if [ -z "${DOCKER_HOST:-}" ]; then
    for _sock in "${HOME:-/var/root}/.colima/default/docker.sock" "/Users/agentsmith/.colima/default/docker.sock"; do
        [ -S "$_sock" ] && export DOCKER_HOST="unix://$_sock" && break
    done
fi

if [ "${REPLICA_SLACK_TOKEN+set}" = set ]; then
    SLACK_TOKEN="$REPLICA_SLACK_TOKEN"   # test seam (may be empty, to exercise the no-token path)
else
    SLACK_TOKEN=$(grep -E '^SLACK_BOT_TOKEN=' /Users/agentsmith/Developer/repos/ddp-agents/.env \
        2>/dev/null | head -1 | cut -d'=' -f2- | tr -d '"'"'" | awk '{print $1}')
fi

post_slack() {
    # $1 = message, already passed through clean_text(). Returns 0 ONLY if Slack accepted it.
    # Slack answers HTTP 200 with {"ok":false,...} for a bad token, missing scope or bad channel, and
    # the no-token case posts nothing at all; both must leave the alert state unadvanced so the next
    # run retries, otherwise a failed page is recorded as sent and then silenced for REMIND_S.
    if [ "$DRY_RUN" = "1" ]; then
        echo "DRY_RUN slack: $1"
        return 0
    fi
    if [ -z "$SLACK_TOKEN" ]; then
        log "no Slack token available: message NOT delivered, will retry next run"
        return 1
    fi
    local resp
    resp="$(curl -s --max-time 10 -X POST https://slack.com/api/chat.postMessage \
        -H "Authorization: Bearer $SLACK_TOKEN" -H "Content-Type: application/json" \
        -d "{\"channel\": \"#automation-errors\", \"text\": \"$1\"}")" || resp=""
    case "$resp" in
        *'"ok":true'*) return 0 ;;
    esac
    log "Slack did not accept the message (${resp:0:120}): will retry next run"
    return 1
}

# One line, no quotes, backslashes or other control characters (all JSON-breaking), capped.
clean_text() { printf '%s' "$1" | tr '\n\r\t' '   ' | tr -d '\000-\037"\\' | cut -c1-400; }

# track <key> <ok|bad> <message> [alert_after_bad_runs] [remind_seconds]
# State file replica-health.<key>.state holds "<bad_runs> <last_alert_epoch> <first_bad_epoch>".
# The last two args default to CONSECUTIVE / REMIND_S; the schema check runs only every few hours, so
# it alerts on its first failure (waiting for a second would add half a day) and reminds daily.
track() {
    local key="$1" verdict="$2" msg state bad last first need="${4:-$CONSECUTIVE}" remind="${5:-$REMIND_S}"
    msg="$(clean_text "$3")"
    state="$LAST_RUN_DIR/replica-health.$key.state"
    bad=0; last=0; first=$NOW_EPOCH
    [ -f "$state" ] && read -r bad last first < "$state"
    case "$bad$last$first" in *[!0-9]*) bad=0; last=0; first=$NOW_EPOCH ;; esac   # corrupt -> reset

    if [ "$verdict" = "ok" ]; then
        if [ -f "$state" ]; then
            if [ "$last" -gt 0 ]; then
                log "RECOVERED: $key"
                if ! post_slack "✅ *Mac replica of RDS — $key recovered* (was bad for ~$(( (NOW_EPOCH - first) / 60 )) min)"; then
                    return 0   # keep the state: the recovery message is retried on the next run
                fi
            fi
            rm -f "$state"
        fi
        return 0
    fi

    bad=$(( bad + 1 ))
    if [ "$bad" -ge "$need" ] && { [ "$last" -eq 0 ] || [ $(( NOW_EPOCH - last )) -ge "$remind" ]; }; then
        log "ALERT: $key — $msg"
        if [ "$last" -eq 0 ]; then
            post_slack "⚠️ *Mac replica of RDS — $key is bad:* $msg — LegBot reads this replica. See ops/postgres-replica/local/README.md." && last=$NOW_EPOCH
        else
            post_slack "⚠️ *Mac replica of RDS — $key is STILL bad* (~$(( (NOW_EPOCH - first) / 60 )) min): $msg" && last=$NOW_EPOCH
        fi
    fi
    mkdir -p "$LAST_RUN_DIR"
    echo "$bad $last $first" > "$state"
}

# --- Find the database that carries the subscription (its name changes on every rebuild) -----------
if [ -n "${REPLICA_DB:-}" ]; then
    db="$REPLICA_DB"
else
    db="$(docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d postgres -tAc \
        "SELECT d.datname FROM pg_subscription s JOIN pg_database d ON d.oid = s.subdbid WHERE s.subname = '$SUBSCRIPTION'" 2>&1)"
    db_rc=$?
    if [ "$db_rc" -ne 0 ]; then
        track replica bad "cannot query local Postgres container $PG_CONTAINER: $db"
        exit 0
    fi
    if [ -z "$db" ]; then
        track replica bad "no subscription named $SUBSCRIPTION exists on this Postgres server"
        exit 0
    fi
fi

# --- Stage 1: replica-status.sh (every run) ---------------------------------------------------------
out="$(bash "$STATUS_CMD" "$db" 2>&1)"
status="$(printf '%s\n' "$out" | sed -n 's/^== Overall status: \([A-Z]*\) ==$/\1/p' | tail -1)"
detail="$(printf '%s\n' "$out" | sed -n '/^== Overall status:/{n;p;}' | tail -1)"
case "$status" in
    HEALTHY|INCOMPLETE) track replica ok "" ;;   # INCOMPLETE = local checks passed, RDS side not configured
    BROKEN|DISCONNECTED|LAGGING) track replica bad "$status — $detail" ;;
    *) track replica bad "could not read a status from replica-status.sh (exit unknown): $(printf '%s\n' "$out" | tail -2)" ;;
esac

# --- Stage 2: compare-schema.sh (every SCHEMA_EVERY_S, only with an RDS credential) ----------------
if [ -n "${RDS_HOST:-}" ] && [ -n "${RDS_REPLICATION_PASSWORD:-}" ]; then
    checked="$LAST_RUN_DIR/replica-health.schema.checked"
    last_checked=0
    [ -f "$checked" ] && read -r last_checked < "$checked"
    case "$last_checked" in ''|*[!0-9]*) last_checked=0 ;; esac
    if [ $(( NOW_EPOCH - last_checked )) -ge "$SCHEMA_EVERY_S" ]; then
        mkdir -p "$LAST_RUN_DIR"
        schema_out="$(bash "$COMPARE_CMD" "$db" 2>&1)"
        schema_rc=$?
        echo "$NOW_EPOCH" > "$checked"
        if [ "$schema_rc" -eq 0 ]; then
            track schema ok ""
        else
            track schema bad "$(printf '%s\n' "$schema_out" | grep -E '^FAIL' | head -3 | tr '\n' ' ')" 1 86400
        fi
    fi
fi

exit 0
