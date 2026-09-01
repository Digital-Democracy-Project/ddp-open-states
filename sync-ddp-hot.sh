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
# No --delete: this is deliberately additive-only. DDP-HOT gaining a file some other local
# process put there and this job not otherwise knowing about is harmless; this job silently
# deleting a local file that fell out of the bucket is not something OPEN-236 asked for.
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

# A single sync tick normally finishes well within a 15-min cadence, but a slow or hung tick
# must not pile up concurrent syncs against the same destination. This machine is a Mac, not
# Linux -- there is no `flock` command here at all (confirmed: it isn't installed by default on
# macOS) -- so this uses `lockf`, the BSD equivalent that ships with macOS itself, wrapping the
# aws invocation directly rather than a separate acquire-then-run step. `-t 0` fails immediately
# instead of blocking if another tick still holds the lock (empirically confirmed to exit 75,
# sysexits.h's EX_TEMPFAIL, on this exact macOS version); `-k` keeps the lock file around between
# runs instead of deleting it (deleting and recreating it on every tick would reopen a tiny race
# a long-lived lock file doesn't have); `-s` keeps lockf's own contention message off stderr
# since this script logs that case itself. Not the archiver's S3-based SourceLock -- that lock
# exists to coordinate across machines/processes writing to S3; this job only ever runs as one
# process on this one Mac, writing to local disk, so a local file lock is the right scope.
log "sync-ddp-hot: starting, s3://$SRC_BUCKET -> $DEST_DIR"
if lockf -t 0 -k -s "$LOCK_FILE" "$AWS_BIN" s3 sync "s3://$SRC_BUCKET" "$DEST_DIR" \
        --ignore-glacier-warnings 2>&1 | tee -a "$LOG_FILE"; then
    log "sync-ddp-hot: ok"
    exit 0
else
    rc=$?
    if [ "$rc" -eq 75 ]; then
        log "sync-ddp-hot: another sync is already running (lock held on $LOCK_FILE), skipping this tick"
        exit 0
    fi
    log "sync-ddp-hot: FAILED (exit $rc) -- see the aws s3 sync output above"
    exit 1
fi
