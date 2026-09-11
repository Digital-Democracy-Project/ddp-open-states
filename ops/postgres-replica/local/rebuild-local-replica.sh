#!/usr/bin/env bash
# OPEN-272: build the Mac's replacement local Postgres alongside the existing one
# (PLAN-rds-local-postgres-replication.md §3.5/§7.4). Non-destructive: builds under a NEW
# database name and verifies the schema applies cleanly + api-v3 can start against it. STOPS
# there -- repointing the real api-v3 container and retiring the old database are deliberately
# NOT automated here (see "What this does NOT do" below).
#
# Correction found by actually running this against a real schema dump (not just reading it):
# this does NOT run the full authenticated, data-bearing api-v3 smoke test from plan §7.4
# (curl .../bills/<id>?include=versions). That test needs (a) real bill data, which doesn't
# exist until OPEN-273's subscription completes its initial copy, and (b) a valid API key
# checked against api-v3's own Profile table, which isn't one of the 7 replicated tables at all
# and has zero rows on a schema-only rebuild regardless. Running it here would fail for reasons
# that have nothing to do with whether THIS step (the rebuild) worked. That full smoke test
# belongs after OPEN-273's initial sync, once real data actually exists -- see that ticket.
# What this script verifies instead: the schema applies without unexpected errors, and api-v3
# can start up and serve its own OpenAPI schema against the new (empty) database without an
# import-time crash -- a real, narrower check that doesn't need data or an API key.
#
# The Mac's local Postgres and api-v3 both run in Docker (confirmed via `docker ps`):
#   ddp-openstates-postgres-1  (postgres:16-alpine, port 5433 -> 5432)
#   ddp-openstates-api-1       (ddp-openstates-api:local, port 8002 -> 80, network ddp-agents_default)
#
# Usage:
#   ./rebuild-local-replica.sh <schema-only-dump.sql> <new-database-name>
#
# <schema-only-dump.sql> must already exist -- for a real rebuild this comes from RDS
# (pg_dump --schema-only against the 7 tables, per ops/postgres-replica/rds/, run by whoever has
# RDS access; this script does not fetch it).
set -euo pipefail

SCHEMA_DUMP="${1:?Usage: $0 <schema-only-dump.sql> <new-database-name>}"
NEW_DB="${2:?Usage: $0 <schema-only-dump.sql> <new-database-name>}"

PG_CONTAINER="ddp-openstates-postgres-1"
PG_USER="openstates"
API_IMAGE="ddp-openstates-api:local"
API_NETWORK="ddp-agents_default"
SMOKE_TEST_CONTAINER="ddp-openstates-api-rebuild-smoketest"
SMOKE_TEST_PORT="8003"

if [ ! -f "$SCHEMA_DUMP" ]; then
  echo "FAIL: $SCHEMA_DUMP does not exist" >&2
  exit 1
fi

echo "== Confirm PostgreSQL major-version compatibility =="
# The subscriber (this Mac) must be the same or newer major version than the publisher (RDS) --
# this only confirms the LOCAL side's version; compare against the RDS version reported by
# ops/postgres-replica/rds/01-inspect.sql's own `SELECT version();` before trusting this alone.
docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d postgres -c "SELECT version();"

echo
echo "== Build the replacement database under a NEW name -- the existing 'openstates' database" \
     "is not touched =="
if docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d postgres -tAc \
    "SELECT 1 FROM pg_database WHERE datname = '$NEW_DB'" | grep -q 1; then
  echo "FAIL: database '$NEW_DB' already exists -- pick a name that isn't in use, or clean up" >&2
  echo "the leftover from a prior run first (this script does not drop anything for you)." >&2
  exit 1
fi
docker exec "$PG_CONTAINER" createdb -U "$PG_USER" "$NEW_DB"

# Apply the schema with ON_ERROR_STOP so any UNEXPECTED error fails this script loudly, rather
# than psql's default of continuing past errors (which silently masked a real failure when this
# was first tested -- an error scrolled by and the script still printed "PASS").
#
# One EXPECTED error is filtered out first, not silenced blindly: the 7-table scope (per plan
# §3.2) doesn't include opencivicdata_division, but opencivicdata_jurisdiction has a FOREIGN KEY
# to it (division_id -> opencivicdata_division.id). Confirmed by actually running this dump: the
# constraint fails to create since the referenced table doesn't exist in this scoped schema.
# division_id itself is still a plain, readable column -- only the FK's referential-integrity
# enforcement is lost, which the local replica (read-only, disposable, never itself the source of
# truth) doesn't need. This is the ONE specific constraint stripped, not a general
# "ignore unknown-table errors" mechanism -- a genuinely new unexpected error still fails the run.
# Statement-aware removal (not a per-line grep -- the ADD CONSTRAINT clause spans multiple
# lines, and a naive line-based filter first tried here left a syntactically broken partial
# "ALTER TABLE ONLY ..." statement with no closing clause, confirmed by actually running it and
# getting a syntax error, not just by reading the diff):
python3 -c "
import re, sys
with open('$SCHEMA_DUMP') as f:
    sql = f.read()
# Split on ';' followed by a newline -- safe here since this is a schema-only DDL dump with no
# string-literal data that could contain an embedded ';\n'.
statements = sql.split(';\n')
kept = [s for s in statements if 'opencivicdata_division' not in s]
removed = len(statements) - len(kept)
with open('$SCHEMA_DUMP.filtered', 'w') as f:
    f.write(';\n'.join(kept))
print(f'Filtered out {removed} statement(s) referencing opencivicdata_division', file=sys.stderr)
if removed != 1:
    print(f'FAIL: expected exactly 1 statement removed (the known FK constraint), got {removed} --', file=sys.stderr)
    print('investigate before trusting this filtered schema.', file=sys.stderr)
    sys.exit(1)
"
docker exec -i "$PG_CONTAINER" psql -v ON_ERROR_STOP=1 -U "$PG_USER" -d "$NEW_DB" < "$SCHEMA_DUMP.filtered"
rm -f "$SCHEMA_DUMP.filtered"
echo "PASS: schema applied to '$NEW_DB' with no unexpected errors"

echo
echo "== api-v3 startup check against the new (empty) database =="
# Confirms api-v3 can start against this schema and serve its own OpenAPI introspection without
# an import-time crash -- catches a schema/ORM mismatch even with zero rows. This is NOT the
# full data-bearing smoke test from plan §7.4 -- see the header comment for why that has to wait
# for OPEN-273's initial sync.
docker run --rm -d --network "$API_NETWORK" \
  -e "DATABASE_URL=postgresql://$PG_USER:openstates_dev@$PG_CONTAINER:5432/$NEW_DB" \
  -p "$SMOKE_TEST_PORT:80" \
  --name "$SMOKE_TEST_CONTAINER" \
  "$API_IMAGE" >/dev/null

cleanup() {
  docker stop "$SMOKE_TEST_CONTAINER" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "Waiting for the container to come up..."
started=""
for _ in $(seq 1 20); do
  if curl -sf "http://localhost:$SMOKE_TEST_PORT/openapi.json" >/dev/null 2>&1; then
    started="yes"
    break
  fi
  # Fail fast if the container already exited (crashed on startup) rather than waiting out the
  # full timeout for a container that's never coming up.
  if [ "$(docker inspect -f '{{.State.Running}}' "$SMOKE_TEST_CONTAINER" 2>/dev/null)" != "true" ]; then
    break
  fi
  sleep 1
done

if [ "$started" != "yes" ]; then
  echo "FAIL: api-v3 did not come up against the new schema within the timeout, or crashed --" >&2
  echo "recent container logs:" >&2
  docker logs --tail 50 "$SMOKE_TEST_CONTAINER" 2>&1 >&2 || true
  exit 1
fi
echo "PASS: api-v3 started and served /openapi.json against the new schema"

echo
echo "== Stopped here on purpose =="
echo "New database '$NEW_DB' now exists, with the schema applied and api-v3 confirmed able to"
echo "start against it. This script does NOT: repoint the real ddp-openstates-api-1 container's"
echo "DATABASE_URL, touch the existing 'openstates' database, or drop anything. Per"
echo "PLAN-rds-local-postgres-replication.md §3.5/§3.7, repointing api-v3 and retiring the old"
echo "database are separate, deliberate steps that come after OPEN-273's subscription brings in"
echo "real data and its own full data-bearing smoke test passes -- retain the old database until"
echo "at least one full scheduled LegBot batch run has completed against the new one with no"
echo "reported regression."
