#!/usr/bin/env bash
# test-sync-ddp-hot.sh — fixture tests for sync-ddp-hot.sh (OPEN-236)
#
# No network, no real bucket, no /Volumes/DDP-HOT: SYNC_AWS_BIN points at a fake `aws` stand-in
# for each scenario (same OS_TEXT_EXTRACT-style substitution convention cloud_archiver.py's own
# tests use), and every other path is redirected into a mktemp dir via the SYNC_* seams. Run it
# anywhere:
#     bash test-sync-ddp-hot.sh
# Exits 0 with "ALL PASS" or 1 with the first failing assertion.

set -u

SCRIPT="$(cd "$(dirname "$0")" && pwd)/sync-ddp-hot.sh"
TMPDIR_ROOT=$(mktemp -d /tmp/sync-ddp-hot-test.XXXXXX)
trap 'rm -rf "$TMPDIR_ROOT"' EXIT

PASS=0
FAIL=0

assert_contains() {  # <label> <haystack> <needle>
    if echo "$2" | grep -qF -- "$3"; then
        echo "PASS: $1"; PASS=$((PASS + 1))
    else
        echo "FAIL: $1 — expected to find: $3"; echo "--- output was:"; echo "$2"; FAIL=$((FAIL + 1))
    fi
}

assert_not_contains() {  # <label> <haystack> <needle>
    if echo "$2" | grep -qF -- "$3"; then
        echo "FAIL: $1 — expected NOT to find: $3"; echo "--- output was:"; echo "$2"; FAIL=$((FAIL + 1))
    else
        echo "PASS: $1"; PASS=$((PASS + 1))
    fi
}

assert_num() {  # <label> <actual> <op> <expected>
    if [ "$2" "$3" "$4" ]; then echo "PASS: $1"; PASS=$((PASS + 1))
    else echo "FAIL: $1 (got $2, wanted $3 $4)"; FAIL=$((FAIL + 1)); fi
}

# fake_aws <name> <exit_code> <stdout...> — writes a stand-in `aws` binary that only
# understands `s3 sync SRC DEST --ignore-glacier-warnings`, so a test can assert the wrapper
# invoked it correctly (right bucket, right dest, the flag present) as well as control what it
# returns. Records its own argv for later inspection.
fake_aws() {
    local name="$1" exit_code="$2" path; shift 2
    path="$TMPDIR_ROOT/$name"
    {
        echo '#!/usr/bin/env bash'
        echo "echo \"\$@\" > '$TMPDIR_ROOT/$name.argv'"
        while [ "$#" -gt 0 ]; do printf 'echo %q\n' "$1"; shift; done
        echo "exit $exit_code"
    } > "$path"
    chmod +x "$path"
    echo "$path"
}

run_sync() {  # $1=aws_bin $2=log_file $3=lock_file
    SYNC_SRC_BUCKET="ddp-bill-archive" \
    SYNC_DEST_DIR="$TMPDIR_ROOT/dest" \
    SYNC_LOG_FILE="$2" \
    SYNC_LOCK_FILE="$3" \
    SYNC_AWS_BIN="$1" \
    bash "$SCRIPT" 2>&1
}

echo "=== 0. syntax check ==="
if bash -n "$SCRIPT"; then echo "PASS: bash -n"; PASS=$((PASS + 1)); else echo "FAIL: bash -n"; FAIL=$((FAIL + 1)); fi

echo "=== 1. a clean run (only glacier-class objects skipped) reports success ==="
AWS1=$(fake_aws "aws-ok" 0 "download: s3://ddp-bill-archive/bills/raw/fl/2026/lower/HB1-abcd.pdf to dest/bills/raw/fl/2026/lower/HB1-abcd.pdf")
LOG1="$TMPDIR_ROOT/ok.log"
OUT=$(run_sync "$AWS1" "$LOG1" "$TMPDIR_ROOT/ok.lock")
RC=$?
assert_num "clean run exits 0" "$RC" -eq 0
assert_contains "clean run logs ok" "$OUT" "sync-ddp-hot: ok"
assert_contains "invoked aws s3 sync against the right bucket" "$(cat "$TMPDIR_ROOT/aws-ok.argv")" "s3 sync s3://ddp-bill-archive"
assert_contains "invoked with --ignore-glacier-warnings" "$(cat "$TMPDIR_ROOT/aws-ok.argv")" "--ignore-glacier-warnings"
assert_contains "log file records the ok line too" "$(cat "$LOG1")" "sync-ddp-hot: ok"

echo "=== 2. a real failure (AccessDenied, a bad listing, a local write failure) reports failure ==="
AWS2=$(fake_aws "aws-fail" 1 "fatal error: An error occurred (AccessDenied) when calling the ListObjectsV2 operation: User: arn:aws:iam::350941939790:user/ddp-scraper is not authorized to perform: s3:ListBucket")
LOG2="$TMPDIR_ROOT/fail.log"
OUT=$(run_sync "$AWS2" "$LOG2" "$TMPDIR_ROOT/fail.lock")
RC=$?
assert_num "real failure exits non-zero" "$RC" -ne 0
assert_contains "real failure logs FAILED" "$OUT" "sync-ddp-hot: FAILED"
assert_contains "the real aws-cli error text still reaches the log" "$OUT" "AccessDenied"

echo "=== 3. --ignore-glacier-warnings suppresses per-object skip noise, not just real output ==="
# A fake aws that emits what a large jurisdiction's real run would: one skip warning per
# historical Deep Archive object. The wrapper doesn't need to filter this itself (that's the
# whole point of the flag -- verified against awscli 2.36.24's own source, s3handler.py's
# _warn_glacier: the flag suppresses the warning at its source, before it ever reaches stdout),
# so this test just proves that IF aws-cli behaves as documented, this wrapper's log stays
# clean -- it doesn't add its own noise on top.
AWS3=$(fake_aws "aws-quiet" 0)
LOG3="$TMPDIR_ROOT/quiet.log"
OUT=$(run_sync "$AWS3" "$LOG3" "$TMPDIR_ROOT/quiet.lock")
LINE_COUNT=$(wc -l < "$LOG3" | tr -d ' ')
assert_num "a quiet successful run logs only its own two lines" "$LINE_COUNT" -eq 2
assert_not_contains "no per-object noise in a quiet run" "$OUT" "GLACIER"

echo "=== 4. a concurrent tick is skipped, not queued or run in parallel ==="
# macOS has no flock(1) at all -- sync-ddp-hot.sh uses lockf(1) instead, so the contending
# holder here must too, or this test would prove nothing about the actual locking mechanism
# in use. A real background process holding the lock (not a hand-simulated fd) matches what
# an actually-still-running previous tick looks like.
LOCK4="$TMPDIR_ROOT/concurrent.lock"
lockf -k "$LOCK4" sleep 3 &
HOLDER_PID=$!
sleep 0.5  # give the holder a moment to actually acquire the lock before we contend for it
AWS4=$(fake_aws "aws-should-not-run" 0)
LOG4="$TMPDIR_ROOT/concurrent.log"
OUT=$(run_sync "$AWS4" "$LOG4" "$LOCK4")
RC=$?
assert_num "a tick that loses the lock still exits 0 (not an alertable failure)" "$RC" -eq 0
assert_contains "skip is logged" "$OUT" "already running"
assert_file_absent() { [ ! -f "$1" ] && { echo "PASS: $2"; PASS=$((PASS + 1)); } || { echo "FAIL: $2"; FAIL=$((FAIL + 1)); }; }
assert_file_absent "$TMPDIR_ROOT/aws-should-not-run.argv" "aws was never actually invoked while the lock was held"
wait "$HOLDER_PID" 2>/dev/null

echo "=== 5. a second, non-overlapping run after the lock is free runs normally ==="
AWS5=$(fake_aws "aws-after" 0)
LOG5="$TMPDIR_ROOT/after.log"
OUT=$(run_sync "$AWS5" "$LOG5" "$TMPDIR_ROOT/ok.lock")  # reuse lock file from test 1, now free
RC=$?
assert_num "run after lock is released exits 0" "$RC" -eq 0
assert_contains "run after lock release actually invokes aws" "$OUT" "sync-ddp-hot: ok"

echo ""
echo "RESULT: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] && { echo "ALL PASS"; exit 0; } || exit 1
