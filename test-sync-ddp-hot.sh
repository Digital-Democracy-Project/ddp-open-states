#!/usr/bin/env bash
# test-sync-ddp-hot.sh — fixture tests for sync-ddp-hot.sh (OPEN-236)
#
# No network, no real bucket: SYNC_AWS_BIN points at a fake `aws` stand-in for each scenario
# (same OS_TEXT_EXTRACT-style substitution convention cloud_archiver.py's own tests use), and
# every other path is redirected via the SYNC_* seams. The mount-safety preflight (pm-review
# round 1) is tested against the REAL /Volumes/DDP-HOT mount when this happens to run on a
# machine that has it -- read-only (a `stat` call) and safe even then, since SYNC_AWS_BIN always
# points at a fake binary that never touches the filesystem, real mount or not. Run it anywhere:
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

assert_file_absent() {  # <path> <label>
    if [ ! -f "$1" ]; then echo "PASS: $2"; PASS=$((PASS + 1))
    else echo "FAIL: $2"; FAIL=$((FAIL + 1)); fi
}

# fake_aws <name> <exit_code> <stdout...> — writes a stand-in `aws` binary that only
# understands `s3 sync SRC DEST --ignore-glacier-warnings`, so a test can assert the wrapper
# invoked it correctly (right bucket, right dest, the flag present) as well as control what it
# returns. Records its own argv for later inspection. Never touches the filesystem, so it's
# safe to point at a real mounted destination too.
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

run_sync() {  # $1=aws_bin $2=log_file $3=lock_file $4=dest_dir
    SYNC_SRC_BUCKET="ddp-bill-archive" \
    SYNC_DEST_DIR="$4" \
    SYNC_LOG_FILE="$2" \
    SYNC_LOCK_FILE="$3" \
    SYNC_AWS_BIN="$1" \
    bash "$SCRIPT" 2>&1
}

echo "=== 0. syntax check ==="
if bash -n "$SCRIPT"; then echo "PASS: bash -n"; PASS=$((PASS + 1)); else echo "FAIL: bash -n"; FAIL=$((FAIL + 1)); fi

# pm-review round 1, HIGH severity: the wrapper refuses to run against a destination that
# doesn't look like its own mounted volume (comparing device ids -- see the script's own
# comment). The happy-path tests below need a destination that DOES pass that check, so they
# use the real DDP-HOT mount if this happens to be running on a machine that has one -- purely
# for the `stat` comparison; SYNC_AWS_BIN is always a fake binary that never writes there.
REAL_MOUNT="/Volumes/DDP-HOT"
mount_available() {
    [ -d "$REAL_MOUNT" ] || return 1
    [ "$(stat -f '%d' "$REAL_MOUNT" 2>/dev/null)" != "$(stat -f '%d' "$(dirname "$REAL_MOUNT")" 2>/dev/null)" ]
}

if mount_available; then
    echo "=== 1. a clean run (only glacier-class objects skipped) reports success ==="
    AWS1=$(fake_aws "aws-ok" 0 "download: s3://ddp-bill-archive/bills/raw/fl/2026/lower/HB1-abcd.pdf to dest/bills/raw/fl/2026/lower/HB1-abcd.pdf")
    LOG1="$TMPDIR_ROOT/ok.log"
    OUT=$(run_sync "$AWS1" "$LOG1" "$TMPDIR_ROOT/ok.lock" "$REAL_MOUNT")
    RC=$?
    assert_num "clean run exits 0" "$RC" -eq 0
    assert_contains "clean run logs ok" "$OUT" "sync-ddp-hot: ok"
    assert_contains "invoked aws s3 sync against the right bucket" "$(cat "$TMPDIR_ROOT/aws-ok.argv")" "s3 sync s3://ddp-bill-archive/bills"
    assert_contains "invoked with --ignore-glacier-warnings" "$(cat "$TMPDIR_ROOT/aws-ok.argv")" "--ignore-glacier-warnings"
    # Found live against the real, already-populated DDP-HOT mount (not a scratch dir): macOS's
    # own metadata directories (Spotlight, Trash, document-revisions, temp items) sit at the
    # ROOT of every mounted volume, several unreadable to a normal process even as their owner.
    # aws s3 sync has to walk the whole destination tree, hits those, and exits 2 -- --exclude
    # does NOT fix this (confirmed live, both directory-contents and bare-name patterns: the
    # local walk still touches the entry before filtering applies). Scoping the sync to the
    # "bills" subtree specifically -- every real object key already starts with "bills/" -- means
    # aws-cli's destination walk never reaches the volume root at all.
    assert_contains "destination is scoped to the bills subtree, not the volume root" "$(cat "$TMPDIR_ROOT/aws-ok.argv")" "$REAL_MOUNT/bills"
    assert_contains "log file records the ok line too" "$(cat "$LOG1")" "sync-ddp-hot: ok"

    echo "=== 2. a real failure (AccessDenied, a bad listing, a local write failure) reports failure ==="
    AWS2=$(fake_aws "aws-fail" 1 "fatal error: An error occurred (AccessDenied) when calling the ListObjectsV2 operation: User: arn:aws:iam::350941939790:user/ddp-scraper is not authorized to perform: s3:ListBucket")
    LOG2="$TMPDIR_ROOT/fail.log"
    OUT=$(run_sync "$AWS2" "$LOG2" "$TMPDIR_ROOT/fail.lock" "$REAL_MOUNT")
    RC=$?
    assert_num "real failure exits non-zero" "$RC" -ne 0
    assert_contains "real failure logs FAILED" "$OUT" "sync-ddp-hot: FAILED"
    assert_contains "the real aws-cli error text still reaches the log" "$OUT" "AccessDenied"

    echo "=== 3. --ignore-glacier-warnings suppresses per-object skip noise, not just real output ==="
    # A fake aws that emits what a large jurisdiction's real run would: one skip warning per
    # historical Deep Archive object. The wrapper doesn't need to filter this itself (that's the
    # whole point of the flag -- verified against awscli 2.36.24's own source, s3handler.py's
    # _warn_glacier: the flag suppresses the warning at its source, before it ever reaches
    # stdout), so this test just proves that IF aws-cli behaves as documented, this wrapper's
    # log stays clean -- it doesn't add its own noise on top.
    AWS3=$(fake_aws "aws-quiet" 0)
    LOG3="$TMPDIR_ROOT/quiet.log"
    OUT=$(run_sync "$AWS3" "$LOG3" "$TMPDIR_ROOT/quiet.lock" "$REAL_MOUNT")
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
    OUT=$(run_sync "$AWS4" "$LOG4" "$LOCK4" "$REAL_MOUNT")
    RC=$?
    assert_num "a tick that loses the lock still exits 0 (not an alertable failure)" "$RC" -eq 0
    assert_contains "skip is logged" "$OUT" "already running"
    assert_file_absent "$TMPDIR_ROOT/aws-should-not-run.argv" "aws was never actually invoked while the lock was held"
    wait "$HOLDER_PID" 2>/dev/null

    echo "=== 5. a second, non-overlapping run after the lock is free runs normally ==="
    AWS5=$(fake_aws "aws-after" 0)
    LOG5="$TMPDIR_ROOT/after.log"
    OUT=$(run_sync "$AWS5" "$LOG5" "$TMPDIR_ROOT/ok.lock" "$REAL_MOUNT")  # reuse test 1's lock, now free
    RC=$?
    assert_num "run after lock is released exits 0" "$RC" -eq 0
    assert_contains "run after lock release actually invokes aws" "$OUT" "sync-ddp-hot: ok"

    echo "=== 6. an aws-cli exit code that happens to numerically match lockf's own EX_TEMPFAIL (75) is still reported as a failure, not misread as a lock skip ==="
    # pm-review round 1 flagged an earlier version of this wrapper (lockf directly wrapping the
    # aws invocation) for exactly this ambiguity: lockf passes through whatever exit code the
    # wrapped command produces once the lock IS acquired, so a bare "was it 75?" check couldn't
    # tell "lockf itself refused" apart from "aws happened to also exit 75." Round 2 removed the
    # ambiguity at the source instead of string-matching around it: the lock is now
    # attempted/held via a plain `lockf -t 0 <fd>` that never runs aws at all, so its result can
    # only ever mean one thing, and aws's own exit code -- 75 or otherwise -- reaches the normal
    # ok/FAILED branch below with no special-casing. This test just confirms that.
    AWS6=$(fake_aws "aws-weird-exit" 75 "some unrelated aws-cli error text, nothing to do with locking")
    LOG6="$TMPDIR_ROOT/weird-exit.log"
    OUT=$(run_sync "$AWS6" "$LOG6" "$TMPDIR_ROOT/weird-exit.lock" "$REAL_MOUNT")
    RC=$?
    assert_num "a colliding-exit-code real failure still exits non-zero" "$RC" -ne 0
    assert_contains "it's reported as FAILED, not as a benign lock skip" "$OUT" "sync-ddp-hot: FAILED"
    assert_not_contains "it is NOT misreported as another sync already running" "$OUT" "already running"

    echo "=== 9. two full instances of the actual script contend for the same lock end to end ==="
    # pm-review round 3: tests 4/5 prove the underlying lockf primitive excludes correctly, but
    # only against a bare `lockf ... sleep` holder, not against a second real invocation of this
    # script -- the thing actually being shipped. This runs the real script twice concurrently:
    # the first with a fake aws that sleeps (simulating a slow in-flight sync), the second with a
    # fake aws that must NOT be invoked. A third invocation, after the first finishes, proves the
    # lock is released, not held forever.
    LOCK9="$TMPDIR_ROOT/e2e.lock"
    AWS9_SLOW=$(fake_aws "aws-e2e-slow" 0)
    # fake_aws's own "exit N" line always comes last; insert a sleep before it so this instance
    # stays inside the aws step (and thus keeps the lock held) long enough for the second
    # instance below to collide with it.
    sed -i '' '$ i\
sleep 2
' "$AWS9_SLOW"
    LOG9A="$TMPDIR_ROOT/e2e-first.log"
    run_sync "$AWS9_SLOW" "$LOG9A" "$LOCK9" "$REAL_MOUNT" > "$TMPDIR_ROOT/e2e-first.out" 2>&1 &
    FIRST_PID=$!
    sleep 0.5  # let the first real instance actually acquire the lock and get into the aws step
    AWS9_SHOULD_NOT_RUN=$(fake_aws "aws-e2e-should-not-run" 0)
    LOG9B="$TMPDIR_ROOT/e2e-second.log"
    OUT9B=$(run_sync "$AWS9_SHOULD_NOT_RUN" "$LOG9B" "$LOCK9" "$REAL_MOUNT")
    RC9B=$?
    assert_num "a second full instance exits 0 while the first is still running" "$RC9B" -eq 0
    assert_contains "the second instance logs the skip" "$OUT9B" "already running"
    assert_file_absent "$TMPDIR_ROOT/aws-e2e-should-not-run.argv" "the second instance's aws was never invoked while the first held the lock"
    wait "$FIRST_PID"
    assert_contains "the first instance completed normally once its aws finished" "$(cat "$TMPDIR_ROOT/e2e-first.out")" "sync-ddp-hot: ok"

    AWS9_THIRD=$(fake_aws "aws-e2e-third" 0)
    LOG9C="$TMPDIR_ROOT/e2e-third.log"
    OUT9C=$(run_sync "$AWS9_THIRD" "$LOG9C" "$LOCK9" "$REAL_MOUNT")
    RC9C=$?
    assert_num "a third instance after the first releases the lock runs normally" "$RC9C" -eq 0
    assert_contains "the third instance actually invokes aws" "$OUT9C" "sync-ddp-hot: ok"

    echo "=== 10. a real lockf failure (can't even create the lock file) is reported as FAILED, not silently skipped as contention ==="
    # pm-review round 3, real bug: an earlier version of this treated ANY nonzero lockf result as
    # "someone else is running" -- collapsing lockf's own EX_CANTCREAT (73, couldn't create the
    # lock file at all -- e.g. a permissions problem) into a silent no-op skip, which would have
    # been worse than the exit-75 ambiguity this whole redesign exists to fix. Pointing the lock
    # file at a directory that doesn't exist reproduces EX_CANTCREAT for real (confirmed
    # empirically: `exec 200>` fails, then `lockf -t 0 200` reports "Bad file descriptor", exit
    # 73) -- not a hand-picked exit code, the actual failure this scenario really produces.
    AWS10=$(fake_aws "aws-should-not-run-bad-lockdir" 0)
    LOG10="$TMPDIR_ROOT/bad-lockdir.log"
    OUT=$(run_sync "$AWS10" "$LOG10" "$TMPDIR_ROOT/no-such-dir-at-all/lock" "$REAL_MOUNT")
    RC=$?
    assert_num "an uncreatable lock file exits non-zero" "$RC" -ne 0
    assert_contains "it's reported as FAILED to acquire the lock, not a benign skip" "$OUT" "FAILED to acquire the lock"
    assert_not_contains "it is NOT misreported as another sync already running" "$OUT" "already running"
    assert_file_absent "$TMPDIR_ROOT/aws-should-not-run-bad-lockdir.argv" "aws was never invoked when the lock file itself couldn't be created"
else
    echo "=== 1-10 SKIPPED: $REAL_MOUNT is not a mounted volume on this machine ==="
fi

echo "=== 7. a missing destination directory is refused, not silently created on the boot disk ==="
AWS7=$(fake_aws "aws-should-not-run-missing-dest" 0)
LOG7="$TMPDIR_ROOT/missing-dest.log"
OUT=$(run_sync "$AWS7" "$LOG7" "$TMPDIR_ROOT/missing-dest.lock" "$TMPDIR_ROOT/does-not-exist/dest")
RC=$?
assert_num "missing destination exits non-zero" "$RC" -ne 0
assert_contains "refusal is logged" "$OUT" "REFUSING to run"
assert_file_absent "$TMPDIR_ROOT/aws-should-not-run-missing-dest.argv" "aws was never invoked against a missing destination"

echo "=== 8. a destination that exists but isn't its own mount point is refused ==="
# The exact hazard this preflight exists for: an ordinary directory (same device as its parent,
# not a separately mounted volume) must never be treated as if it were the real DDP-HOT mount.
mkdir -p "$TMPDIR_ROOT/looks-like-a-plain-dir"
AWS8=$(fake_aws "aws-should-not-run-plain-dir" 0)
LOG8="$TMPDIR_ROOT/plain-dir.log"
OUT=$(run_sync "$AWS8" "$LOG8" "$TMPDIR_ROOT/plain-dir.lock" "$TMPDIR_ROOT/looks-like-a-plain-dir")
RC=$?
assert_num "a same-device destination exits non-zero" "$RC" -ne 0
assert_contains "refusal is logged" "$OUT" "REFUSING to run"
assert_file_absent "$TMPDIR_ROOT/aws-should-not-run-plain-dir.argv" "aws was never invoked against a same-device destination"

echo ""
echo "RESULT: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] && { echo "ALL PASS"; exit 0; } || exit 1
