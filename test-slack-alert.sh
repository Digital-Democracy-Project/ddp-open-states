#!/usr/bin/env bash
# test-slack-alert.sh — tests for lib/slack-alert.sh's post_slack_alert (OPEN-325, route-first OPEN-436)
#
# No network and no real Slack: a fake `curl` on PATH records what would have been sent. Every case
# runs in a clean `env -i` so the real SLACK_BOT_TOKEN / CODEBOT_* of whoever runs this never leak in.
#     bash test-slack-alert.sh          (and /bin/bash test-slack-alert.sh: macOS's bash 3.2 is the target)
# Exits 0 with "ALL PASS" or 1 with the failing assertions.
#
# What is being guarded: alerts posted with only `channel` and `text` show up in Slack as the app's own
# name, Agent Smith, instead of CodeBot. The scripts each had their own copy of the curl, so the fix
# lives in ONE function, and the last block fails if a script grows a second way to post.

set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
LIB="$HERE/lib/slack-alert.sh"
T=$(mktemp -d "${TMPDIR:-/tmp}/slack-alert-test.XXXXXX") || { echo "cannot create a temp directory"; exit 2; }
trap 'rm -rf "$T"' EXIT

PASS=0
FAIL=0
ok()   { PASS=$((PASS + 1)); echo "  ok   $1"; }
fail() { FAIL=$((FAIL + 1)); echo "  FAIL $1"; }
check() { if [ "$2" = "$3" ]; then ok "$1"; else fail "$1 — expected [$3], got [$2]"; fi; }

# A fake curl that tells the two destinations apart by URL. A call to the CAMS route (a URL containing
# operator-alerts) records its -d body as payload.route and answers FAKE_ROUTE_CODE (default 202, printed
# because the helper asks for -w '%{http_code}'), exiting FAKE_ROUTE_EXIT (default 0; a real curl that cannot
# connect prints 000 and exits 7). Any other call is Slack: it records the -d body as payload and answers
# FAKE_CURL_RESPONSE (default {"ok":true}), exiting FAKE_CURL_EXIT (default 0). Every call adds a line to
# `calls` and its URL to `urls`; every -H goes to `headers`.
mkdir -p "$T/bin"
cat > "$T/bin/curl" <<'EOF'
#!/bin/bash
url=""
for arg in "$@"; do case "$arg" in http*) url="$arg" ;; esac; done
case "$url" in *operator-alerts*) route=1; pf=payload.route ;; *) route=0; pf=payload ;; esac
i=1
while [ $i -le $# ]; do
    arg="${!i}"; next=$((i + 1))
    if [ "$arg" = "-d" ]; then printf '%s' "${!next}" > "$FAKE_CURL_DIR/$pf"; fi
    if [ "$arg" = "-H" ]; then printf '%s\n' "${!next}" >> "$FAKE_CURL_DIR/headers"; fi
    i=$((i + 1))
done
echo called >> "$FAKE_CURL_DIR/calls"
echo "$url" >> "$FAKE_CURL_DIR/urls"
if [ "$route" = 1 ]; then
    printf '%s' "${FAKE_ROUTE_CODE-202}"
    exit "${FAKE_ROUTE_EXIT:-0}"
fi
printf '%s' "${FAKE_CURL_RESPONSE-{\"ok\":true\}}"
exit "${FAKE_CURL_EXIT:-0}"
EOF
chmod +x "$T/bin/curl"

# run_alert <env-file-content|-> <script-body> [VAR=value ...]
# Runs the body with the library sourced, in a clean environment. Prints the body's output; the fake
# curl's records land in $T/run/.
run_alert() {
    local envfile_content="$1" body="$2"; shift 2
    rm -rf "$T/run"; mkdir -p "$T/run"
    local envfile="$T/run/agents.env"
    if [ "$envfile_content" = "-" ]; then : > "$envfile"; else printf '%s\n' "$envfile_content" > "$envfile"; fi
    env -i PATH="$T/bin:/usr/bin:/bin" HOME="$T" FAKE_CURL_DIR="$T/run" SLACK_ALERT_ENV_FILE="$envfile" "$@" \
        /bin/bash -c "source '$LIB'; $body" 2>"$T/run/stderr"
}
payload() { cat "$T/run/payload" 2>/dev/null; }
calls()   { [ -f "$T/run/calls" ] && wc -l < "$T/run/calls" | tr -d ' ' || echo 0; }

json_get() {   # json_get <key> [file]  (reads the recorded Slack payload, or the named file such as payload.route)
    local f="$T/run/${2:-payload}"
    if command -v jq >/dev/null 2>&1; then jq -r ".$1" "$f"
    else python3 -c "import json,sys; print(json.load(open('$f'))['$1'])"; fi
}
json_valid() {   # json_valid [file]
    local f="$T/run/${1:-payload}"
    if command -v jq >/dev/null 2>&1; then jq -e . "$f" >/dev/null 2>&1
    else python3 -c "import json; json.load(open('$f'))" 2>/dev/null; fi
}
json_has() {   # json_has <key> <file>: 1 if the key is present
    local f="$T/run/$2"
    if command -v jq >/dev/null 2>&1; then jq -e "has(\"$1\")" "$f" >/dev/null 2>&1 && echo 1 || echo 0
    else python3 -c "import json,sys; sys.exit(0 if '$1' in json.load(open('$f')) else 1)" && echo 1 || echo 0; fi
}
urls() { cat "$T/run/urls" 2>/dev/null | tr '\n' ' '; }
ROUTE="http://localhost:8000/api/v1/operator-alerts"
command -v jq >/dev/null 2>&1 || command -v python3 >/dev/null 2>&1 || { echo "need jq or python3 to read the payloads"; exit 2; }

echo "defaults"
run_alert 'SLACK_BOT_TOKEN=xoxb-from-file' 'post_slack_alert "scrape failed: ut"'
check "posts once" "$(calls)" "1"
check "channel defaults to #automation-errors" "$(json_get channel)" "#automation-errors"
check "text is passed through" "$(json_get text)" "scrape failed: ut"
check "username defaults to CodeBot" "$(json_get username)" "CodeBot"
check "icon defaults to :robot_face:" "$(json_get icon_emoji)" ":robot_face:"
check "the token goes in the Authorization header" "$(grep -c 'Bearer xoxb-from-file' "$T/run/headers")" "1"

echo "channel"
run_alert 'SLACK_BOT_TOKEN=xoxb-t' 'post_slack_alert "x" "#other"'
check "an explicit channel wins" "$(json_get channel)" "#other"

echo "settings: the .env file and the environment"
run_alert 'SLACK_BOT_TOKEN=xoxb-t
CODEBOT_SLACK_USERNAME="Failure Bot"   # the display name
CODEBOT_SLACK_ICON_EMOJI=:codebot:' 'post_slack_alert "x"'
check "a multi-word username is kept whole, quotes and inline comment removed" "$(json_get username)" "Failure Bot"
check "the icon comes from the .env file" "$(json_get icon_emoji)" ":codebot:"
run_alert "CODEBOT_SLACK_USERNAME=FromFile" 'post_slack_alert "x"' SLACK_BOT_TOKEN=xoxb-env CODEBOT_SLACK_USERNAME=FromEnv
check "an exported variable beats the .env file" "$(json_get username)" "FromEnv"
check "the token can come from the environment alone" "$(grep -c 'Bearer xoxb-env' "$T/run/headers")" "1"
run_alert 'SLACK_BOT_TOKEN=xoxb-t
CODEBOT_SLACK_USERNAME=
CODEBOT_SLACK_ICON_EMOJI=' 'post_slack_alert "x"'
check "an empty username means the default" "$(json_get username)" "CodeBot"
check "an empty icon means the default" "$(json_get icon_emoji)" ":robot_face:"
run_alert 'OTHER=1' 'post_slack_alert "x"' ; rc=$?
check "no .env file entry for the token: nothing is sent" "$(calls)" "0"
check "...and the call still succeeds" "$rc" "0"
check "...and says why on stderr" "$(grep -c 'SLACK_BOT_TOKEN is not set' "$T/run/stderr")" "1"
rm -f "$T/run/agents.env"
rm -rf "$T/run2"; mkdir -p "$T/run2"
env -i PATH="$T/bin:/usr/bin:/bin" HOME="$T" FAKE_CURL_DIR="$T/run2" SLACK_ALERT_ENV_FILE="$T/does-not-exist" \
    /bin/bash -c "source '$LIB'; post_slack_alert x" 2>/dev/null; rc=$?
check "a missing .env file is not an error" "$rc" "0"

echo "payload is valid JSON for hostile text"
run_alert 'SLACK_BOT_TOKEN=xoxb-t' 'post_slack_alert "$(printf '"'"'say "hi" \ back\\slash\nline two\ttab\r'"'"')"'
if json_valid; then ok "quotes, backslashes, newline, tab and CR still make valid JSON"; else fail "invalid JSON: $(payload)"; fi
check "the text round-trips" "$(json_get text | head -1)" 'say "hi" \ back\slash'
run_alert 'SLACK_BOT_TOKEN=xoxb-t' 'post_slack_alert "⚠️ *OpenStates scrape failed: ut* — check the log"'
check "unicode and emoji survive" "$(json_get text)" "⚠️ *OpenStates scrape failed: ut* — check the log"

echo "reports whether Slack took the message (OPEN-435)"
run_alert 'SLACK_BOT_TOKEN=xoxb-t' 'post_slack_alert "x"; echo "$OPERATOR_ALERT_DELIVERED $OPERATOR_ALERT_REASON"' >"$T/out"
check "ok:true is delivered" "$(cat "$T/out")" "1 ok"
run_alert 'SLACK_BOT_TOKEN=xoxb-t' 'post_slack_alert "x"; echo "$OPERATOR_ALERT_DELIVERED $OPERATOR_ALERT_REASON"' 'FAKE_CURL_RESPONSE={"ok":false,"error":"invalid_auth"}' >"$T/out"
check "ok:false is not delivered" "$(cat "$T/out")" "0 refused"
run_alert 'SLACK_BOT_TOKEN=xoxb-t' 'post_slack_alert "x"; echo "$OPERATOR_ALERT_DELIVERED $OPERATOR_ALERT_REASON"' FAKE_CURL_EXIT=22 FAKE_CURL_RESPONSE= >"$T/out"
check "a curl failure is not delivered" "$(cat "$T/out")" "0 refused"
run_alert '' 'post_slack_alert "x"; echo "$OPERATOR_ALERT_DELIVERED $OPERATOR_ALERT_REASON"' >"$T/out"
check "no token is not delivered" "$(cat "$T/out")" "0 no-token"
run_alert 'SLACK_BOT_TOKEN=xoxb-t' 'post_slack_alert "a"; OPERATOR_ALERT_DELIVERED=1; FAKE=1; post_slack_alert "b"; echo "$OPERATOR_ALERT_DELIVERED"' 'FAKE_CURL_RESPONSE={"ok":false}' >"$T/out"
check "a later failed post resets the flag" "$(cat "$T/out")" "0"

echo "route first (OPEN-436)"
RT='SLACK_BOT_TOKEN=xoxb-t
CAMS_API_TOKEN=cams-secret-value'
run_alert "$RT" 'post_slack_alert "scrape failed: ut" --source ddp-open-states/run-scrape; echo "$OPERATOR_ALERT_DELIVERED $OPERATOR_ALERT_REASON"' OPERATOR_ALERT_URL="$ROUTE" >"$T/out"
check "a 202 is delivered" "$(cat "$T/out")" "1 ok"
check "a 202 makes exactly one call, to the route, and none to Slack" "$(urls)" "$ROUTE "
check "the route body is v1 with the source and the text" "$(json_get v payload.route) $(json_get source payload.route) $(json_get text payload.route)" "1 ddp-open-states/run-scrape scrape failed: ut"
check "no channel is sent unless the caller gave one (the route's map decides)" "$(json_has channel payload.route)" "0"
check "no dedupe_key is sent unless the caller gave one" "$(json_has dedupe_key payload.route)" "0"
check "the CAMS token is the bearer, read from the .env file" "$(grep -c 'Bearer cams-secret-value' "$T/run/headers")" "1"
check "the Slack token is not sent to CAMS" "$(grep -c 'xoxb-t' "$T/run/headers")" "0"
run_alert 'CAMS_API_TOKEN=cams-secret-value' 'post_slack_alert "x"; echo "$OPERATOR_ALERT_DELIVERED"' OPERATOR_ALERT_URL="$ROUTE" >"$T/out"
check "a route post needs no Slack token: delivered with SLACK_BOT_TOKEN unset" "$(cat "$T/out")" "1"
run_alert "$RT" 'post_slack_alert "x" "#other" --source ddp-open-states/run-archive --dedupe-key scrape:ut' OPERATOR_ALERT_URL="$ROUTE"
check "an explicit channel goes to the route" "$(json_get channel payload.route)" "#other"
check "--dedupe-key goes to the route" "$(json_get dedupe_key payload.route)" "scrape:ut"
check "--source defaults to ddp-open-states/unknown" "$(run_alert "$RT" 'post_slack_alert "x"' OPERATOR_ALERT_URL="$ROUTE"; json_get source payload.route)" "ddp-open-states/unknown"
run_alert "$RT" 'post_slack_alert "$(printf '"'"'say "hi" \ back\\slash\nline two\ttab\r'"'"')"' OPERATOR_ALERT_URL="$ROUTE"
if json_valid payload.route; then ok "hostile text is valid JSON in the route body too"; else fail "invalid route JSON: $(cat "$T/run/payload.route")"; fi

echo "route first: every failure falls through to the direct post"
for case_ in "000 7" "401 0" "400 0" "503 0" "500 0" "302 0"; do
    code="${case_% *}"; rc="${case_#* }"
    run_alert "$RT" 'post_slack_alert "scrape failed: ut" --source ddp-open-states/run-scrape; echo "$OPERATOR_ALERT_DELIVERED $OPERATOR_ALERT_REASON"' \
        OPERATOR_ALERT_URL="$ROUTE" FAKE_ROUTE_CODE="$code" FAKE_ROUTE_EXIT="$rc" >"$T/out"
    check "route $code: the alert is still delivered, directly" "$(cat "$T/out")" "1 ok"
    check "route $code: one call to the route, then one to Slack" "$(urls)" "$ROUTE https://slack.com/api/chat.postMessage "
    check "route $code: the direct post carries the CodeBot name" "$(json_get username)" "CodeBot"
    check "route $code: the direct post carries the icon" "$(json_get icon_emoji)" ":robot_face:"
    check "route $code: the direct post carries the text" "$(json_get text)" "scrape failed: ut"
    check "route $code: the fallback is reported on stderr, without the token" "$(grep -c 'CAMS answered' "$T/run/stderr") $(grep -c 'cams-secret-value' "$T/run/stderr")" "1 0"
done
run_alert "$RT" 'post_slack_alert "x"; echo "$OPERATOR_ALERT_DELIVERED $OPERATOR_ALERT_REASON"' OPERATOR_ALERT_URL="$ROUTE" FAKE_ROUTE_CODE=503 'FAKE_CURL_RESPONSE={"ok":false,"error":"not_in_channel"}' >"$T/out"
check "route refused and Slack refused: not delivered" "$(cat "$T/out")" "0 refused"
run_alert "$RT" 'set -euo pipefail; post_slack_alert "x"; echo survived' OPERATOR_ALERT_URL="$ROUTE" FAKE_ROUTE_CODE=000 FAKE_ROUTE_EXIT=7 >"$T/out"
check "a failing route call does not trip set -euo pipefail" "$(cat "$T/out")" "survived"
run_alert "$RT" 'post_slack_alert "x"; echo "$OPERATOR_ALERT_DELIVERED"' OPERATOR_ALERT_URL="$ROUTE" FAKE_ROUTE_CODE=202 >"$T/out"
check "any 2xx counts as delivered (the route's duplicate and rate-limited answers are 202)" "$(cat "$T/out")" "1"

echo "route first: when the route is not used"
run_alert "$RT" 'post_slack_alert "x" --direct' OPERATOR_ALERT_URL="$ROUTE"
check "--direct never calls the route" "$(urls)" "https://slack.com/api/chat.postMessage "
run_alert "$RT" 'post_slack_alert "x" --source ddp-open-states/run-scrape --direct' OPERATOR_ALERT_URL="$ROUTE"
check "--direct after other options still never calls the route" "$(urls)" "https://slack.com/api/chat.postMessage "
run_alert "$RT" 'post_slack_alert "x"' OPERATOR_ALERT_URL="$ROUTE" OPERATOR_ALERT_VIA_CAMS=false
check "OPERATOR_ALERT_VIA_CAMS=false posts directly (the rollback)" "$(urls)" "https://slack.com/api/chat.postMessage "
run_alert "$RT" 'post_slack_alert "x"'
check "OPERATOR_ALERT_URL unset (the default): posts directly, as before OPEN-436" "$(urls)" "https://slack.com/api/chat.postMessage "
check "...and says nothing about CAMS" "$(grep -c 'CAMS' "$T/run/stderr")" "0"
run_alert 'SLACK_BOT_TOKEN=xoxb-t' 'post_slack_alert "x"' OPERATOR_ALERT_URL="$ROUTE"
check "no CAMS token: posts directly" "$(urls)" "https://slack.com/api/chat.postMessage "
run_alert "$RT" 'post_slack_alert "x"' OPERATOR_ALERT_URL=http://localhost:8000/api/v1/operator-alerts OPERATOR_ALERT_VIA_CAMS=
check "an empty OPERATOR_ALERT_VIA_CAMS means the default (route first)" "$(urls)" "$ROUTE "
run_alert "$RT
OPERATOR_ALERT_URL=$ROUTE" 'post_slack_alert "x"'
check "OPERATOR_ALERT_URL can come from the .env file" "$(urls)" "$ROUTE "

echo "never fails the calling script"
run_alert 'SLACK_BOT_TOKEN=xoxb-t' 'set -euo pipefail; post_slack_alert "x"; echo survived' FAKE_CURL_EXIT=22 >"$T/out"
check "a failing curl does not trip set -euo pipefail" "$(cat "$T/out")" "survived"
run_alert 'SLACK_BOT_TOKEN=xoxb-t' 'set -euo pipefail; post_slack_alert "x"; echo survived' 'FAKE_CURL_RESPONSE={"ok":false,"error":"not_in_channel"}' >"$T/out"
check "Slack refusing the post does not trip it either" "$(cat "$T/out")" "survived"
check "...and the refusal is reported on stderr" "$(grep -c 'not_in_channel' "$T/run/stderr")" "1"
run_alert '' 'set -euo pipefail; post_slack_alert "x"; echo survived' >"$T/out"
check "no token: still returns 0 under set -euo pipefail" "$(cat "$T/out")" "survived"
run_alert 'SLACK_BOT_TOKEN=xoxb-secret-value' 'post_slack_alert "x"' 'FAKE_CURL_RESPONSE={"ok":false}'
check "the token is never printed to stderr" "$(grep -c 'xoxb-secret-value' "$T/run/stderr")" "0"

echo "the scripts"
for s in run-scrape.sh run-archive.sh backup-openstates-db.sh start-os-api.sh; do
    if /bin/bash -n "$HERE/$s" 2>/dev/null; then ok "$s parses under bash 3.2"; else fail "$s does not parse"; fi
    check "$s posts through post_slack_alert" "$(grep -c 'post_slack_alert "' "$HERE/$s" | tr -d ' ' | awk '{print ($1>0)}')" "1"
done
# The real fallback line each script ships, run with the library missing: the alert is skipped with a
# message and the script (here set -euo pipefail) carries on. Run it from every script that has it.
for s in run-scrape.sh run-archive.sh backup-openstates-db.sh start-os-api.sh; do
    guard="$(grep -A1 '^\[ -r "\$SCRIPT_DIR/lib/slack-alert.sh" \]' "$HERE/$s")"
    if [ -z "$guard" ]; then fail "$s has no guarded source line"; continue; fi
    out="$(env -i PATH="/usr/bin:/bin" /bin/bash -c "set -euo pipefail; SCRIPT_DIR=/nonexistent
$guard
post_slack_alert 'hello'; echo survived" 2>&1)"
    check "$s: a missing lib/slack-alert.sh skips the alert but not the script" "$(printf '%s' "$out" | tail -1)" "survived"
done

# Class A scripts name their own source for the route; class B scripts (alerts about CAMS, Docker or the replica)
# must go direct. A new caller should have to choose one on purpose.
for s in run-scrape.sh run-archive.sh backup-openstates-db.sh; do
    check "$s passes --source ddp-open-states/..." "$(grep -c 'post_slack_alert .*--source ddp-open-states/' "$HERE/$s" | tr -d ' ' | awk '{print ($1>0)}')" "1"
    check "$s does not pass --direct (class A)" "$(grep -c 'post_slack_alert .*--direct' "$HERE/$s" | tr -d ' ')" "0"
done
for s in start-os-api.sh check-replica-health.sh; do
    check "$s passes --direct (class B)" "$(grep -c 'post_slack_alert .*--direct' "$HERE/$s" | tr -d ' ' | awk '{print ($1>0)}')" "1"
done

echo "nothing else posts to Slack"
# One way to post: this repo's shell scripts must not carry their own chat.postMessage call.
offenders=""
for f in "$HERE"/*.sh "$HERE"/lib/*.sh; do
    name="$(basename "$f")"
    case "$name" in slack-alert.sh|test-*.sh) continue ;; esac
    if grep -q 'slack.com/api/chat.postMessage' "$f"; then offenders="$offenders $name"; fi
done
check "no script but the helper calls chat.postMessage" "${offenders:- none}" " none"
check "the helper carries the CodeBot identity" "$(grep -c 'icon_emoji' "$LIB" | tr -d ' ' | awk '{print ($1>0)}')" "1"

echo
if [ "$FAIL" -eq 0 ]; then
    echo "ALL PASS ($PASS assertions)"
    exit 0
fi
echo "$FAIL FAILED, $PASS passed"
exit 1
