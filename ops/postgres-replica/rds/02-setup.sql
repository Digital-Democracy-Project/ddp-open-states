-- OPEN-271, Phase 2 setup (PLAN-rds-local-postgres-replication.md §7.3).
-- Run against RDS ONLY after 01-inspect.sql's checks pass (wal_level=logical,
-- rds.logical_replication=1, headroom confirmed, REPLICA IDENTITY remediated where needed).
--
-- <secure-password> below must come from a real secret generator at run time (e.g. `openssl
-- rand -base64 32`) and be stored via Secrets Manager / this project's existing credential
-- convention -- never committed here, never typed inline into a file that gets saved.
-- <database_name> is the actual RDS database name this plan targets.

-- ---- Remediate REPLICA IDENTITY first, for any table 01-inspect.sql flagged ----
-- (uncomment/run only the ones actually needed -- 01-inspect.sql's own comment explains which):
-- ALTER TABLE opencivicdata_bill REPLICA IDENTITY FULL;
-- ALTER TABLE opencivicdata_legislativesession REPLICA IDENTITY FULL;
-- ALTER TABLE opencivicdata_jurisdiction REPLICA IDENTITY FULL;
-- ALTER TABLE opencivicdata_organization REPLICA IDENTITY FULL;
-- ALTER TABLE opencivicdata_billversion REPLICA IDENTITY FULL;
-- ALTER TABLE opencivicdata_billversionlink REPLICA IDENTITY FULL;
-- ALTER TABLE ddp_bill_version_document REPLICA IDENTITY FULL;

-- ---- Dedicated replication role (plan §3.4 item 1) ----
-- Never reused from an existing app/admin/Django account. Used ONLY by the local subscription
-- (OPEN-273) to pull replicated data -- never handed to a consumer.
CREATE ROLE ddp_local_replication WITH LOGIN PASSWORD '<secure-password-generated-at-run-time>';
GRANT rds_replication TO ddp_local_replication;
GRANT CONNECT ON DATABASE <database_name> TO ddp_local_replication;
GRANT USAGE ON SCHEMA public TO ddp_local_replication;
GRANT SELECT ON
  opencivicdata_bill, opencivicdata_legislativesession, opencivicdata_jurisdiction,
  opencivicdata_organization, opencivicdata_billversion, opencivicdata_billversionlink,
  ddp_bill_version_document
TO ddp_local_replication;

-- ---- Table-scoped publication (plan §3.2) -- NOT FOR ALL TABLES ----
-- Naming exactly these 7 tables, not a guessed subset and not a general-purpose mirror.
CREATE PUBLICATION ddp_legbot_publication FOR TABLE
  opencivicdata_bill, opencivicdata_legislativesession, opencivicdata_jurisdiction,
  opencivicdata_organization, opencivicdata_billversion, opencivicdata_billversionlink,
  ddp_bill_version_document;

-- ---- Verify ----
SELECT * FROM pg_publication WHERE pubname = 'ddp_legbot_publication';
SELECT * FROM pg_publication_tables WHERE pubname = 'ddp_legbot_publication';
-- Expect exactly the 7 tables above in pg_publication_tables, nothing more, nothing less.

SELECT rolname, rolreplication FROM pg_roles WHERE rolname = 'ddp_local_replication';
-- Expect rolreplication = true (via the rds_replication grant).
