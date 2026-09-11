#!/usr/bin/env bash
# OPEN-274: replica health-check script (PLAN-rds-local-postgres-replication.md §7.6). A small
# CLI health check, not a service -- matches the plan's own "do not build unnecessary
# infrastructure" guidance. Reports subscription status, apply lag (LSN-based, not just message
# receipt time), retained WAL, and an overall HEALTHY/LAGGING/DISCONNECTED/BROKEN/INCOMPLETE
# status. Registers with `cams status`'s existing generic background-jobs display (a Redis hash,
# `cams:background_jobs`) as a heartbeat reporter -- no new display code needed, per that
# mechanism's own design (see ddp-agents/src/cams/background_jobs.py's own docstring: "any job
# reporting a heartbeat there shows up automatically").
#
# Usage (correction, pm-review round 1 -- the usage line previously advertised RDS_HOST and
# RDS_CA_BUNDLE_PATH, which this script never actually read; fixed to match what it really uses):
#   RDS_MONITORING_DATABASE_URL=<resolved live RDS connection string, e.g. via
#     resolve_rds_database_url(), pointed at a role with visibility into pg_replication_slots> \
#     LAGGING_THRESHOLD_BYTES=<n> ./replica-status.sh <database-name>
#
# The RDS-side retained-WAL/replication-slot query needs a credential with visibility into
# pg_replication_slots (instance-wide, not just this database) -- never ddp_local_replication
# itself for this (plan §3.4 item 3's reasoning: this is a one-off read, not the replication
# connection). This script does NOT resolve that credential itself (environment/deployment
# specific, matching how ddp-sync's own resolve_rds_database_url() is used elsewhere) and is NOT
# exercised end-to-end against real RDS from this session (no RDS access here, see
# ops/postgres-replica/NETWORK-PATH-CONFIRMED-OPEN-270.md) -- only the local-side checks and the
# cams heartbeat reporting were validated directly.
#
# Correction, pm-review round 1: this script deliberately does NOT use `set -e` -- an earlier
# version did, and a failure partway through (an RDS connection error, a malformed query result)
# could exit the script before it ever reached the heartbeat-reporting step at the end, which is
# exactly backwards for a health check: a failure is precisely when you most need the heartbeat to
# report something (even BROKEN), not go silent. Every command below is checked explicitly instead.
set -uo pipefail

DATABASE_NAME="${1:?Usage: $0 <database-name>}"
PG_CONTAINER="${PG_CONTAINER:-ddp-openstates-postgres-1}"
PG_USER="${PG_USER:-openstates}"
REDIS_CONTAINER="${REDIS_CONTAINER:-ddp-agents-redis-1}"
JOB_NAME="${JOB_NAME:-ddp_legbot_replica}"
LAGGING_THRESHOLD_BYTES="${LAGGING_THRESHOLD_BYTES:-104857600}"  # 100MB, a starting number per
  # plan §9 open question 4 -- not derived from an observed steady-state, revisit once real data
  # exists.

status="UNKNOWN"
detail=""

echo "== Local Postgres: running? =="
if ! docker exec "$PG_CONTAINER" pg_isready -U "$PG_USER" >/dev/null 2>&1; then
  status="BROKEN"
  detail="local Postgres container ($PG_CONTAINER) is not accepting connections"
  echo "FAIL: $detail" >&2
else
  echo "PASS: local Postgres is running"

  echo
  echo "== Subscription enabled? =="
  sub_enabled_stdout="$(docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$DATABASE_NAME" -tAc \
    "SELECT subenabled FROM pg_subscription WHERE subname = 'ddp_legbot_subscription';" 2>/tmp/replica-status-err.$$)"
  sub_enabled_rc=$?
  sub_enabled_err="$(cat /tmp/replica-status-err.$$ 2>/dev/null || true)"; rm -f /tmp/replica-status-err.$$
  if [ "$sub_enabled_rc" -ne 0 ]; then
    status="BROKEN"
    detail="query for subscription status failed: $sub_enabled_err"
    echo "FAIL: $detail" >&2
  elif [ "$sub_enabled_stdout" != "t" ]; then
    status="DISCONNECTED"
    detail="ddp_legbot_subscription is not enabled (or does not exist) on $DATABASE_NAME"
    echo "FAIL: $detail" >&2
  else
    echo "PASS: subscription is enabled"

    echo
    echo "== Local apply state (received/latest LSN, last message receipt time) =="
    # Correction, per plan §7.6 (already applied here from the start): receipt time alone only
    # shows the connection is talking, not that it has applied all outstanding WAL -- report the
    # LSN values for operator visibility (the authoritative lag number still comes from the
    # RDS-side confirmed_flush_lsn below, not from these).
    # Correction, pm-review round 1: filter to relid IS NULL -- pg_stat_subscription can show
    # additional rows for per-table tablesync workers during initial sync, which would otherwise
    # break the single-row parsing below or pick an arbitrary row.
    local_state_stdout="$(docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$DATABASE_NAME" -tAc "
      SELECT pid || '|' || COALESCE(received_lsn::text, 'null') || '|' ||
             COALESCE(latest_end_lsn::text, 'null') || '|' ||
             COALESCE(last_msg_receipt_time::text, 'null')
      FROM pg_stat_subscription
      WHERE subname = 'ddp_legbot_subscription' AND pid IS NOT NULL AND relid IS NULL;
    " 2>/tmp/replica-status-err.$$)"
    local_state_rc=$?
    local_state_err="$(cat /tmp/replica-status-err.$$ 2>/dev/null || true)"; rm -f /tmp/replica-status-err.$$
    if [ "$local_state_rc" -ne 0 ]; then
      status="BROKEN"
      detail="query for local apply state failed: $local_state_err"
      echo "FAIL: $detail" >&2
    elif [ -z "$local_state_stdout" ]; then
      status="DISCONNECTED"
      detail="subscription is enabled but has no active main apply worker (pg_stat_subscription has no matching row)"
      echo "FAIL: $detail" >&2
    else
      IFS='|' read -r worker_pid received_lsn latest_end_lsn last_receipt <<< "$local_state_stdout"
      echo "worker pid=$worker_pid received_lsn=$received_lsn latest_end_lsn=$latest_end_lsn last_receipt=$last_receipt"

      echo
      echo "== RDS-side: retained WAL and apply lag (needs RDS access -- NOT exercised by this" \
           "session's own testing, see header comment) =="
      if [ -n "${RDS_MONITORING_DATABASE_URL:-}" ]; then
        rds_state_stdout="$(psql "$RDS_MONITORING_DATABASE_URL" -tAc "
          -- Correction, pm-review round 1: found by actually running this and getting a wrong
          -- result -- boolean::text in Postgres yields 'true'/'false', NOT 't'/'f', but the
          -- comparison below checks for 't'. Casting via ''::text picks up the plain -tA output
          -- format instead ('t'/'f'), which is what the bash comparison actually expects.
          SELECT COALESCE(pg_wal_lsn_diff(pg_current_wal_lsn(), confirmed_flush_lsn)::bigint::text, 'null') || '|' ||
                 pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) || '|' ||
                 (CASE WHEN active THEN 't' ELSE 'f' END)
          FROM pg_replication_slots WHERE slot_name = 'ddp_legbot_subscription';
        " 2>/tmp/replica-status-err.$$)"
        rds_state_rc=$?
        rds_state_err="$(cat /tmp/replica-status-err.$$ 2>/dev/null || true)"; rm -f /tmp/replica-status-err.$$
        if [ "$rds_state_rc" -ne 0 ]; then
          status="BROKEN"
          detail="RDS-side query failed (connection or permission problem): $rds_state_err"
          echo "FAIL: $detail" >&2
        elif [ -z "$rds_state_stdout" ]; then
          status="BROKEN"
          detail="could not find replication slot 'ddp_legbot_subscription' on RDS"
          echo "FAIL: $detail" >&2
        else
          IFS='|' read -r apply_lag_bytes retained_wal slot_active <<< "$rds_state_stdout"
          echo "apply_lag_bytes=$apply_lag_bytes retained_wal=$retained_wal slot_active=$slot_active"
          # Correction, pm-review round 1: this is the publisher's total WAL-vs-confirmed-flush
          # distance for this slot -- the standard way logical replication lag is measured, but it
          # reflects the WHOLE RDS instance's WAL activity, not only writes relevant to this
          # publication's 7 tables. A busy, unrelated table on the same RDS instance can inflate
          # this number even when this subscription is perfectly caught up on its own data. Labeled
          # accordingly rather than implying it's scoped to just this publication's own writes.
          detail="publisher_wal_lag_bytes=$apply_lag_bytes retained_wal=$retained_wal last_receipt=$last_receipt"
          if [ "$apply_lag_bytes" = "null" ]; then
            status="BROKEN"
            detail="$detail (confirmed_flush_lsn is null -- slot exists but has never confirmed a flush)"
          elif [ "$slot_active" != "t" ]; then
            status="DISCONNECTED"
          elif [ "$apply_lag_bytes" -gt "$LAGGING_THRESHOLD_BYTES" ]; then
            status="LAGGING"
          else
            status="HEALTHY"
          fi
        fi
      else
        # Correction, pm-review round 1: this used to report "HEALTHY (local-only...)" and exit 0
        # -- a local apply worker existing does NOT mean replication is actually caught up; that
        # requires the RDS-side check above. Reporting HEALTHY without performing it is a false
        # "all clear." Now reports INCOMPLETE and fails the exit code, since this is not a
        # complete health assessment, not a pass.
        echo "SKIPPED: RDS_MONITORING_DATABASE_URL not set -- cannot assess replication lag, only" >&2
        echo "that a local apply worker process exists." >&2
        status="INCOMPLETE"
        detail="local apply worker running (pid=$worker_pid), but RDS-side lag was NOT checked (no RDS_MONITORING_DATABASE_URL) -- this is not a full health assessment"
      fi
    fi
  fi
fi

echo
echo "== Overall status: $status =="
echo "$detail"

echo
echo "== Reporting heartbeat to cams status (Redis hash cams:background_jobs) =="
# Writes the exact same JSON schema as ddp-agents/src/cams/background_jobs.py's report_heartbeat()
# helper, directly via redis-cli rather than importing that Python module cross-repo -- this
# script lives in ddp-open-states-dev, that module lives in ddp-agents(-dev); the wire format is
# intentionally tiny and stable (one Redis hash, one JSON blob per job) precisely so any reporter,
# regardless of language or repo, can write it directly. cams status's own display code just
# iterates whatever job names exist in the hash -- no new display code needed. This step runs
# regardless of the status determined above -- reporting a BROKEN/INCOMPLETE heartbeat is exactly
# as important as reporting a HEALTHY one, arguably more so.
now_epoch="$(date +%s)"
existing_entry="$(docker exec "$REDIS_CONTAINER" redis-cli HGET cams:background_jobs "$JOB_NAME" 2>/dev/null || echo "")"
heartbeat_json="$(python3 -c "
import json, sys
existing = sys.argv[3]
started_at = float(sys.argv[2])
if existing:
    try:
        started_at = json.loads(existing).get('started_at', started_at)
    except Exception:
        pass
print(json.dumps({
    'detail': sys.argv[1],
    'last_heartbeat_at': float(sys.argv[2]),
    'started_at': started_at,
    'expected_interval_s': None,
}))
" "$status: $detail" "$now_epoch" "$existing_entry" 2>/tmp/replica-status-err.$$)"
heartbeat_build_rc=$?
if [ "$heartbeat_build_rc" -ne 0 ]; then
  echo "WARN: failed to build heartbeat JSON: $(cat /tmp/replica-status-err.$$ 2>/dev/null)" >&2
  rm -f /tmp/replica-status-err.$$
elif ! docker exec "$REDIS_CONTAINER" redis-cli HSET cams:background_jobs "$JOB_NAME" "$heartbeat_json" >/dev/null 2>/tmp/replica-status-err.$$; then
  echo "WARN: failed to write heartbeat to cams:background_jobs: $(cat /tmp/replica-status-err.$$ 2>/dev/null)" >&2
  rm -f /tmp/replica-status-err.$$
else
  echo "Reported to cams:background_jobs under job name '$JOB_NAME'"
fi

if [ "$status" = "HEALTHY" ]; then
  exit 0
else
  exit 1
fi
