#!/usr/bin/env bash
# OPEN-277: schema-comparison script (PLAN-rds-local-postgres-replication.md §7.7, §7.9). Compares
# RDS vs. the local replica for exactly the 7 tables this plan's publication carries (§3.2) --
# not a general schema-diff tool. Run manually after any Django migration touching these 7
# tables (§7.9's own procedure), not on a schedule.
#
# Checks, per table:
#   1. Does the table exist on both sides?
#   2. Do the column name/type/nullability triples match?
# Compared keyed by COLUMN NAME (sorted), not physical ordinal position -- pm-review round 1:
# Postgres logical replication itself matches columns by name, not position, so two schemas with
# the same named columns in a different physical order (e.g. independently recreated at some
# point in each side's own history) replicate perfectly correctly; comparing by ordinal position
# would falsely flag that as a mismatch. Uses pg_attribute + format_type() rather than
# information_schema.columns' data_type/character_maximum_length pair -- confirmed against the
# real schema that format_type() correctly distinguishes array types (text[] vs text) and gives
# full precision (e.g. "character varying(25)") in one string, which the information_schema pair
# does not capture correctly for this schema's actual array-typed columns
# (opencivicdata_bill.classification/subject).
# Does NOT check indexes, constraints, or anything beyond column shape -- the plan's own scope for
# this script (§7.7) is column-level agreement, not a full schema audit.
#
# Usage:
#   RDS_HOST=<rds-endpoint> RDS_REPLICATION_PASSWORD=<ddp_local_replication's password, from
#     Secrets Manager -- ops/postgres-replica/rds/00-generate-role-secret.sh> \
#     ./compare-schema.sh <local-database-name>
#
# Reuses the ddp_local_replication credential (§3.4 item 1) for this read -- it already has
# SELECT scoped to exactly these 7 tables (OPEN-271), which is also exactly what pg_attribute
# needs to expose their column metadata. Not a new credential: this is a read against the same
# 7-table scope that role already exists for, not a wider grant.
set -uo pipefail

LOCAL_DB="${1:?Usage: $0 <local-database-name>}"
PG_CONTAINER="${PG_CONTAINER:-ddp-openstates-postgres-1}"
PG_USER="${PG_USER:-openstates}"

: "${RDS_HOST:?Set RDS_HOST to the RDS endpoint}"
: "${RDS_REPLICATION_PASSWORD:?Set RDS_REPLICATION_PASSWORD to ddp_local_replications password}"
RDS_PORT="${RDS_PORT:-5432}"
RDS_DATABASE="${RDS_DATABASE:-openstates}"

if [[ ! "$LOCAL_DB" =~ ^[a-z_][a-z0-9_]*$ ]]; then
  echo "FAIL: '$LOCAL_DB' is not a safe database name" >&2
  exit 1
fi

# The plan's own §3.2 table list, read directly from api-v3's actual query construction -- not a
# guessed subset. Order matters for nothing here; this is just what gets iterated.
TABLES=(
  opencivicdata_bill
  opencivicdata_legislativesession
  opencivicdata_jurisdiction
  opencivicdata_organization
  opencivicdata_billversion
  opencivicdata_billversionlink
  ddp_bill_version_document
)

# pm-review round 1: the password no longer appears in the connection string / process args
# (visible to anything that can see this process's argv, e.g. `ps`) -- passed via PGPASSWORD
# instead, matching psql's own documented mechanism for exactly this concern.
RDS_CONN="host=$RDS_HOST port=$RDS_PORT dbname=$RDS_DATABASE user=ddp_local_replication sslmode=verify-full"

COLUMN_QUERY="
  SELECT a.attname || '|' || format_type(a.atttypid, a.atttypmod) || '|' || a.attnotnull
  FROM pg_attribute a
  JOIN pg_class c ON c.oid = a.attrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'public' AND c.relname = '__TABLE__'
    AND a.attnum > 0 AND NOT a.attisdropped
  ORDER BY a.attname;
"

mismatch_found=0

for table in "${TABLES[@]}"; do
  echo "== $table =="
  query="${COLUMN_QUERY//__TABLE__/$table}"

  rds_columns="$(PGPASSWORD="$RDS_REPLICATION_PASSWORD" psql "$RDS_CONN" -tAc "$query" 2>&1)"
  rds_rc=$?

  local_columns="$(docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$LOCAL_DB" -tAc "$query" 2>&1)"
  local_rc=$?

  if [ "$rds_rc" -ne 0 ]; then
    echo "FAIL: could not query RDS for $table: $rds_columns" >&2
    mismatch_found=1
    continue
  fi
  if [ "$local_rc" -ne 0 ]; then
    echo "FAIL: could not query local replica for $table: $local_columns" >&2
    mismatch_found=1
    continue
  fi

  if [ -z "$rds_columns" ]; then
    echo "FAIL: $table does not exist on RDS (or ddp_local_replication cannot see it)" >&2
    mismatch_found=1
    continue
  fi
  if [ -z "$local_columns" ]; then
    echo "FAIL: $table does not exist on the local replica ($LOCAL_DB)" >&2
    mismatch_found=1
    continue
  fi

  if [ "$rds_columns" = "$local_columns" ]; then
    echo "PASS: columns match ($(echo "$rds_columns" | wc -l | tr -d ' ') columns)"
  else
    echo "FAIL: column mismatch" >&2
    echo "-- RDS:" >&2
    echo "$rds_columns" >&2
    echo "-- local ($LOCAL_DB):" >&2
    echo "$local_columns" >&2
    mismatch_found=1
  fi
done

echo
if [ "$mismatch_found" -eq 0 ]; then
  echo "PASS: all 7 tables match between RDS and the local replica."
  exit 0
else
  echo "FAIL: at least one table has a schema mismatch or is missing -- see above." >&2
  echo "Per plan §7.9: for an additive Django migration, apply the equivalent change to the" >&2
  echo "local replica manually (logical replication does not propagate DDL). For a destructive" >&2
  echo "or incompatible change, rebuild the replica instead (§7.8) rather than hand-patching it." >&2
  exit 1
fi
