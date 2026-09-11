#!/usr/bin/env bash
# OPEN-274: replica health-check script (PLAN-rds-local-postgres-replication.md §7.6). A small
# CLI health check, not a service -- matches the plan's own "do not build unnecessary
# infrastructure" guidance. Reports subscription status, apply lag (LSN-based, not just message
# receipt time), retained WAL, and an overall HEALTHY/LAGGING/DISCONNECTED/BROKEN status. Registers
# with `cams status`'s existing generic background-jobs display (a Redis hash, `cams:background_jobs`)
# as a heartbeat reporter -- no new display code needed, per that mechanism's own design (see
# ddp-agents/src/cams/background_jobs.py's own docstring: "any job reporting a heartbeat there
# shows up automatically").
#
# Usage:
#   RDS_HOST=<rds-endpoint> RDS_CA_BUNDLE_PATH=<path> LAGGING_THRESHOLD_BYTES=<n> \
#     ./replica-status.sh <database-name>
#
# The RDS-side retained-WAL/replication-slot query needs a credential with visibility into
# pg_replication_slots (instance-wide, not just this database) -- this script resolves that the
# same way OPEN-268's Fargate work resolves a live RDS credential (`resolve_rds_database_url()`);
# it is NOT tested end-to-end against real RDS from this session (no RDS access here, see
# ops/postgres-replica/NETWORK-PATH-CONFIRMED-OPEN-270.md) -- only the local-side checks and the
# cams heartbeat reporting were validated directly.
set -euo pipefail

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
  sub_enabled="$(docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$DATABASE_NAME" -tAc \
    "SELECT subenabled FROM pg_subscription WHERE subname = 'ddp_legbot_subscription';" 2>&1 || echo "")"
  if [ "$sub_enabled" != "t" ]; then
    status="DISCONNECTED"
    detail="ddp_legbot_subscription is not enabled (or does not exist) on $DATABASE_NAME"
    echo "FAIL: $detail" >&2
  else
    echo "PASS: subscription is enabled"

    echo
    echo "== Local apply state (received/latest LSN, last message receipt time) =="
    # Correction, per plan §7.6 (already applied here from the start): receipt time alone only
    # shows the connection is talking, not that it has applied all outstanding WAL -- report the
    # LSN values so real apply lag can be computed against the RDS-side confirmed_flush_lsn below,
    # not just "message received recently."
    local_state="$(docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$DATABASE_NAME" -tAc "
      SELECT pid || '|' || COALESCE(received_lsn::text, 'null') || '|' ||
             COALESCE(latest_end_lsn::text, 'null') || '|' ||
             COALESCE(last_msg_receipt_time::text, 'null')
      FROM pg_stat_subscription WHERE subname = 'ddp_legbot_subscription' AND pid IS NOT NULL;
    ")"
    if [ -z "$local_state" ]; then
      status="DISCONNECTED"
      detail="subscription is enabled but has no active apply worker (pg_stat_subscription has no row with a pid)"
      echo "FAIL: $detail" >&2
    else
      IFS='|' read -r worker_pid received_lsn latest_end_lsn last_receipt <<< "$local_state"
      echo "worker pid=$worker_pid received_lsn=$received_lsn latest_end_lsn=$latest_end_lsn last_receipt=$last_receipt"

      echo
      echo "== RDS-side: retained WAL and apply lag (needs RDS access -- NOT exercised by this" \
           "session's own testing, see header comment) =="
      # Resolve a live RDS credential the same way OPEN-268's Fargate work does -- never the
      # ddp_local_replication credential itself for this (plan §3.4 item 3's reasoning: this is a
      # one-off read, not the replication connection). This script does not implement that
      # resolution itself (it's environment/deployment-specific, matching how ddp-sync's own
      # resolve_rds_database_url() is used elsewhere) -- it expects RDS_MONITORING_DATABASE_URL to
      # already be resolved and exported by whatever wraps this script in its real deployment.
      if [ -n "${RDS_MONITORING_DATABASE_URL:-}" ]; then
        rds_state="$(psql "$RDS_MONITORING_DATABASE_URL" -tAc "
          SELECT pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), confirmed_flush_lsn)) || '|' ||
                 pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) || '|' ||
                 active::text
          FROM pg_replication_slots WHERE slot_name = 'ddp_legbot_subscription';
        " 2>&1 || echo "")"
        if [ -z "$rds_state" ]; then
          status="BROKEN"
          detail="could not find replication slot 'ddp_legbot_subscription' on RDS, or could not connect"
          echo "FAIL: $detail" >&2
        else
          IFS='|' read -r apply_lag retained_wal slot_active <<< "$rds_state"
          echo "apply_lag=$apply_lag retained_wal=$retained_wal slot_active=$slot_active"
          detail="apply_lag=$apply_lag retained_wal=$retained_wal last_receipt=$last_receipt"
          # Threshold check operates on bytes, not the pretty-printed string -- fetch the raw byte
          # count separately rather than parsing "123 MB" back out of pg_size_pretty's output.
          apply_lag_bytes="$(psql "$RDS_MONITORING_DATABASE_URL" -tAc "
            SELECT pg_wal_lsn_diff(pg_current_wal_lsn(), confirmed_flush_lsn)::bigint
            FROM pg_replication_slots WHERE slot_name = 'ddp_legbot_subscription';
          ")"
          if [ "$slot_active" != "t" ]; then
            status="DISCONNECTED"
          elif [ "$apply_lag_bytes" -gt "$LAGGING_THRESHOLD_BYTES" ]; then
            status="LAGGING"
          else
            status="HEALTHY"
          fi
        fi
      else
        echo "SKIPPED: RDS_MONITORING_DATABASE_URL not set -- reporting local-only status" >&2
        status="HEALTHY (local-only, RDS-side lag not checked)"
        detail="local apply worker running (pid=$worker_pid); RDS-side lag not checked (no RDS_MONITORING_DATABASE_URL)"
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
# iterates whatever job names exist in the hash -- no new display code needed.
now_epoch="$(date +%s)"
# Matches report_heartbeat()'s own behavior exactly: preserve the existing started_at if this job
# has already reported before, so cams status's "how long has this been running" display is
# meaningful rather than resetting to "just started" on every single invocation.
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
" "$status: $detail" "$now_epoch" "$existing_entry")"
docker exec "$REDIS_CONTAINER" redis-cli HSET cams:background_jobs "$JOB_NAME" "$heartbeat_json" >/dev/null
echo "Reported to cams:background_jobs under job name '$JOB_NAME'"

if [[ "$status" == HEALTHY* ]]; then
  exit 0
else
  exit 1
fi
