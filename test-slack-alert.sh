#!/usr/bin/env bash
# test-slack-alert.sh — tests for lib/slack-alert.sh's post_slack_alert (OPEN-325)
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

# A fake curl: records the -d payload, the Authorization header and one line per call, and answers with
# FAKE_CURL_RESPONSE (default {"ok":true}), exiting FAKE_CURL_EXIT (default 0).
mkdir -p "$T/bin"
cat > "$T/bin/curl" <<'EOF'
#!/bin/bash
i=1
while [ $i -le $# ]; do
    arg="${!i}"; next=$((i + 1))
    if [ "$arg" = "-d" ]; then printf '%s' "${!next}" > "$FAKE_CURL_DIR/payload"; fi
    if [ "$arg" = "-H" ]; then printf '%s\n' "${!next}" >> "$FAKE_CURL_DIR/headers"; fi
    i=$((i + 1))
done
echo called >> "$FAKE_CURL_DIR/calls"
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

json_get() {   # json_get <key>  (reads the recorded payload)
    if command -v jq >/dev/null 2>&1; then jq -r ".$1" "$T/run/payload"
    else python3 -c "import json,sys; print(json.load(open('$T/run/payload'))['$1'])"; fi
}
json_valid() {
    if command -v jq >/dev/null 2>&1; then jq -e . "$T/run/payload" >/dev/null 2>&1
    else python3 -c "import json; json.load(open('$T/run/payload'))" 2>/dev/null; fi
}
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

echo "nothing else posts to Slack"
# One way to post: this repo's shell scripts must not carry their own chat.postMessage call. The one
# exception is check-replica-health.sh, left alone on purpose because it is under active change
# (OPEN-312 / OPEN-313); delete it from this list when it adopts post_slack_alert.
EXEMPT=" check-replica-health.sh "
offenders=""
for f in "$HERE"/*.sh "$HERE"/lib/*.sh; do
    name="$(basename "$f")"
    case "$name" in slack-alert.sh|test-*.sh) continue ;; esac
    case "$EXEMPT" in *" $name "*) continue ;; esac
    if grep -q 'slack.com/api/chat.postMessage' "$f"; then offenders="$offenders $name"; fi
done
check "no script but the helper (and the exempt one) calls chat.postMessage" "${offenders:- none}" " none"
check "the helper carries the CodeBot identity" "$(grep -c 'icon_emoji' "$LIB" | tr -d ' ' | awk '{print ($1>0)}')" "1"

echo
if [ "$FAIL" -eq 0 ]; then
    echo "ALL PASS ($PASS assertions)"
    exit 0
fi
echo "$FAIL FAILED, $PASS passed"
exit 1
