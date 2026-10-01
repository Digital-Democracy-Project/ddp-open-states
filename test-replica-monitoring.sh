#!/usr/bin/env bash
# test-replica-monitoring.sh — fixture tests for the RDS -> Mac replica monitoring (OPEN-312):
#   check-replica-health.sh                        (alert state machine + scheduling glue)
#   ops/postgres-replica/local/replica-status.sh   (stale-receipt check, RDS-side via container)
#   ops/postgres-replica/local/compare-schema.sh   (table list from the publication, set comparison)
#
# No network, no database, no production paths: `docker` is a stub on PATH that answers from fixture
# files, every state/log path is a mktemp dir, and Slack is REPLICA_DRY_RUN=1. Run it anywhere:
#     bash test-replica-monitoring.sh
# Exits 0 with "ALL PASS" or 1 after listing every failing assertion.

set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
GLUE="$HERE/check-replica-health.sh"
STATUS="$HERE/ops/postgres-replica/local/replica-status.sh"
COMPARE="$HERE/ops/postgres-replica/local/compare-schema.sh"
T=$(mktemp -d /tmp/replica-monitoring-test.XXXXXX)
trap 'rm -rf "$T"' EXIT
PASS=0; FAIL=0

assert_contains() {  # <label> <haystack> <needle>
    if printf '%s' "$2" | grep -qF -- "$3"; then echo "PASS: $1"; PASS=$((PASS + 1))
    else echo "FAIL: $1 — expected to find: $3"; echo "--- output was:"; echo "$2"; FAIL=$((FAIL + 1)); fi
}
assert_not_contains() {  # <label> <haystack> <needle>
    if printf '%s' "$2" | grep -qF -- "$3"; then echo "FAIL: $1 — expected NOT to find: $3"; echo "--- output was:"; echo "$2"; FAIL=$((FAIL + 1))
    else echo "PASS: $1"; PASS=$((PASS + 1)); fi
}
assert_eq() {  # <label> <actual> <expected>
    if [ "$2" = "$3" ]; then echo "PASS: $1"; PASS=$((PASS + 1))
    else echo "FAIL: $1 — expected '$3', got '$2'"; FAIL=$((FAIL + 1)); fi
}
assert_file() {  # <label> <path> <exists|absent>
    local ok=0
    if [ "$3" = exists ]; then [ -e "$2" ] && ok=1; else [ ! -e "$2" ] && ok=1; fi
    if [ "$ok" -eq 1 ]; then echo "PASS: $1"; PASS=$((PASS + 1))
    else echo "FAIL: $1 — $2 should be $3"; FAIL=$((FAIL + 1)); fi
}

# =====================================================================================================
# Part 1: check-replica-health.sh (assessors replaced by canned scripts)
# =====================================================================================================
G="$T/glue"; mkdir -p "$G/last-run"
NOW=1800000000

cat > "$G/status.sh" <<'EOF'
#!/usr/bin/env bash
cat "$GLUE_STATUS_FILE"
EOF
cat > "$G/compare.sh" <<'EOF'
#!/usr/bin/env bash
cat "$GLUE_COMPARE_FILE"; exit "$(cat "$GLUE_COMPARE_RC")"
EOF
echo "0" > "$G/compare.rc"

set_status() {  # <STATUS> <detail>
    printf '== Overall status: %s ==\n%s\n' "$1" "$2" > "$G/status.out"
}
run_glue() {  # <now_offset_s> [extra env assignments via env(1) args...]
    local off="$1"; shift
    env REPLICA_LAST_RUN_DIR="$G/last-run" REPLICA_LOG_FILE="$G/test.log" REPLICA_DRY_RUN=1 \
        REPLICA_NOW_EPOCH=$(( NOW + off )) REPLICA_DB=fixture_db \
        REPLICA_STATUS_CMD="$G/status.sh" REPLICA_COMPARE_CMD="$G/compare.sh" \
        GLUE_STATUS_FILE="$G/status.out" GLUE_COMPARE_FILE="$G/compare.out" GLUE_COMPARE_RC="$G/compare.rc" \
        "$@" bash "$GLUE" 2>&1
}

echo "--- glue: replica verdicts"
set_status HEALTHY "publisher_wal_lag_bytes=0"
out=$(run_glue 0 env -u RDS_HOST -u RDS_REPLICATION_PASSWORD)
assert_eq "healthy run prints nothing" "$out" ""
assert_file "healthy run leaves no state file" "$G/last-run/replica-health.replica.state" absent

set_status DISCONNECTED "no message from the publisher for 900s"
out=$(run_glue 300)
assert_not_contains "first bad run does not alert (one blip never pages)" "$out" "DRY_RUN slack"
assert_file "first bad run records state" "$G/last-run/replica-health.replica.state" exists

out=$(run_glue 600)
assert_contains "second consecutive bad run alerts" "$out" "DRY_RUN slack: ⚠️ *Mac replica of RDS — replica is bad:* DISCONNECTED"
assert_contains "alert carries the detail" "$out" "no message from the publisher for 900s"

out=$(run_glue 900)
assert_not_contains "third bad run inside the reminder window is silent" "$out" "DRY_RUN slack"

out=$(run_glue $(( 600 + 21600 )))
assert_contains "after REMIND_S a reminder goes out" "$out" "is STILL bad"

set_status HEALTHY "ok"
out=$(run_glue $(( 600 + 21600 + 300 )))
assert_contains "recovery message posts" "$out" "replica recovered"
assert_file "recovery clears the state file" "$G/last-run/replica-health.replica.state" absent

echo "--- glue: INCOMPLETE counts as ok; garbage counts as bad"
set_status INCOMPLETE "local apply worker running, RDS-side not checked"
out=$(run_glue 0); run_glue 300 >/dev/null
assert_file "INCOMPLETE is not treated as a failure" "$G/last-run/replica-health.replica.state" absent
printf 'something unexpected\n' > "$G/status.out"
run_glue 0 >/dev/null; out=$(run_glue 300)
assert_contains "unparseable assessor output alerts rather than passing silently" "$out" "could not read a status"
set_status HEALTHY "ok"; run_glue 600 >/dev/null   # clear

echo "--- glue: alert text is JSON-safe"
set_status BROKEN 'RDS-side query failed: "quoted" and back\slash
second line'
run_glue 0 >/dev/null; out=$(run_glue 300)
assert_not_contains "double quotes stripped from detail" "$out" '"quoted"'
assert_not_contains "backslashes stripped from detail" "$out" 'back\slash'
set_status HEALTHY "ok"; run_glue 600 >/dev/null

echo "--- glue: corrupt state file resets instead of crashing"
echo "garbage here" > "$G/last-run/replica-health.replica.state"
set_status DISCONNECTED "x"
out=$(run_glue 0)
assert_not_contains "corrupt state does not alert or crash on first bad run" "$out" "DRY_RUN slack"
set_status HEALTHY "ok"; run_glue 300 >/dev/null

echo "--- glue: schema stage"
set_status HEALTHY "ok"
printf 'PASS: all 47 published tables are subscribed and match\n' > "$G/compare.out"; echo 0 > "$G/compare.rc"
rm -f "$G/last-run/replica-health.schema.checked"
out=$(run_glue 0 env -u RDS_HOST -u RDS_REPLICATION_PASSWORD)
assert_file "no RDS credential: schema stage skipped" "$G/last-run/replica-health.schema.checked" absent

printf 'FAIL: published on RDS but NOT subscribed locally:\n  opencivicdata_newtable\n' > "$G/compare.out"; echo 1 > "$G/compare.rc"
out=$(run_glue 0 env RDS_HOST=rds.example RDS_REPLICATION_PASSWORD=pw)
assert_contains "schema drift alerts on the FIRST failing check" "$out" "schema is bad"
assert_contains "schema alert names the problem" "$out" "NOT subscribed locally"
assert_file "schema stage records when it last ran" "$G/last-run/replica-health.schema.checked" exists
out=$(run_glue 3600 env RDS_HOST=rds.example RDS_REPLICATION_PASSWORD=pw)
assert_not_contains "schema stage is throttled inside SCHEMA_EVERY_S" "$out" "DRY_RUN slack"
out=$(run_glue $(( 6 * 3600 + 60 )) env RDS_HOST=rds.example RDS_REPLICATION_PASSWORD=pw)
assert_not_contains "still-bad schema is not re-posted before the daily reminder" "$out" "DRY_RUN slack"
printf 'PASS: all 47 published tables match\n' > "$G/compare.out"; echo 0 > "$G/compare.rc"
out=$(run_glue $(( 12 * 3600 + 120 )) env RDS_HOST=rds.example RDS_REPLICATION_PASSWORD=pw)
assert_contains "schema recovery posts" "$out" "schema recovered"

echo "--- glue: a message Slack did not accept must not count as delivered (pm-review)"
CB="$T/bin-curl"; mkdir -p "$CB"
cat > "$CB/curl" <<'EOF'
#!/usr/bin/env bash
echo "$*" >> "$CURL_LOG"; cat "$CURL_REPLY"
EOF
chmod +x "$CB/curl"
echo '{"ok":false,"error":"invalid_auth"}' > "$G/curl.reply"; : > "$G/curl.log"
run_glue_live() {  # <now_offset_s> [env args]
    local off="$1"; shift
    env REPLICA_LAST_RUN_DIR="$G/last-run" REPLICA_LOG_FILE="$G/test.log" REPLICA_DRY_RUN=0 \
        REPLICA_NOW_EPOCH=$(( NOW + off )) REPLICA_DB=fixture_db REPLICA_SLACK_TOKEN=xoxb-test \
        REPLICA_STATUS_CMD="$G/status.sh" REPLICA_COMPARE_CMD="$G/compare.sh" \
        GLUE_STATUS_FILE="$G/status.out" CURL_LOG="$G/curl.log" CURL_REPLY="$G/curl.reply" \
        PATH="$CB:$PATH" "$@" bash "$GLUE" 2>&1
}
rm -f "$G/last-run/"replica-health.*
set_status DISCONNECTED "publisher gone"
run_glue_live 0 >/dev/null; out=$(run_glue_live 300)
assert_contains "Slack HTTP-200 ok:false is reported as not delivered" "$out" "Slack did not accept the message"
assert_eq "a rejected alert leaves last_alert_epoch at 0 (not recorded as sent)" "$(awk '{print $2}' "$G/last-run/replica-health.replica.state")" "0"
before=$(wc -l < "$G/curl.log")
run_glue_live 600 >/dev/null
assert_eq "the next run retries the alert instead of staying silent for 6h" "$(( $(wc -l < "$G/curl.log") - before ))" "1"
echo '{"ok":true}' > "$G/curl.reply"
run_glue_live 900 >/dev/null
assert_eq "once Slack accepts, the alert is recorded as sent" "$(awk '{print ($2>0)}' "$G/last-run/replica-health.replica.state")" "1"
before=$(wc -l < "$G/curl.log"); run_glue_live 1200 >/dev/null
assert_eq "and is then silent (no duplicate within the reminder window)" "$(( $(wc -l < "$G/curl.log") - before ))" "0"

echo '{"ok":false,"error":"channel_not_found"}' > "$G/curl.reply"
set_status HEALTHY "ok"
out=$(run_glue_live 1500)
assert_contains "a recovery Slack rejects is not silently dropped" "$out" "Slack did not accept the message"
assert_file "...and its state is kept so the recovery is retried" "$G/last-run/replica-health.replica.state" exists
echo '{"ok":true}' > "$G/curl.reply"; run_glue_live 1800 >/dev/null
assert_file "recovery delivered on the retry: state cleared" "$G/last-run/replica-health.replica.state" absent

rm -f "$G/last-run/"replica-health.*
set_status DISCONNECTED "publisher gone"
run_glue_live 0 env REPLICA_SLACK_TOKEN= >/dev/null; out=$(run_glue_live 300 env REPLICA_SLACK_TOKEN=)
assert_contains "no Slack token: reported as not delivered" "$out" "no Slack token available"
assert_eq "no Slack token: alert not recorded as sent" "$(awk '{print $2}' "$G/last-run/replica-health.replica.state")" "0"
rm -f "$G/last-run/"replica-health.*; set_status HEALTHY "ok"

echo "--- glue: tabs and other control characters are stripped too (pm-review)"
set_status BROKEN "$(printf 'tab\there bell\a end')"
run_glue 0 >/dev/null; out=$(run_glue 300)
assert_not_contains "no tab in the alert text" "$out" "$(printf '\t')"
assert_not_contains "no bell character in the alert text" "$out" "$(printf '\a')"
assert_contains "the rest of the text survives" "$out" "tab here bell end"
set_status HEALTHY "ok"; run_glue 600 >/dev/null; rm -f "$G/last-run/"replica-health.*

echo "--- glue: runs under launchd's bare environment (no HOME, minimal PATH) -- found live 2026-10-01"
# The health-monitor daemon gets PATH=/usr/bin:/bin:/usr/sbin:/sbin and no HOME. With `set -u` the
# first $HOME reference used to abort the whole script silently, so the monitor never ran at all.
rm -f "$G/last-run/"replica-health.*
set_status DISCONNECTED "daemon-env check"
run_glue_bare() {  # <now_offset_s>
    env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin \
        REPLICA_LAST_RUN_DIR="$G/last-run" REPLICA_LOG_FILE="$G/test.log" REPLICA_DRY_RUN=1 \
        REPLICA_NOW_EPOCH=$(( NOW + $1 )) REPLICA_DB=fixture_db REPLICA_SLACK_TOKEN=x \
        REPLICA_STATUS_CMD="$G/status.sh" GLUE_STATUS_FILE="$G/status.out" \
        bash "$GLUE" 2>&1
}
out=$(run_glue_bare 0)
assert_not_contains "no HOME: does not abort on an unbound variable" "$out" "unbound variable"
assert_file "no HOME: the check actually ran (recorded its first bad run)" "$G/last-run/replica-health.replica.state" exists
out=$(run_glue_bare 300)
assert_contains "no HOME: second bad run alerts as normal" "$out" "DRY_RUN slack"
set_status HEALTHY "ok"; run_glue_bare 600 >/dev/null; rm -f "$G/last-run/"replica-health.*

echo "--- glue: discovery failures alert (docker stub)"
B="$T/bin-glue"; mkdir -p "$B"
cat > "$B/docker" <<'EOF'
#!/usr/bin/env bash
case "$STUB_MODE" in
  docker_down) echo "Cannot connect to the Docker daemon" >&2; exit 1 ;;
  no_sub) exit 0 ;;   # psql succeeded, zero rows
esac
EOF
chmod +x "$B/docker"
rm -f "$G/last-run/"replica-health.*
for mode in docker_down no_sub; do
    run_glue_nodb() {
        env REPLICA_LAST_RUN_DIR="$G/last-run" REPLICA_LOG_FILE="$G/test.log" REPLICA_DRY_RUN=1 \
            REPLICA_NOW_EPOCH=$(( NOW + $1 )) REPLICA_STATUS_CMD="$G/status.sh" GLUE_STATUS_FILE="$G/status.out" \
            STUB_MODE="$mode" PATH="$B:$PATH" bash "$GLUE" 2>&1
    }
    run_glue_nodb 0 >/dev/null; out=$(run_glue_nodb 300)
    case "$mode" in
        docker_down) assert_contains "Postgres container unreachable alerts" "$out" "cannot query local Postgres container" ;;
        no_sub)      assert_contains "missing subscription alerts" "$out" "no subscription named ddp_legbot_subscription" ;;
    esac
    rm -f "$G/last-run/"replica-health.*
done

# =====================================================================================================
# Part 2: replica-status.sh (docker stub answers each query from environment fixtures)
# =====================================================================================================
S="$T/status-bin"; mkdir -p "$S"
cat > "$S/docker" <<'EOF'
#!/usr/bin/env bash
# Answers replica-status.sh's docker calls. Fixtures arrive through STUB_* env vars.
all="$*"
case "$all" in
  *pg_isready*)            exit 0 ;;
  *"SELECT subenabled"*)   echo "${STUB_SUBENABLED:-t}" ;;
  *"FROM pg_stat_subscription"*) [ -n "${STUB_LOCAL_STATE:-}" ] && echo "$STUB_LOCAL_STATE"; exit 0 ;;
  *pg_replication_slots*)  [ "${STUB_RDS_FAIL:-0}" = 1 ] && { echo "connection refused" >&2; exit 2; }
                           [ -n "${STUB_RDS_STATE:-}" ] && echo "$STUB_RDS_STATE"; exit 0 ;;
  *HGET*)                  exit 0 ;;
  *HSET*)                  exit 0 ;;
esac
EOF
chmod +x "$S/docker"

run_status() {  # env assignments as args
    env PATH="$S:$PATH" REDIS_CONTAINER=stub "$@" bash "$STATUS" fixture_db 2>&1
}
LOCAL_FRESH="1234|92/B8|92/B8|2026-09-30 23:14:53+00|4"
LOCAL_STALE="1234|92/B8|92/B8|2026-09-30 22:00:00+00|4000"
LOCAL_NEW="1234|92/B8|92/B8|null|null"

echo "--- replica-status: local-only"
out=$(run_status STUB_LOCAL_STATE="$LOCAL_FRESH")
assert_contains "fresh receipt, no RDS URL: INCOMPLETE (not a false all-clear)" "$out" "Overall status: INCOMPLETE"
out=$(run_status STUB_LOCAL_STATE="$LOCAL_STALE")
assert_contains "worker exists but silent for 4000s: DISCONNECTED" "$out" "Overall status: DISCONNECTED"
assert_contains "detail names the silence" "$out" "no message from the publisher for 4000s"
out=$(run_status STUB_LOCAL_STATE="$LOCAL_STALE" RECEIPT_STALE_S=5000)
assert_contains "RECEIPT_STALE_S is honoured" "$out" "Overall status: INCOMPLETE"
out=$(run_status STUB_LOCAL_STATE="$LOCAL_NEW")
assert_contains "no message yet (worker just started) is not stale" "$out" "Overall status: INCOMPLETE"
out=$(run_status STUB_LOCAL_STATE="")
assert_contains "no apply worker row: DISCONNECTED" "$out" "Overall status: DISCONNECTED"
out=$(run_status STUB_LOCAL_STATE="$LOCAL_FRESH" RECEIPT_STALE_S=abc)
assert_contains "non-integer RECEIPT_STALE_S fails clearly" "$out" "RECEIPT_STALE_S must be a positive integer"

echo "--- replica-status: RDS-side through the container"
out=$(run_status STUB_LOCAL_STATE="$LOCAL_FRESH" RDS_MONITORING_DATABASE_URL="postgresql://x" STUB_RDS_STATE="1024|12 MB|t")
assert_contains "caught up, slot active: HEALTHY" "$out" "Overall status: HEALTHY"
out=$(run_status STUB_LOCAL_STATE="$LOCAL_FRESH" RDS_MONITORING_DATABASE_URL="postgresql://x" STUB_RDS_STATE="999999999|900 MB|t")
assert_contains "lag over threshold: LAGGING" "$out" "Overall status: LAGGING"
out=$(run_status STUB_LOCAL_STATE="$LOCAL_FRESH" RDS_MONITORING_DATABASE_URL="postgresql://x" STUB_RDS_STATE="1024|12 MB|f")
assert_contains "slot inactive on RDS: DISCONNECTED" "$out" "Overall status: DISCONNECTED"
out=$(run_status STUB_LOCAL_STATE="$LOCAL_FRESH" RDS_MONITORING_DATABASE_URL="postgresql://x" STUB_RDS_FAIL=1)
assert_contains "RDS query failing: BROKEN" "$out" "Overall status: BROKEN"
out=$(run_status STUB_LOCAL_STATE="$LOCAL_STALE" RDS_MONITORING_DATABASE_URL="postgresql://x" STUB_RDS_STATE="1024|12 MB|t")
assert_contains "RDS says caught up but nothing received for 4000s: DISCONNECTED, not HEALTHY" "$out" "Overall status: DISCONNECTED"

# =====================================================================================================
# Part 3: compare-schema.sh (table list from the publication; docker stub as RDS and local)
# =====================================================================================================
C="$T/compare-bin"; FX="$T/compare-fx"; mkdir -p "$C" "$FX"
cat > "$C/docker" <<'EOF'
#!/usr/bin/env bash
# RDS calls carry `-e PGPASSWORD`; local calls do not. Fixtures live in $FX.
all="$*"
side=local; case "$all" in *"-e PGPASSWORD"*) side=rds ;; esac
case "$all" in
  *pg_publication_tables*)  [ -f "$FX/publication_fail" ] && { echo "could not connect" >&2; exit 2; }; cat "$FX/published"; exit 0 ;;
  *pg_subscription_rel*)    cat "$FX/subscribed"; exit 0 ;;
esac
table=$(printf '%s' "$all" | sed -n "s/.*relname = '\([^']*\)'.*/\1/p")
[ -n "$table" ] && [ -f "$FX/${side}_cols_$table" ] && cat "$FX/${side}_cols_$table"
exit 0
EOF
chmod +x "$C/docker"
run_compare() {
    env PATH="$C:$PATH" FX="$FX" RDS_HOST=rds.example RDS_REPLICATION_PASSWORD=pw bash "$COMPARE" fixture_db 2>&1
    echo "exit=$?"
}
reset_fx() {
    rm -f "$FX"/*
    printf 'opencivicdata_bill\nopencivicdata_person\n' > "$FX/published"
    printf 'opencivicdata_bill\nopencivicdata_person\n' > "$FX/subscribed"
    for t in opencivicdata_bill opencivicdata_person; do
        printf 'id|character varying|true\ntitle|text|true\n' > "$FX/rds_cols_$t"
        cp "$FX/rds_cols_$t" "$FX/local_cols_$t"
    done
}

echo "--- compare-schema"
reset_fx; out=$(run_compare)
assert_contains "matching sets and columns: PASS with a dynamic table count" "$out" "all 2 published tables are subscribed and match"
assert_contains "exit 0 when everything matches" "$out" "exit=0"

reset_fx; printf 'opencivicdata_person\nopencivicdata_bill\n' > "$FX/published"; out=$(run_compare)
assert_contains "same tables in a different ORDER (two databases' collations disagree) still PASS" "$out" "all 2 published tables are subscribed and match"
assert_contains "and exit 0" "$out" "exit=0"

reset_fx; printf 'opencivicdata_bill\nopencivicdata_person\nopencivicdata_newtable\n' > "$FX/published"; out=$(run_compare)
assert_contains "table published but never subscribed is reported" "$out" "published on RDS but NOT subscribed locally"
assert_contains "it names the table" "$out" "opencivicdata_newtable"
assert_contains "it names the fix" "$out" "REFRESH PUBLICATION"
assert_contains "and fails" "$out" "exit=1"

reset_fx; printf 'opencivicdata_bill\nopencivicdata_person\nopencivicdata_old\n' > "$FX/subscribed"; out=$(run_compare)
assert_contains "table subscribed but no longer published is reported" "$out" "subscribed locally but no longer in the RDS publication"

reset_fx; printf 'id|character varying|true\ntitle|text|true\nnewcol|text|false\n' > "$FX/rds_cols_opencivicdata_person"; out=$(run_compare)
assert_contains "a column present on RDS but missing locally is caught" "$out" "column mismatch"
assert_contains "and fails" "$out" "exit=1"

reset_fx; printf 'opencivicdata_bill\nbad name; drop table x\n' > "$FX/published"; out=$(run_compare)
assert_contains "an unexpected table name from RDS is refused, never interpolated" "$out" "refusing unexpected table name"

reset_fx; touch "$FX/publication_fail"; out=$(run_compare)
assert_contains "unreadable publication fails loudly" "$out" "could not read publication"
assert_contains "and exits non-zero" "$out" "exit=1"

reset_fx; : > "$FX/published"; out=$(run_compare)
assert_contains "an empty publication is a failure, not a pass" "$out" "lists no tables"

echo
if [ "$FAIL" -eq 0 ]; then echo "ALL PASS ($PASS assertions)"; exit 0
else echo "$FAIL FAILED, $PASS passed"; exit 1; fi
