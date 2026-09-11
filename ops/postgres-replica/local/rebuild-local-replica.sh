#!/usr/bin/env bash
# OPEN-272: build the Mac's replacement local Postgres alongside the existing one
# (PLAN-rds-local-postgres-replication.md §3.5/§7.4). Non-destructive: builds under a NEW
# database name and verifies the schema applies cleanly + is actually queryable. STOPS there --
# repointing the real api-v3 container and retiring the old database are deliberately NOT
# automated here (see "Stopped here on purpose" at the end).
#
# Correction found by actually running this against a real schema dump (not just reading it):
# this does NOT run the full authenticated, data-bearing api-v3 smoke test from plan §7.4
# (curl .../bills/<id>?include=versions). That test needs (a) real bill data, which doesn't
# exist until OPEN-273's subscription completes its initial copy, and (b) a valid API key
# checked against api-v3's own Profile table, which isn't one of the 7 replicated tables at all
# and has zero rows on a schema-only rebuild regardless. Every api-v3 route that touches real
# data requires that API key (confirmed by reading api-v3/api/jurisdictions.py and auth.py --
# there is no unauthenticated route that queries any of the 7 tables), so there's no way to
# route around this at the HTTP layer at this stage. That full smoke test belongs after
# OPEN-273's initial sync, once real data actually exists -- see that ticket.
#
# What this script verifies instead (pm-review round 1 correction: the previous version claimed
# an api-v3 container-startup check "catches an ORM/schema mismatch" -- it doesn't, since
# /openapi.json is generated from route/model definitions and FastAPI doesn't need a DB
# connection to serve it, confirmed by reading api-v3/api/main.py): (1) direct SQL queries
# against all 7 tables in the new database, proving the schema is genuinely queryable at the SQL
# level -- the ORM-relevant part of "does this schema work" that doesn't need an API key; and
# (2) that api-v3 can still start and serve HTTP against the new schema without crashing --
# a real but narrower signal than schema validation, described honestly as just that.
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
# RDS access; this script does not fetch it). <new-database-name> must be a plain lowercase
# identifier (letters, digits, underscores) -- validated below, not just assumed safe.
set -euo pipefail

SCHEMA_DUMP="${1:?Usage: $0 <schema-only-dump.sql> <new-database-name>}"
NEW_DB="${2:?Usage: $0 <schema-only-dump.sql> <new-database-name>}"

PG_CONTAINER="ddp-openstates-postgres-1"
PG_USER="openstates"
API_IMAGE="ddp-openstates-api:local"
API_NETWORK="ddp-agents_default"
SMOKE_TEST_CONTAINER="ddp-openstates-api-rebuild-smoketest"
SMOKE_TEST_PORT="8003"

EXPECTED_TABLES=(
  opencivicdata_bill opencivicdata_legislativesession opencivicdata_jurisdiction
  opencivicdata_organization opencivicdata_billversion opencivicdata_billversionlink
  ddp_bill_version_document
)

if [ ! -f "$SCHEMA_DUMP" ]; then
  echo "FAIL: $SCHEMA_DUMP does not exist" >&2
  exit 1
fi

# Correction, pm-review round 1: NEW_DB gets interpolated into SQL and shell commands below --
# validate it's a plain safe identifier now rather than assuming so, instead of discovering a
# quoting problem partway through.
if [[ ! "$NEW_DB" =~ ^[a-z_][a-z0-9_]*$ ]]; then
  echo "FAIL: '$NEW_DB' is not a safe database name (expected: lowercase letters, digits," >&2
  echo "underscores, not starting with a digit)." >&2
  exit 1
fi

echo "== Confirm PostgreSQL major-version compatibility =="
# The subscriber (this Mac) must be the same or newer major version than the publisher (RDS) --
# this only confirms the LOCAL side's version; compare against the RDS version reported by
# ops/postgres-replica/rds/01-inspect.sql's own `SELECT version();` before trusting this alone.
# This is a manual comparison an operator must actually do -- this script cannot check the RDS
# side itself (no RDS access, see ops/postgres-replica/rds/README.md).
docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d postgres -c "SELECT version();"

echo
echo "== Filter the schema dump (before creating anything, so a filtering problem leaves" \
     "nothing behind) =="
# Correction, pm-review round 1: anchored to the exact known ALTER TABLE/FOREIGN KEY block for
# opencivicdata_jurisdiction.division_id -> opencivicdata_division.id, not a broad "any statement
# mentioning this table name" substring match -- narrower match means a future, different,
# genuinely-unexpected statement mentioning this table elsewhere (a comment, say) is NOT silently
# swallowed by this filter. The 7-table scope (per plan §3.2) doesn't include
# opencivicdata_division; this FK is the one confirmed-real cross-scope reference (see
# ops/postgres-replica/local/README.md for how this was found). division_id itself remains a
# plain, readable column -- only the FK's referential-integrity enforcement is lost, which the
# local replica (read-only, disposable, never itself the source of truth) doesn't need.
FILTERED_DUMP="$(mktemp)"
trap 'rm -f "$FILTERED_DUMP"' EXIT

# SCHEMA_DUMP passed via argv (correction, pm-review round 1: the prior version interpolated the
# path into the Python source string, which breaks or misbehaves for a path containing a quote).
python3 -c "
import re, sys
schema_dump_path = sys.argv[1]
filtered_path = sys.argv[2]
with open(schema_dump_path) as f:
    sql = f.read()
# Split on ';' followed by a newline -- safe here since this is a schema-only DDL dump with no
# string-literal data that could contain an embedded ';\n'. A real RDS dump could in principle
# contain a dollar-quoted function/trigger body with an embedded ';\n' -- none of the 7 tables in
# this plan have triggers or functions attached (confirmed against this dump), but if a future
# dump does, this split would need revisiting rather than trusted blindly.
statements = sql.split(';\n')
fk_pattern = re.compile(
    r'ALTER TABLE ONLY public\.opencivicdata_jurisdiction\s*\n\s*'
    r'ADD CONSTRAINT \S+ FOREIGN KEY \(division_id\) REFERENCES public\.opencivicdata_division',
)
matched = [s for s in statements if fk_pattern.search(s)]
if len(matched) != 1:
    print(f'FAIL: expected exactly 1 statement matching the known jurisdiction->division FK,', file=sys.stderr)
    print(f'found {len(matched)} -- investigate before trusting this filtered schema.', file=sys.stderr)
    sys.exit(1)
kept = [s for s in statements if not fk_pattern.search(s)]
with open(filtered_path, 'w') as f:
    f.write(';\n'.join(kept))
print('Filtered out exactly the known jurisdiction->division FK constraint.', file=sys.stderr)
" "$SCHEMA_DUMP" "$FILTERED_DUMP"

echo
echo "== Build the replacement database under a NEW name -- the existing 'openstates' database" \
     "is not touched =="
existing_db_check="$(docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d postgres -tAc \
    "SELECT 1 FROM pg_database WHERE datname = '$NEW_DB'")"
existing_db_check_status=$?
if [ "$existing_db_check_status" -ne 0 ]; then
  echo "FAIL: could not check whether '$NEW_DB' already exists (psql itself failed) -- fix that" >&2
  echo "before proceeding, don't assume the database doesn't exist just because the check errored." >&2
  exit 1
fi
if [ "$existing_db_check" = "1" ]; then
  echo "FAIL: database '$NEW_DB' already exists -- pick a name that isn't in use, or clean up" >&2
  echo "the leftover from a prior run first (this script does not drop anything for you)." >&2
  exit 1
fi
docker exec "$PG_CONTAINER" createdb -U "$PG_USER" "$NEW_DB"

# Apply the (already-filtered) schema with ON_ERROR_STOP so any UNEXPECTED error fails this
# script loudly, rather than psql's default of continuing past errors (which silently masked a
# real failure when this was first tested -- an error scrolled by and the script still printed
# "PASS").
docker exec -i "$PG_CONTAINER" psql -v ON_ERROR_STOP=1 -U "$PG_USER" -d "$NEW_DB" < "$FILTERED_DUMP"
echo "PASS: schema applied to '$NEW_DB' with no unexpected errors"
echo "If this fails partway through, '$NEW_DB' is left in a partially-restored state -- it is not"
echo "dropped automatically. Before retrying, drop it by hand:"
echo "  docker exec $PG_CONTAINER psql -U $PG_USER -d postgres -c 'DROP DATABASE $NEW_DB;'"

echo
echo "== Confirm the schema is genuinely queryable (direct SQL, no API key needed) =="
# Correction, pm-review round 1: this is the real "does the ORM-relevant schema work" check --
# every api-v3 route that touches these tables requires an API key checked against a Profile
# table with zero rows at this stage (confirmed by reading api-v3/api/jurisdictions.py), so there
# is no unauthenticated HTTP route to verify this through instead. Query all 7 tables directly.
query=""
for t in "${EXPECTED_TABLES[@]}"; do
  query+="SELECT '$t' AS table_name, count(*) AS row_count FROM $t UNION ALL "
done
query="${query% UNION ALL }"
echo "Row counts (expect 0 for all -- this is a schema-only rebuild, real data arrives via"
echo "OPEN-273's subscription):"
docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$NEW_DB" -c "$query"

echo "Confirm the filtered FK is genuinely gone (expect 0 rows):"
docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$NEW_DB" -tAc "
SELECT count(*) FROM pg_constraint c
JOIN pg_class t ON t.oid = c.conrelid
WHERE t.relname = 'opencivicdata_jurisdiction' AND c.contype = 'f'
  AND pg_get_constraintdef(c.oid) LIKE '%opencivicdata_division%';
"
echo "PASS: schema is queryable at the SQL level"

echo
echo "== api-v3 startup check against the new (empty) database =="
# Confirms api-v3 can start against this schema and serve HTTP without an import-time crash --
# a real but narrower signal than "schema is compatible" (corrected above): /openapi.json is
# generated from route/model definitions and doesn't require a database connection (confirmed by
# reading api-v3/api/main.py), so this does NOT independently confirm ORM/schema compatibility --
# the SQL-level check above is what actually does that.
#
# Correction, pm-review round 1: no longer --rm -- a crash would remove the container before
# `docker logs` could run. Cleanup below explicitly removes it after collecting logs if needed.
docker run -d --network "$API_NETWORK" \
  -e "DATABASE_URL=postgresql://$PG_USER:openstates_dev@$PG_CONTAINER:5432/$NEW_DB" \
  -p "$SMOKE_TEST_PORT:80" \
  --name "$SMOKE_TEST_CONTAINER" \
  "$API_IMAGE" >/dev/null

cleanup() {
  rm -f "$FILTERED_DUMP"
  docker rm -f "$SMOKE_TEST_CONTAINER" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "Waiting for the container to come up..."
started=""
for _ in $(seq 1 30); do
  if curl -sf "http://localhost:$SMOKE_TEST_PORT/openapi.json" >/dev/null 2>&1; then
    started="yes"
    break
  fi
  if [ "$(docker inspect -f '{{.State.Running}}' "$SMOKE_TEST_CONTAINER" 2>/dev/null)" != "true" ]; then
    break
  fi
  sleep 1
done

if [ "$started" != "yes" ]; then
  echo "FAIL: api-v3 did not come up against the new schema within the timeout, or crashed --" >&2
  echo "recent container logs:" >&2
  docker logs --tail 50 "$SMOKE_TEST_CONTAINER" >&2 2>&1 || true
  exit 1
fi
echo "PASS: api-v3 started and served HTTP against the new schema (container-startup signal only"
echo "-- see above for the real schema-compatibility check)"

echo
echo "== Stopped here on purpose =="
echo "New database '$NEW_DB' now exists, schema applied and confirmed queryable. This script does"
echo "NOT: repoint the real ddp-openstates-api-1 container's DATABASE_URL, touch the existing"
echo "'openstates' database, or drop anything. Per PLAN-rds-local-postgres-replication.md"
echo "§3.5/§3.7, repointing api-v3 and retiring the old database are separate, deliberate steps"
echo "that come after OPEN-273's subscription brings in real data and its own full data-bearing"
echo "smoke test passes -- retain the old database until at least one full scheduled LegBot batch"
echo "run has completed against the new one with no reported regression."
