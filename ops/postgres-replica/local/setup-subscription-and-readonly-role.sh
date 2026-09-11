#!/usr/bin/env bash
# OPEN-273: stand up the local subscription and the read-only consumer role, then verify initial
# sync (PLAN-rds-local-postgres-replication.md §7.5). Run this against the NEW database
# OPEN-272's rebuild-local-replica.sh already built and verified -- not the existing 'openstates'
# database.
#
# Prerequisite (pm-review round 1 -- confirmed missing on this Mac, not yet fetched): the RDS CA
# bundle for sslmode=verify-full. AWS publishes this at a known public URL
# (https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem) -- download it and pass its
# path as RDS_CA_BUNDLE_PATH. verify-full without this configured will fail to connect, which is
# the correct, safe failure mode -- do not weaken to sslmode=require to work around a missing
# bundle.
#
# Usage:
#   RDS_HOST=<rds-endpoint> RDS_CA_BUNDLE_PATH=<path to the RDS CA bundle inside the container> \
#     ./setup-subscription-and-readonly-role.sh <new-database-name>
#
# Fetches ddp_local_replication's password (ops/postgres-replica/rds/00-generate-role-secret.sh)
# and generates+fetches a NEW, separate secret for ddp_local_readonly
# (generate-readonly-role-secret.sh, run once first if that secret doesn't exist yet) -- neither
# password is ever a shell argument, so neither appears in shell history or `ps` output.
set -euo pipefail

NEW_DB="${1:?Usage: $0 <new-database-name>}"

: "${RDS_HOST:?Set RDS_HOST to the RDS endpoint}"
: "${RDS_CA_BUNDLE_PATH:?Set RDS_CA_BUNDLE_PATH to the RDS CA bundle path inside the container}"
RDS_PORT="${RDS_PORT:-5432}"
RDS_DATABASE="${RDS_DATABASE:-openstates}"

PG_CONTAINER="${PG_CONTAINER:-ddp-openstates-postgres-1}"
PG_USER="${PG_USER:-openstates}"
REGION="us-east-1"

EXPECTED_TABLES=(
  opencivicdata_bill opencivicdata_legislativesession opencivicdata_jurisdiction
  opencivicdata_organization opencivicdata_billversion opencivicdata_billversionlink
  ddp_bill_version_document
)

if [[ ! "$NEW_DB" =~ ^[a-z_][a-z0-9_]*$ ]]; then
  echo "FAIL: '$NEW_DB' is not a safe database name" >&2
  exit 1
fi

RDS_REPLICATION_PASSWORD="$(aws secretsmanager get-secret-value --region "$REGION" --secret-id "ddp-openstates/ddp_local_replication" --query 'SecretString' --output text)"
READONLY_PASSWORD="$(aws secretsmanager get-secret-value --region "$REGION" --secret-id "ddp-openstates/ddp_local_readonly" --query 'SecretString' --output text)"
# Defense in depth (pm-review round 1): even though both secrets are generated with
# ExcludePunctuation, don't trust that blindly here -- a password containing a single quote would
# break the SQL/conninfo string interpolation below.
for pw_name in RDS_REPLICATION_PASSWORD READONLY_PASSWORD; do
  pw_value="${!pw_name}"
  if [[ "$pw_value" == *"'"* ]]; then
    echo "FAIL: $pw_name contains a single quote -- unsafe to interpolate into SQL/conninfo." >&2
    exit 1
  fi
done

echo "== Check for a pre-existing subscription or role (this script doesn't resume a partial" \
     "run -- fail with clear guidance rather than a raw duplicate-object error) =="
existing_sub="$(docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$NEW_DB" -tAc \
  "SELECT 1 FROM pg_subscription WHERE subname = 'ddp_legbot_subscription';")"
existing_role="$(docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$NEW_DB" -tAc \
  "SELECT 1 FROM pg_roles WHERE rolname = 'ddp_local_readonly';")"
if [ "$existing_sub" = "1" ] || [ "$existing_role" = "1" ]; then
  echo "FAIL: 'ddp_legbot_subscription' and/or 'ddp_local_readonly' already exist on '$NEW_DB' --" >&2
  echo "this looks like a partial or repeat run. Per PLAN-rds-local-postgres-replication.md §3.7" >&2
  echo "('rebuild, never repair in place'), the safe recovery is to re-run OPEN-272's rebuild" >&2
  echo "against a fresh database name, not to patch this one in place." >&2
  exit 1
fi

echo
echo "== Create the subscription =="
# sslmode=verify-full, not require -- per PLAN-rds-local-postgres-replication.md §7.5/§8, require
# encrypts but does not verify the server certificate.
docker exec "$PG_CONTAINER" psql -v ON_ERROR_STOP=1 -U "$PG_USER" -d "$NEW_DB" -c "
CREATE SUBSCRIPTION ddp_legbot_subscription
CONNECTION 'host=$RDS_HOST port=$RDS_PORT dbname=$RDS_DATABASE user=ddp_local_replication password=$RDS_REPLICATION_PASSWORD sslmode=verify-full sslrootcert=$RDS_CA_BUNDLE_PATH'
PUBLICATION ddp_legbot_publication
WITH (copy_data = true, create_slot = true, enabled = true);
"

echo
echo "== Create the read-only consumer role =="
# Local-side only -- never the subscription-owner role above. This is the only credential ever
# handed to a consumer (LegBot, api-v3). default_transaction_read_only is a convenience default
# only, not the real security boundary -- correction from pm-review round 1: a session can
# override it with `SET default_transaction_read_only = off`, so the REAL boundary is that no
# INSERT/UPDATE/DELETE grant is given at all (confirmed below, after the override).
docker exec "$PG_CONTAINER" psql -v ON_ERROR_STOP=1 -U "$PG_USER" -d "$NEW_DB" -c "
CREATE ROLE ddp_local_readonly WITH LOGIN PASSWORD '$READONLY_PASSWORD';
GRANT CONNECT ON DATABASE $NEW_DB TO ddp_local_readonly;
GRANT USAGE ON SCHEMA public TO ddp_local_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ddp_local_readonly;
ALTER ROLE ddp_local_readonly SET default_transaction_read_only = on;
"

echo
echo "== Wait for initial sync (pg_subscription_rel.srsubstate = 'r' for all 7 expected tables) =="
# Correction, pm-review round 1: the previous version ran two SEPARATE queries (a not-ready count
# and a total count), which could race -- if relations register between the two queries, a
# transient state could read as "0 not ready, 7 total" even if some of those 7 weren't actually
# ready yet. Now a single query returns everything needed from one consistent snapshot, and also
# checks the exact expected table NAMES (not just a count of 7), since a count alone can't tell
# the difference between the right 7 tables and some other 7.
sync_complete=""
for _ in $(seq 1 60); do
  # One row per (table, ready-or-not); NULL srrelid means an expected table has no
  # pg_subscription_rel entry at all yet (registration hasn't happened, not even "not ready").
  result="$(docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$NEW_DB" -tAc "
    SELECT string_agg(t || ':' || COALESCE(sr.srsubstate::text, 'missing'), ',')
    FROM unnest(ARRAY[$(printf "'%s'," "${EXPECTED_TABLES[@]}" | sed 's/,$//')]) AS t
    LEFT JOIN pg_subscription_rel sr ON sr.srrelid = ('public.' || t)::regclass;
  ")"
  if [[ "$result" != *"missing"* ]] && [[ "$result" != *":d"* ]] && [[ "$result" != *":i"* ]] && [[ "$result" != *":s"* ]]; then
    echo "PASS: all 7 expected tables report srsubstate='r' (initial sync complete): $result"
    sync_complete="yes"
    break
  fi
  sleep 1
done
if [ "$sync_complete" != "yes" ]; then
  echo "FAIL: initial sync did not complete for all 7 expected tables within the timeout." >&2
  echo "Last observed state: $result" >&2
  docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$NEW_DB" -c "
    SELECT srrelid::regclass, srsubstate FROM pg_subscription_rel ORDER BY 1;
  " >&2
  exit 1
fi

echo
echo "== Verify the read-only role can read all 7 tables =="
# Correction, pm-review round 1: the previous version only read one of the 7 tables. A missing
# SELECT grant or a naming problem on any of the other six would have gone undetected.
for t in "${EXPECTED_TABLES[@]}"; do
  docker exec "$PG_CONTAINER" env PGPASSWORD="$READONLY_PASSWORD" \
    psql -v ON_ERROR_STOP=1 -U ddp_local_readonly -d "$NEW_DB" -h localhost -tAc \
    "SELECT count(*) FROM $t;" >/dev/null
done
echo "PASS: ddp_local_readonly can SELECT from all 7 expected tables"

echo
echo "== Verify the read-only role genuinely cannot write, even after overriding the session" \
     "default (the real security boundary is the missing GRANT, not the convenience default) =="
# Correction, pm-review round 1: wrapped in an explicit transaction that is always rolled back --
# if the write unexpectedly succeeded, autocommit would have left __write_check_probe__ sitting
# in real replicated data. Also runs the check twice: once relying on the session default (as
# before), and once after explicitly turning that default off, to prove the underlying GRANT-level
# boundary holds even if the session default is bypassed.
#
# Correction, found live against a real database (not caught by pm-review round 1): the
# override=true case originally used `BEGIN; SET default_transaction_read_only = off; ...` --
# but default_transaction_read_only only controls the mode a FUTURE BEGIN starts in; setting it
# after a transaction has already started has no effect on that transaction's own read/write
# mode. Confirmed directly: with that sequence the error is always "cannot execute INSERT in a
# read-only transaction" (session-default enforcement), never a permission check, EVEN with an
# explicit INSERT grant added to the test role first -- meaning override=true was silently
# identical to override=false and would have still printed PASS even if ddp_local_readonly were
# accidentally granted INSERT/UPDATE/DELETE someday, exactly the regression this second check
# exists to catch. Fixed with `SET TRANSACTION READ WRITE` instead, which does flip the CURRENT
# transaction's mode -- confirmed: the same INSERT then succeeds against a role with a real
# INSERT grant, and correctly fails with "permission denied for table" once that grant is
# revoked, so this now actually exercises the GRANT-level boundary it claims to.
for override in "false" "true"; do
  sql="BEGIN;"
  if [ "$override" = "true" ]; then
    sql+=" SET TRANSACTION READ WRITE;"
  fi
  sql+=" INSERT INTO opencivicdata_jurisdiction (id) VALUES ('__write_check_probe__'); ROLLBACK;"
  write_check_output="$(docker exec "$PG_CONTAINER" env PGPASSWORD="$READONLY_PASSWORD" \
      psql -U ddp_local_readonly -d "$NEW_DB" -h localhost -c "$sql" 2>&1 || true)"
  if echo "$write_check_output" | grep -qE "read-only transaction|permission denied"; then
    echo "PASS (override=$override): write correctly refused"
  else
    echo "FAIL (override=$override): write was NOT refused -- ddp_local_readonly can write." >&2
    echo "Actual output: $write_check_output" >&2
    exit 1
  fi
done

echo
echo "== Done =="
echo "Subscription is live and initial sync is complete. Per plan §7.7, the full data-bearing"
echo "api-v3 smoke test (deferred from OPEN-272) can now run for real against this database --"
echo "real data exists here now."
