#!/usr/bin/env bash
# OPEN-271, Phase 2 setup (PLAN-rds-local-postgres-replication.md §7.3).
# Run against RDS ONLY after 01-inspect.sql's checks pass (wal_level=logical,
# rds.logical_replication=1, headroom confirmed, all 7 tables found in the expected schema,
# REPLICA IDENTITY remediated where needed, and the executing role's own ownership/privilege
# over all 7 tables confirmed).
#
# Fetches the ddp_local_replication password from Secrets Manager (created by
# 00-generate-role-secret.sh) and pipes it directly to psql -- the password never touches disk
# or this script's own arguments/environment dump, matching this project's existing
# deploy/rotate-database-url.sh convention.
#
# Usage: PGHOST=<rds-endpoint> PGUSER=<admin-user> PGDATABASE=<database_name> ./02-setup.sh
set -euo pipefail

SECRET_ID="ddp-openstates/ddp_local_replication"
REGION="us-east-1"

: "${PGHOST:?Set PGHOST to the RDS endpoint}"
: "${PGUSER:?Set PGUSER to an admin identity confirmed by 01-inspect.sql to own/have authority over all 7 tables}"
: "${PGDATABASE:?Set PGDATABASE to the real database name}"

ROLE_PASSWORD="$(aws secretsmanager get-secret-value --region "$REGION" --secret-id "$SECRET_ID" --query 'SecretString' --output text)"

# Everything below runs as one transaction -- correction from pm-review round 1: the prior
# version ran these as separate ungrouped statements, so a late failure (e.g. CREATE PUBLICATION
# erroring after the role and grants already committed) could leave partial state. Wrapped so it's
# all-or-nothing; if this fails partway through, nothing above the failure point is left behind.
psql "host=$PGHOST dbname=$PGDATABASE user=$PGUSER sslmode=verify-full" <<SQL
BEGIN;

SET lock_timeout = '5s';  -- REPLICA IDENTITY changes take a lock; fail fast rather than hang
                           -- against a busy production table, per pm-review round 1.

-- ---- Remediate REPLICA IDENTITY, for any table 01-inspect.sql flagged ----
-- (uncomment/run only the ones 01-inspect.sql's query actually flagged):
-- ALTER TABLE public.opencivicdata_bill REPLICA IDENTITY FULL;
-- ALTER TABLE public.opencivicdata_legislativesession REPLICA IDENTITY FULL;
-- ALTER TABLE public.opencivicdata_jurisdiction REPLICA IDENTITY FULL;
-- ALTER TABLE public.opencivicdata_organization REPLICA IDENTITY FULL;
-- ALTER TABLE public.opencivicdata_billversion REPLICA IDENTITY FULL;
-- ALTER TABLE public.opencivicdata_billversionlink REPLICA IDENTITY FULL;
-- ALTER TABLE public.ddp_bill_version_document REPLICA IDENTITY FULL;

-- ---- Dedicated replication role (plan §3.4 item 1) ----
-- Never reused from an existing app/admin/Django account. Used ONLY by the local subscription
-- (OPEN-273) to pull replicated data -- never handed to a consumer.
CREATE ROLE ddp_local_replication WITH LOGIN PASSWORD '$ROLE_PASSWORD';
GRANT rds_replication TO ddp_local_replication;
GRANT CONNECT ON DATABASE $PGDATABASE TO ddp_local_replication;
GRANT USAGE ON SCHEMA public TO ddp_local_replication;
GRANT SELECT ON
  public.opencivicdata_bill, public.opencivicdata_legislativesession,
  public.opencivicdata_jurisdiction, public.opencivicdata_organization,
  public.opencivicdata_billversion, public.opencivicdata_billversionlink,
  public.ddp_bill_version_document
TO ddp_local_replication;

-- ---- Table-scoped publication (plan §3.2) -- NOT FOR ALL TABLES ----
-- Naming exactly these 7 tables, not a guessed subset and not a general-purpose mirror.
CREATE PUBLICATION ddp_legbot_publication FOR TABLE
  public.opencivicdata_bill, public.opencivicdata_legislativesession,
  public.opencivicdata_jurisdiction, public.opencivicdata_organization,
  public.opencivicdata_billversion, public.opencivicdata_billversionlink,
  public.ddp_bill_version_document;

COMMIT;

-- ---- Verify (outside the transaction, read-only) ----
\echo 'Publication tables (expect exactly the 7 above, nothing more, nothing less):'
SELECT schemaname, tablename FROM pg_publication_tables WHERE pubname = 'ddp_legbot_publication' ORDER BY tablename;

-- Correction from pm-review round 1: GRANT rds_replication grants MEMBERSHIP, it does NOT set
-- pg_roles.rolreplication -- that column stays false for this role even when correctly set up.
-- Checking rolreplication=true here would be a false negative. Check membership instead:
\echo 'Expect true (replication role membership, NOT rolreplication):'
SELECT pg_has_role('ddp_local_replication', 'rds_replication', 'member');
SQL

echo "Done. Run 03-verify-role-can-read.sh next to confirm the new role can actually connect and read."
