#!/usr/bin/env bash
# lib/slack-alert.sh -- the one way a ddp-open-states shell script posts an alert to Slack (OPEN-325).
#
# SOURCE it, do not run it:
#     source "$SCRIPT_DIR/lib/slack-alert.sh"
#     post_slack_alert "⚠️ *OpenStates scrape failed: $STATE* — check the log"
#
# Why it exists: every alert goes through the one Slack app (Agent Smith's SLACK_BOT_TOKEN). A post with
# only `channel` and `text` shows up under the app's own name, Agent Smith, but this failure stream is
# meant to read as CodeBot (ddp-agents' failure triage and ddp-sync's alerts already do). Each script used
# to carry its own hand-written curl, so the sender identity was missing in all of them and any new alert
# would copy the mistake. The identity is set here, once. test-slack-alert.sh fails if another script
# posts to Slack directly.
#
# post_slack_alert TEXT [CHANNEL]
#   CHANNEL defaults to #automation-errors. ALWAYS returns 0: an alert is best-effort and must never
#   change a calling script's exit status or trip its `set -e`. A post that cannot be sent (no token,
#   Slack refused it) is reported on stderr, not swallowed.
#
# Settings, each read from the environment first, then from ddp-agents' .env (the same file these
# scripts already read SLACK_BOT_TOKEN from):
#   SLACK_BOT_TOKEN              required to send anything
#   CODEBOT_SLACK_USERNAME       default "CodeBot"
#   CODEBOT_SLACK_ICON_EMOJI     default ":robot_face:"
# SLACK_ALERT_ENV_FILE overrides the .env path (used by the tests).
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

post_slack_alert() {
    local text="${1:-}" channel="${2:-#automation-errors}"
    local token username icon payload resp

    token="$(_slack_alert_setting SLACK_BOT_TOKEN)"
    if [ -z "$token" ]; then
        echo "slack-alert: SLACK_BOT_TOKEN is not set; alert not sent: ${text:0:200}" >&2
        return 0
    fi
    username="$(_slack_alert_setting CODEBOT_SLACK_USERNAME)"
    [ -n "$username" ] || username="CodeBot"
    icon="$(_slack_alert_setting CODEBOT_SLACK_ICON_EMOJI)"
    [ -n "$icon" ] || icon=":robot_face:"

    payload="{\"channel\":\"$(_slack_alert_json_escape "$channel")\""
    payload="$payload,\"text\":\"$(_slack_alert_json_escape "$text")\""
    payload="$payload,\"username\":\"$(_slack_alert_json_escape "$username")\""
    payload="$payload,\"icon_emoji\":\"$(_slack_alert_json_escape "$icon")\"}"

    resp="$(curl -s --max-time 10 -X POST https://slack.com/api/chat.postMessage \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json; charset=utf-8" \
        -d "$payload" 2>/dev/null || true)"
    case "$resp" in
        *'"ok":true'*) ;;
        *) echo "slack-alert: Slack did not accept the post: ${resp:0:200}" >&2 ;;
    esac
    return 0
}
