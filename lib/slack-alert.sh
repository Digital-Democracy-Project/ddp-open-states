#!/usr/bin/env bash
# lib/slack-alert.sh -- the one way a ddp-open-states shell script posts an alert to Slack (OPEN-325).
#
# SOURCE it, do not run it:
#     source "$SCRIPT_DIR/lib/slack-alert.sh"
#     post_slack_alert ":warning: *OpenStates scrape failed: $STATE* — check the log" --source ddp-open-states/run-scrape
#
# Why it exists: every alert goes through the one Slack app (Agent Smith's SLACK_BOT_TOKEN). A post with
# only `channel` and `text` shows up under the app's own name, Agent Smith, but this failure stream is
# meant to read as CodeBot (ddp-agents' failure triage and ddp-sync's alerts already do). Each script used
# to carry its own hand-written curl, so the sender identity was missing in all of them and any new alert
# would copy the mistake. The identity is set here, once. test-slack-alert.sh fails if another script
# posts to Slack directly.
#
# post_slack_alert TEXT [CHANNEL] [--source S] [--dedupe-key K] [--direct]   (OPEN-436)
#   Route first, direct second (PLAN-cams-operator-alerts §4.9). A class-A alert (a job whose failure is not
#   about CAMS) is first sent to CAMS's POST /api/v1/operator-alerts (5 s, Bearer CAMS_API_TOKEN), which queues
#   it, retries, rate-limits and shows a failed delivery in `cams status`. ANY answer other than 2xx, a timeout
#   or a connection error falls back to the direct CodeBot post below, so an alert is never lost because CAMS
#   is down or the route and this script disagree (a 4xx is a bug here: it is reported on stderr). A 2xx
#   counts as delivered, including the route's "duplicate" and "dropped_rate_limited" answers (§4.13).
#   --direct  skip the route: class B, an alert about CAMS, Docker or the replica itself (start-os-api.sh,
#             check-replica-health.sh) must not depend on CAMS being up.
#   --source  "<service>/<job>", default ddp-open-states/unknown; run-scrape.sh etc. pass their own. The route
#             rejects a source that is not "<service>/<job>" (then the direct post is used).
#   --dedupe-key  optional: the route posts one alert per key per day. No caller sets it today.
#   CHANNEL is sent to the route only when given (the route's channel map decides otherwise) and defaults to
#   #automation-errors for the direct post. ALWAYS returns 0: an alert is best-effort and must never
#   change a calling script's exit status or trip its `set -e`. A post that cannot be sent (no token,
#   Slack refused it) is reported on stderr, not swallowed. A caller that must know whether Slack took the
#   message (check-replica-health.sh advances its alert state only when it did) reads, after the call:
#   OPERATOR_ALERT_DELIVERED   1 only when CAMS answered 2xx or Slack answered "ok":true, else 0
#   OPERATOR_ALERT_REASON      ok | no-token | refused   (same names as ddp-agents' operator-alert.sh)
#
# Settings, each read from the environment first, then from ddp-agents' .env (the same file these
# scripts already read SLACK_BOT_TOKEN from):
#   SLACK_BOT_TOKEN              required for the direct post (not for a route post: CAMS holds its own)
#   CODEBOT_SLACK_USERNAME       default "CodeBot"
#   CODEBOT_SLACK_ICON_EMOJI     default ":robot_face:"
#   OPERATOR_ALERT_URL           full route URL, e.g. http://localhost:8000/api/v1/operator-alerts. UNSET (the
#                                default) means every alert is posted directly, as before OPEN-436: the route is
#                                switched on by adding this line to ddp-agents/.env.
#   CAMS_API_TOKEN               the CAMS bearer token (the same one run-scrape.sh sends to /api/v1/failures)
#   OPERATOR_ALERT_VIA_CAMS      "false" makes this host post directly whatever the two above say (the rollback)
# The mirror of ddp-agents' deployment/scripts/lib/operator-alert.sh (same variable names, same 5 s attempt and
# fallback); if one changes its contract, change the other. SLACK_ALERT_ENV_FILE overrides the .env path (used by the tests).
#
# Needs the `chat:write.customize` scope on the Slack app; without it Slack ignores username/icon_emoji
# and the post still succeeds under the default name, so this can never make an alert fail.
#
# Source it only if it is readable (`[ -r file ] && source file || fallback`): under `set -e`, bash 3.2
# exits the whole script when `source` hits a missing file even with a `||` fallback.
#
# Written for macOS's bash 3.2 (no ${!var}, no associative arrays) and safe under `set -euo pipefail`.

SLACK_ALERT_ENV_FILE="${SLACK_ALERT_ENV_FILE:-/Users/agentsmith/Developer/repos/ddp-agents/.env}"

# The value of setting $1: exported environment variable if non-empty, else the first `NAME=value` line
# of the .env file with surrounding quotes and an inline " # comment" removed. The whole value is kept
# (a multi-word username is not cut to its first word). Prints nothing if it is unset everywhere.
_slack_alert_setting() {
    local name="$1" value=""
    value="$(printenv "$name" 2>/dev/null || true)"
    if [ -z "$value" ] && [ -r "$SLACK_ALERT_ENV_FILE" ]; then
        value="$(grep -E "^${name}=" "$SLACK_ALERT_ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- || true)"
        value="$(printf '%s' "$value" | sed \
            -e 's/[[:space:]]#.*$//' \
            -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' \
            -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'$/\1/")"
    fi
    printf '%s' "$value"
}

# Escape $1 for use inside a JSON string. The hand-built payloads this replaces broke on any quote,
# backslash or newline in the text.
_slack_alert_json_escape() {
    local s="$1"
    s="$(printf '%s' "$s" | tr -d '\000-\010\013\014\016-\037')"   # other control characters are invalid JSON
    s="${s//\\/\\\\}"
    s="${s//\"/\\\"}"
    s="${s//$'\n'/\\n}"
    s="${s//$'\r'/\\r}"
    s="${s//$'\t'/\\t}"
    printf '%s' "$s"
}

# The sender identity as "NAME ICON" (defaults CodeBot :robot_face:). Also what check-replica-health.sh's
# REPLICA_DRY_RUN prints, so a dry run shows who the live post would come from.
_slack_alert_sender() {
    local username icon
    username="$(_slack_alert_setting CODEBOT_SLACK_USERNAME)"
    [ -n "$username" ] || username="CodeBot"
    icon="$(_slack_alert_setting CODEBOT_SLACK_ICON_EMOJI)"
    [ -n "$icon" ] || icon=":robot_face:"
    printf '%s\n%s' "$username" "$icon"
}

# The route attempt. Returns 0 only when CAMS answered 2xx (the alert is queued, or deliberately suppressed as a
# duplicate or over the cap). Anything else returns 1 and the caller posts directly. Silent when the route is not
# configured or switched off; says why on stderr when CAMS answered something else. The token is never printed.
_slack_alert_via_cams() {
    local text="$1" source="$2" dedupe="$3" channel="$4" url cams_token body code
    [ "$(_slack_alert_setting OPERATOR_ALERT_VIA_CAMS)" = "false" ] && return 1
    url="$(_slack_alert_setting OPERATOR_ALERT_URL)"
    cams_token="$(_slack_alert_setting CAMS_API_TOKEN)"
    [ -n "$url" ] && [ -n "$cams_token" ] || return 1

    body="{\"v\":1,\"source\":\"$(_slack_alert_json_escape "$source")\""
    body="$body,\"text\":\"$(_slack_alert_json_escape "$text")\""
    [ -n "$channel" ] && body="$body,\"channel\":\"$(_slack_alert_json_escape "$channel")\""
    [ -n "$dedupe" ] && body="$body,\"dedupe_key\":\"$(_slack_alert_json_escape "$dedupe")\""
    body="$body}"

    code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 -X POST "$url" \
        -H "Authorization: Bearer $cams_token" \
        -H "Content-Type: application/json; charset=utf-8" \
        -d "$body" 2>/dev/null || true)"
    case "$code" in
        2[0-9][0-9]) return 0 ;;
    esac
    echo "slack-alert: CAMS answered ${code:-no answer} for $source; posting directly" >&2
    return 1
}

post_slack_alert() {
    local text="${1:-}" channel="" source="ddp-open-states/unknown" dedupe="" direct=0
    [ $# -gt 0 ] && shift
    case "${1:-}" in ""|--*) ;; *) channel="$1"; shift ;; esac     # an optional CHANNEL comes before the options
    while [ $# -gt 0 ]; do
        case "$1" in
            --source)     source="${2:-$source}"; [ $# -ge 2 ] && shift ;;
            --dedupe-key) dedupe="${2:-}"; [ $# -ge 2 ] && shift ;;
            --direct)     direct=1 ;;
        esac
        shift
    done
    local token sender username icon payload resp
    OPERATOR_ALERT_DELIVERED=0
    OPERATOR_ALERT_REASON=refused

    if [ "$direct" = 0 ] && _slack_alert_via_cams "$text" "$source" "$dedupe" "$channel"; then
        OPERATOR_ALERT_DELIVERED=1; OPERATOR_ALERT_REASON=ok
        return 0
    fi
    channel="${channel:-#automation-errors}"

    token="$(_slack_alert_setting SLACK_BOT_TOKEN)"
    if [ -z "$token" ]; then
        echo "slack-alert: SLACK_BOT_TOKEN is not set; alert not sent: ${text:0:200}" >&2
        OPERATOR_ALERT_REASON=no-token
        return 0
    fi
    sender="$(_slack_alert_sender)"
    username="${sender%%$'\n'*}"
    icon="${sender#*$'\n'}"

    payload="{\"channel\":\"$(_slack_alert_json_escape "$channel")\""
    payload="$payload,\"text\":\"$(_slack_alert_json_escape "$text")\""
    payload="$payload,\"username\":\"$(_slack_alert_json_escape "$username")\""
    payload="$payload,\"icon_emoji\":\"$(_slack_alert_json_escape "$icon")\"}"

    resp="$(curl -s --max-time 10 -X POST https://slack.com/api/chat.postMessage \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json; charset=utf-8" \
        -d "$payload" 2>/dev/null || true)"
    case "$resp" in
        *'"ok":true'*) OPERATOR_ALERT_DELIVERED=1; OPERATOR_ALERT_REASON=ok ;;
        *) echo "slack-alert: Slack did not accept the post: ${resp:0:200}" >&2 ;;
    esac
    return 0
}
