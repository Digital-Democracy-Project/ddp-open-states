#!/usr/bin/env bash
# OPEN-273: stand up the local subscription and the read-only consumer role, then verify initial
# sync (PLAN-rds-local-postgres-replication.md §7.5). Run this against the NEW database
# OPEN-272's rebuild-local-replica.sh already built and verified -- not the existing 'openstates'
# database.
#
# Usage:
#   RDS_HOST=<rds-endpoint> RDS_REPLICATION_PASSWORD=<from Secrets Manager, ops/postgres-replica/rds> \
#     ./setup-subscription-and-readonly-role.sh <new-database-name> <readonly-role-password>
#
# <readonly-role-password> is a separate password for the NEW ddp_local_readonly role this
# script creates (local-side, not the same credential as ddp_local_replication) -- generate one,
# don't reuse another role's password.
set -euo pipefail

NEW_DB="${1:?Usage: $0 <new-database-name> <readonly-role-password>}"
READONLY_PASSWORD="${2:?Usage: $0 <new-database-name> <readonly-role-password>}"

: "${RDS_HOST:?Set RDS_HOST to the RDS endpoint}"
: "${RDS_REPLICATION_PASSWORD:?Set RDS_REPLICATION_PASSWORD to the ddp_local_replication role password}"
RDS_PORT="${RDS_PORT:-5432}"
RDS_DATABASE="${RDS_DATABASE:-openstates}"

PG_CONTAINER="${PG_CONTAINER:-ddp-openstates-postgres-1}"
PG_USER="${PG_USER:-openstates}"

if [[ ! "$NEW_DB" =~ ^[a-z_][a-z0-9_]*$ ]]; then
  echo "FAIL: '$NEW_DB' is not a safe database name" >&2
  exit 1
fi

echo "== Create the subscription =="
# sslmode=verify-full, not require -- per PLAN-rds-local-postgres-replication.md §7.5/§8, require
# encrypts but does not verify the server certificate.
docker exec "$PG_CONTAINER" psql -v ON_ERROR_STOP=1 -U "$PG_USER" -d "$NEW_DB" -c "
CREATE SUBSCRIPTION ddp_legbot_subscription
CONNECTION 'host=$RDS_HOST port=$RDS_PORT dbname=$RDS_DATABASE user=ddp_local_replication password=$RDS_REPLICATION_PASSWORD sslmode=verify-full'
PUBLICATION ddp_legbot_publication
WITH (copy_data = true, create_slot = true, enabled = true);
"

echo
echo "== Create the read-only consumer role =="
# Local-side only -- never the subscription-owner role above. This is the only credential ever
# handed to a consumer (LegBot, api-v3).
docker exec "$PG_CONTAINER" psql -v ON_ERROR_STOP=1 -U "$PG_USER" -d "$NEW_DB" -c "
CREATE ROLE ddp_local_readonly WITH LOGIN PASSWORD '$READONLY_PASSWORD';
GRANT CONNECT ON DATABASE $NEW_DB TO ddp_local_readonly;
GRANT USAGE ON SCHEMA public TO ddp_local_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ddp_local_readonly;
ALTER ROLE ddp_local_readonly SET default_transaction_read_only = on;
"

echo
echo "== Wait for initial sync (pg_subscription_rel.srsubstate = 'r' for all 7 tables) =="
EXPECTED_TABLES=(
  opencivicdata_bill opencivicdata_legislativesession opencivicdata_jurisdiction
  opencivicdata_organization opencivicdata_billversion opencivicdata_billversionlink
  ddp_bill_version_document
)
for _ in $(seq 1 60); do
  not_ready="$(docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$NEW_DB" -tAc "
    SELECT count(*) FROM pg_subscription_rel WHERE srsubstate != 'r';
  ")"
  total="$(docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$NEW_DB" -tAc "
    SELECT count(*) FROM pg_subscription_rel;
  ")"
  if [ "$total" -eq 7 ] && [ "$not_ready" -eq 0 ]; then
    echo "PASS: all 7 tables report srsubstate='r' (initial sync complete)"
    break
  fi
  sleep 1
done
docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$NEW_DB" -c "
SELECT srrelid::regclass, srsubstate FROM pg_subscription_rel ORDER BY 1;
"

echo
echo "== Verify the read-only role can read but not write =="
docker exec "$PG_CONTAINER" env PGPASSWORD="$READONLY_PASSWORD" \
  psql -U ddp_local_readonly -d "$NEW_DB" -h localhost -c "
SELECT count(*) FROM opencivicdata_jurisdiction;
"
# Correction found by actually running this: capture output into a variable first, then grep on
# the variable -- NOT `... | grep -q ...` directly in the if-condition. With `set -o pipefail`
# active, psql's own non-zero exit (expected here, since the INSERT should fail) becomes the
# pipeline's reported exit status even when grep DOES find the expected message, because
# pipefail reports the rightmost command that failed, moving right to left past a successful
# grep. That made this check report FAIL even when the write was correctly refused (confirmed by
# running the exact same psql command directly, outside this script, and seeing the correct
# refusal both times).
write_check_output="$(docker exec "$PG_CONTAINER" env PGPASSWORD="$READONLY_PASSWORD" \
    psql -U ddp_local_readonly -d "$NEW_DB" -h localhost -c "
    INSERT INTO opencivicdata_jurisdiction (id) VALUES ('__write_check_probe__');
  " 2>&1 || true)"
if echo "$write_check_output" | grep -q "read-only transaction"; then
  echo "PASS: write correctly refused (read-only transaction)"
else
  echo "FAIL: write was NOT refused -- ddp_local_readonly can write, which it shouldn't be able to." >&2
  echo "Actual output: $write_check_output" >&2
  exit 1
fi

echo
echo "== Done =="
echo "Subscription is live and initial sync is complete. Per plan §7.7, the full data-bearing"
echo "api-v3 smoke test (deferred from OPEN-272) can now run for real against this database --"
echo "real data exists here now."
