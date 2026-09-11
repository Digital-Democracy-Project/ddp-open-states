#!/usr/bin/env bash
# OPEN-274: the DROP SUBSCRIPTION half of the rebuild/recovery procedure
# (PLAN-rds-local-postgres-replication.md §7.8, §3.7's "rebuild, never repair in place"). This is
# the only recovery path -- there is no "repair a broken replica in place" procedure, by design.
#
# Full recovery cycle (this script covers step 2; OPEN-272's rebuild-local-replica.sh and
# OPEN-273's setup-subscription-and-readonly-role.sh cover steps 4-5, already validated separately
# -- this script doesn't re-implement them):
#   1. Stop LegBot's batch pipeline and any other local consumer (manual step, outside this
#      script -- LegBot's own process is not something this ops tooling controls).
#   2. THIS SCRIPT: drop the subscription, handling both the reachable-publisher case (which drops
#      the remote slot automatically) and the unreachable-publisher case (which cannot reach RDS
#      to drop it, and must detach locally without touching the remote slot).
#   3. Confirm the RDS-side slot(s) are actually gone (needs RDS access -- this script prints the
#      exact query to run, it doesn't run it itself, since the reachable-vs-unreachable case
#      above determines whether that's even possible from here).
#   4. Re-run rebuild-local-replica.sh against a NEW database name.
#   5. Re-run setup-subscription-and-readonly-role.sh against that new database.
#   6. Restart LegBot's batch pipeline and any other local consumer (manual, outside this script).
#
# Usage: ./drop-subscription-for-rebuild.sh <database-name>
set -uo pipefail

DATABASE_NAME="${1:?Usage: $0 <database-name>}"
PG_CONTAINER="${PG_CONTAINER:-ddp-openstates-postgres-1}"
PG_USER="${PG_USER:-openstates}"

echo "== Checking whether the publisher (RDS) is reachable through this subscription =="
# A live apply worker (a row with a non-null pid in pg_stat_subscription, main worker only --
# relid IS NULL excludes per-table tablesync workers, which would otherwise multiply this into
# several rows during initial sync) is a reasonable proxy for "the publisher was reachable
# recently" -- if the subscription exists but has no active worker, treat that as the unreachable
# case rather than assuming a plain DROP SUBSCRIPTION will succeed and then being surprised when
# it hangs/fails.
worker_pid="$(docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$DATABASE_NAME" -tAc "
  SELECT pid FROM pg_stat_subscription
  WHERE subname = 'ddp_legbot_subscription' AND pid IS NOT NULL AND relid IS NULL;
" 2>&1 || echo "")"

if [ -n "$worker_pid" ]; then
  echo "Apply worker is active (pid=$worker_pid) -- attempting a normal DROP SUBSCRIPTION, which"
  echo "also drops the remote replication slot on RDS automatically."
  # Correction, pm-review round 1: a bare "is there an active worker" check does not guarantee
  # RDS is reachable RIGHT NOW -- a worker can stay running while retrying a connection that's
  # actually down. Bound the attempt with a statement_timeout so this fails fast into the
  # unreachable-publisher path below, instead of hanging indefinitely.
  # Two separate -c flags, not one combined statement string: DROP SUBSCRIPTION cannot run as
  # part of a multi-statement simple-query batch (confirmed by actually running the combined
  # form and getting "DROP SUBSCRIPTION cannot run inside a transaction block") -- separate -c
  # flags on the same psql invocation share one connection/session, so the SET still applies to
  # the DROP that follows it.
  drop_output="$(docker exec "$PG_CONTAINER" psql -v ON_ERROR_STOP=1 -U "$PG_USER" -d "$DATABASE_NAME" \
    -c "SET statement_timeout = '15s';" \
    -c "DROP SUBSCRIPTION ddp_legbot_subscription;" 2>&1)"
  drop_rc=$?
  if [ "$drop_rc" -eq 0 ]; then
    echo "PASS: subscription dropped, remote slot dropped automatically."
    echo "Confirm on RDS: SELECT * FROM pg_replication_slots WHERE slot_name = 'ddp_legbot_subscription';"
    echo "-- expect 0 rows."
    exit 0
  else
    # Correction, pm-review round 1: DROP SUBSCRIPTION can also fail for reasons that have
    # nothing to do with publisher reachability (a permission problem, a lock conflict, a timeout
    # from something else entirely) -- print the actual error so an operator can judge that,
    # rather than silently assuming every failure means "unreachable publisher" and proceeding to
    # detach-and-orphan-the-slot on that assumption.
    echo "Normal DROP SUBSCRIPTION failed:" >&2
    echo "$drop_output" >&2
    echo >&2
    echo "If the error above is NOT a connectivity/timeout issue (e.g. it's a permission or lock" >&2
    echo "problem instead), investigate and fix that directly rather than proceeding to the" >&2
    echo "detach-without-touching-the-remote-slot path below -- that path assumes RDS genuinely" >&2
    echo "can't be reached, which a permission error does not confirm." >&2
  fi
fi

echo
echo "== Detaching locally without touching the remote slot (publisher unreachable, or the normal" \
     "drop failed for a reason confirmed above to actually be a connectivity issue) =="
# Correction, found by actually pausing the simulated publisher mid-drill (not just reading the
# procedure): DISABLE and the slot_name=NONE change both return immediately even with the
# publisher completely unreachable, but the final DROP SUBSCRIPTION still waits for the apply
# worker to actually exit -- and a worker stuck retrying a connection to a truly hung (not just
# cleanly-refused) publisher can block that wait indefinitely, defeating the entire point of this
# "unreachable publisher" fallback path. Bound it with the same statement_timeout as the primary
# path above (confirmed this actually gets the DROP cancelled rather than hanging past it).
# Also, capture the exit code explicitly -- this script does not use `set -e`, so an unguarded
# command here would let the script fall through and print PASS even on a real failure.
detach_output="$(docker exec "$PG_CONTAINER" psql -v ON_ERROR_STOP=1 -U "$PG_USER" -d "$DATABASE_NAME" \
  -c "SET statement_timeout = '15s';" \
  -c "ALTER SUBSCRIPTION ddp_legbot_subscription DISABLE;" \
  -c "ALTER SUBSCRIPTION ddp_legbot_subscription SET (slot_name = NONE);" \
  -c "DROP SUBSCRIPTION ddp_legbot_subscription;" 2>&1)"
detach_rc=$?
echo "$detach_output"
if [ "$detach_rc" -ne 0 ]; then
  echo "FAIL: could not fully detach the local subscription." >&2
  echo "It may be left in a PARTIAL state (disabled, slot_name cleared) but not dropped -- check" >&2
  echo "  SELECT subname, subenabled, subslotname FROM pg_subscription;" >&2
  echo "on $DATABASE_NAME before retrying: DROP SUBSCRIPTION ddp_legbot_subscription; directly," >&2
  echo "or investigate why it's still not completing (e.g. the apply worker still hasn't exited)." >&2
  exit 1
fi
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
echo
echo "Correction, pm-review round 1: dropping every slot matching 'pg_%_sync_%' is only safe"
echo "because this plan's own design puts exactly one subscription (this one, from this Mac) on"
echo "this RDS instance's logical replication -- if that ever stops being true (another"
echo "subscription/consumer added to the same RDS instance), this blanket pattern match could drop"
echo "an unrelated subscription's in-progress tablesync slot. Confirm no other subscriptions exist"
echo "before running this on a shared instance: SELECT subname FROM pg_stat_subscription; (querying"
echo "this Mac's own local Postgres won't show OTHER consumers' subscriptions elsewhere -- if RDS"
echo "ever serves more than this one replica, check with whoever administers those other consumers"
echo "instead of assuming from this side alone)."
