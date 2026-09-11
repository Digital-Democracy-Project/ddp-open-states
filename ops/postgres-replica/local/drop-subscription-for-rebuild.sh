#!/usr/bin/env bash
# OPEN-274: the DROP SUBSCRIPTION half of the rebuild/recovery procedure
# (PLAN-rds-local-postgres-replication.md §7.8, §3.7's "rebuild, never repair in place"). This is
# the only recovery path -- there is no "repair a broken replica in place" procedure, by design.
#
# Full recovery cycle (this script covers step 1; OPEN-272's rebuild-local-replica.sh and
# OPEN-273's setup-subscription-and-readonly-role.sh cover the rest, already validated separately
# -- this script doesn't re-implement them):
#   1. Stop LegBot's batch pipeline and any other local consumer (manual step, outside this
#      script -- LegBot's own process is not something this ops tooling controls).
#   2. THIS SCRIPT: drop the subscription, handling both the reachable-publisher case (which drops
#      the remote slot automatically) and the unreachable-publisher case (which cannot reach RDS
#      to drop it, and must detach locally without touching the remote slot).
#   3. Confirm the RDS-side slot is actually gone (needs RDS access -- this script prints the
#      exact query to run, it doesn't run it itself, since the reachable-vs-unreachable case
#      above determines whether that's even possible from here).
#   4. Re-run rebuild-local-replica.sh against a NEW database name.
#   5. Re-run setup-subscription-and-readonly-role.sh against that new database.
#   6. Restart LegBot's batch pipeline and any other local consumer (manual, outside this script).
#
# Usage: ./drop-subscription-for-rebuild.sh <database-name>
set -euo pipefail

DATABASE_NAME="${1:?Usage: $0 <database-name>}"
PG_CONTAINER="${PG_CONTAINER:-ddp-openstates-postgres-1}"
PG_USER="${PG_USER:-openstates}"

echo "== Checking whether the publisher (RDS) is reachable through this subscription =="
# A live apply worker (a row with a non-null pid in pg_stat_subscription) is a reasonable proxy
# for "the publisher was reachable recently" -- if the subscription exists but has no active
# worker, treat that as the unreachable case rather than assuming a plain DROP SUBSCRIPTION will
# succeed and then being surprised when it hangs/fails.
worker_pid="$(docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$DATABASE_NAME" -tAc "
  SELECT pid FROM pg_stat_subscription WHERE subname = 'ddp_legbot_subscription' AND pid IS NOT NULL;
" 2>&1 || echo "")"

if [ -n "$worker_pid" ]; then
  echo "Apply worker is active (pid=$worker_pid) -- attempting a normal DROP SUBSCRIPTION, which"
  echo "also drops the remote replication slot on RDS automatically."
  if docker exec "$PG_CONTAINER" psql -v ON_ERROR_STOP=1 -U "$PG_USER" -d "$DATABASE_NAME" -c "
    DROP SUBSCRIPTION ddp_legbot_subscription;
  " 2>&1; then
    echo "PASS: subscription dropped, remote slot dropped automatically."
    echo "Confirm on RDS: SELECT * FROM pg_replication_slots WHERE slot_name = 'ddp_legbot_subscription'; -- expect 0 rows."
    exit 0
  else
    echo "Normal DROP SUBSCRIPTION failed despite an apparently-active worker -- falling through" >&2
    echo "to the unreachable-publisher path below." >&2
  fi
fi

echo
echo "== Publisher unreachable (or the normal drop failed) -- detaching locally without touching" \
     "the remote slot =="
docker exec "$PG_CONTAINER" psql -v ON_ERROR_STOP=1 -U "$PG_USER" -d "$DATABASE_NAME" -c "
ALTER SUBSCRIPTION ddp_legbot_subscription DISABLE;
ALTER SUBSCRIPTION ddp_legbot_subscription SET (slot_name = NONE);
DROP SUBSCRIPTION ddp_legbot_subscription;
"
echo "PASS: local subscription detached. The remote slot on RDS was NOT touched (couldn't be, or"
echo "the normal path failed) -- once RDS is reachable again, confirm and clean it up there."
echo
echo "Found by actually exercising this drill (killing the publisher mid-initial-copy, not just"
echo "reading the procedure): if the publisher becomes unreachable DURING the initial copy (not"
echo "just after it), Postgres can leave behind an additional per-table TEMPORARY tablesync slot"
echo "(named like pg_<oid>_sync_<relid>_<random>, distinct from the main 'ddp_legbot_subscription'"
echo "slot) that a check for the main slot name alone will miss entirely. Check for BOTH:"
echo "  SELECT slot_name FROM pg_replication_slots WHERE slot_name = 'ddp_legbot_subscription'"
echo "    OR slot_name LIKE 'pg_%_sync_%';"
echo "  -- drop each one found: SELECT pg_drop_replication_slot('<slot_name>');"
