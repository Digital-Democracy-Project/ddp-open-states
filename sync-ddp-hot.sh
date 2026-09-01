#!/usr/bin/env bash
# sync-ddp-hot.sh — periodic `aws s3 sync` from ddp-bill-archive down to DDP-HOT.
#
# OPEN-236 / OPEN-192: the cloud archiver's single S3 write (OPEN-238) never touches DDP-HOT
# directly. DDP-HOT is now a synced MIRROR of ddp-bill-archive, kept current by this job on a
# periodic schedule -- intended: every 15-30 min via cron -- rather than written to in real
# time. See PLAN-scraper-execution-migration.md's "How DDP-HOT gets populated" section.
#
# Deliberately NOT installed as a live crontab entry by this change -- OPEN-236 is build+test
# only. To install for real, once the IAM gap below is resolved:
#   */15 * * * * /Users/agentsmith/Developer/repos/ddp-open-states/sync-ddp-hot.sh
#
# --ignore-glacier-warnings is the whole trick, not a custom log parser: ddp-bill-archive holds
# ~192,487 historical Deep Archive objects that aws s3 sync can never download. Without the
# flag, every one of those prints its own WARNING line on every single run forever (a permanent,
# guaranteed log flood) and the command exits 2. With it, those objects are still skipped, but
# silently -- no warning line, no effect on exit code -- while every OTHER failure mode
# (permission denied, a listing error, a local disk write failure) still surfaces through
# aws-cli's normal fatal-error path and a non-zero exit code, completely unaffected. Verified by
# reading awscli's own source (customizations/s3/s3handler.py's _warn_glacier, awscli 2.36.24),
# not assumed from the --help text alone.
#
# KNOWN GAP, found while building this, not yet resolved: the `ddp-scraper` IAM user (the same
# one already used for the archiver's own S3 PutObject calls, see .env) does not have
# s3:ListBucket / s3:GetBucketLocation on ddp-bill-archive -- confirmed with a live AccessDenied
# response during this ticket's own testing, not assumed. `aws s3 sync` cannot enumerate a
# bucket's contents without ListBucket, so this job cannot actually run under that identity as
# configured today. It needs either a broadened policy for ddp-scraper (read-only S3 verbs on
# this one bucket) or a separate, purpose-scoped read identity -- an AWS IAM change, which is a
# shared-infrastructure decision for a human to make, not something this ticket implements.
#
# No --delete: this only ever ADDS or REPLACES files, never removes one from DDP-HOT that fell
# out of the bucket (deletion propagation is not something OPEN-236 asked for). It does still
# overwrite a local file at a path that also exists in S3 with different content -- that's the
# whole point of a mirror, not an oversight -- so DDP-HOT is authoritative-from-S3 for any path
# this job's key convention covers (bills/raw/...); anything placed at a colliding path by some
# other local process is not preserved.
#
# Test seams (env vars), same convention as check-scrape-staleness.sh's STALE_* seam --
# overridable so test-sync-ddp-hot.sh never touches a real bucket or /Volumes/DDP-HOT:
#   SYNC_SRC_BUCKET   default: ddp-bill-archive
#   SYNC_DEST_DIR     default: $ARCHIVE_ROOT_DIR, falling back to /Volumes/DDP-HOT
#   SYNC_LOG_FILE     default: ~/Developer/repos/ddp-open-states/logs/sync-ddp-hot.log
#   SYNC_LOCK_FILE    default: /tmp/ddp-sync-ddp-hot.lock (a lockf(1) lock file, not a flock fd)
#   SYNC_AWS_BIN      default: aws -- point at a fake binary to test without real AWS calls

set -uo pipefail

SRC_BUCKET="${SYNC_SRC_BUCKET:-ddp-bill-archive}"
DEST_DIR="${SYNC_DEST_DIR:-${ARCHIVE_ROOT_DIR:-/Volumes/DDP-HOT}}"
LOG_FILE="${SYNC_LOG_FILE:-$HOME/Developer/repos/ddp-open-states/logs/sync-ddp-hot.log}"
LOCK_FILE="${SYNC_LOCK_FILE:-/tmp/ddp-sync-ddp-hot.lock}"
AWS_BIN="${SYNC_AWS_BIN:-aws}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

mkdir -p "$(dirname "$LOG_FILE")"

# pm-review round 1, HIGH severity, real: an unmounted /Volumes/DDP-HOT is just an ordinary --
# usually nonexistent, but perfectly writable -- directory on the Mac's own boot disk. Without
# this check, if the external drive were ever unmounted, renamed, or not yet attached when a
# cron tick fires, aws s3 sync would happily create that path and start filling the SYSTEM disk
# with the archive's contents, with no error at all. Comparing device IDs (stat -f %d) against
# the parent directory is the standard portable way to detect "is this its own mount point" on
# macOS -- there's no mountpoint(1) here (that's Linux/util-linux only), and diskutil's text
# output isn't a stable thing to grep. Confirmed empirically against the real, currently-mounted
# DDP-HOT on this machine (differing device id from /Volumes) and against an ordinary /tmp
# subdirectory (same device id as its parent, correctly refused).
dest_dev=$(stat -f '%d' "$DEST_DIR" 2>/dev/null)
parent_dev=$(stat -f '%d' "$(dirname "$DEST_DIR")" 2>/dev/null)
if [ -z "$dest_dev" ] || [ "$dest_dev" = "$parent_dev" ]; then
    log "sync-ddp-hot: REFUSING to run -- $DEST_DIR does not look like a separately-mounted volume (missing, or the same device as $(dirname "$DEST_DIR")). If DDP-HOT is genuinely unmounted, mount it before the next tick; this job will not create/populate that path on the boot disk."
    exit 1
fi

# A single sync tick normally finishes well within a 15-min cadence, but a slow or hung tick
# must not pile up concurrent syncs against the same destination. This machine is a Mac, not
# Linux -- there is no `flock` command here at all (confirmed: it isn't installed by default on
# macOS) -- so this uses `lockf`, the BSD equivalent that ships with macOS itself, wrapping the
# aws invocation directly rather than a separate acquire-then-run step. `-t 0` fails immediately
# instead of blocking if another tick still holds the lock; `-k` keeps the lock file around
# between runs instead of deleting it (deleting and recreating it on every tick would reopen a
# tiny race a long-lived lock file doesn't have). Not the archiver's S3-based SourceLock -- that
# lock exists to coordinate across machines/processes writing to S3; this job only ever runs as
# one process on this one Mac, writing to local disk, so a local file lock is the right scope.
#
# pm-review round 1, real: lockf returns exit 75 (sysexits.h EX_TEMPFAIL) itself when it can't
# acquire the lock, but ALSO simply passes through whatever exit code the wrapped command
# produces once the lock IS acquired ("returns the exit status produced by command" -- lockf(1)).
# aws-cli has never been observed to exit 75 for anything, but relying on the bare number alone
# would silently misreport a real (if freak) aws failure as "someone else is running, skip" --
# swallowing a real failure is worse than the reverse. So this checks for lockf's own literal
# "already locked" message (its exact wording, confirmed empirically) in the captured output,
# not just the number -- that string can only appear because lockf itself printed it before ever
# invoking the child, so a same-numbered failure from aws itself can never produce it.
log "sync-ddp-hot: starting, s3://$SRC_BUCKET -> $DEST_DIR"
TMP_OUT=$(mktemp)
trap 'rm -f "$TMP_OUT"' EXIT
lockf -t 0 -k "$LOCK_FILE" "$AWS_BIN" s3 sync "s3://$SRC_BUCKET" "$DEST_DIR" \
    --ignore-glacier-warnings > "$TMP_OUT" 2>&1
rc=$?
tee -a "$LOG_FILE" < "$TMP_OUT"

if [ "$rc" -eq 0 ]; then
    log "sync-ddp-hot: ok"
    exit 0
elif [ "$rc" -eq 75 ] && grep -qF "already locked" "$TMP_OUT"; then
    log "sync-ddp-hot: another sync is already running (lock held on $LOCK_FILE), skipping this tick"
    exit 0
else
    log "sync-ddp-hot: FAILED (exit $rc) -- see the aws s3 sync output above"
    exit 1
fi
