-- OPEN-271, Phase 2 inspection (PLAN-rds-local-postgres-replication.md §7.2).
-- READ-ONLY. Makes no changes. Run against RDS as any role with enough privilege to read these
-- system views (the existing RDS admin role already used for other maintenance is sufficient).
--
-- Run this BEFORE 02-setup.sql. If any check below needs a parameter-group change (marked),
-- that requires a maintenance window and Ramon's explicit sign-off, separately from the plan's
-- own approval -- do not schedule that reboot unilaterally.

SHOW wal_level;                              -- must be 'logical'
SHOW rds.logical_replication;                -- must be '1' (may require a parameter-group change
                                              -- and a reboot -- confirm before assuming either;
                                              -- the change itself is trivially reversible, the
                                              -- reboot is the part needing a maintenance window)
SHOW max_replication_slots;
SHOW max_wal_senders;
SHOW max_logical_replication_workers;

-- The SHOWs above give configured maxima, not available headroom -- confirm there's room for
-- one more slot/sender/worker before assuming there is:
SELECT count(*) AS slots_in_use FROM pg_replication_slots;
SELECT count(*) AS senders_in_use FROM pg_stat_replication;
-- If either count is already at its respective max shown above, this needs a parameter-group
-- bump (same reboot/maintenance-window caveat as above), not just enabling logical replication
-- and assuming a slot is free.

-- Confirm the 7 real tables this plan replicates actually have a usable replica identity.
-- 'n' (nothing set) is never usable for UPDATE/DELETE replication; 'd' (default, uses the
-- primary key) is only usable if a primary key actually exists -- so a table with 'd' AND no
-- primary key is just as unusable as 'n'. 'f' (full) is already fine. 'i' (a specific index)
-- needs that index confirmed valid separately.
SELECT n.nspname, c.relname, c.relreplident,
  NOT EXISTS (SELECT 1 FROM pg_index i WHERE i.indrelid = c.oid AND i.indisprimary) AS no_primary_key
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'r'
  AND n.nspname NOT IN ('pg_catalog', 'information_schema')
  AND c.relname IN (
    'opencivicdata_bill', 'opencivicdata_legislativesession', 'opencivicdata_jurisdiction',
    'opencivicdata_organization', 'opencivicdata_billversion', 'opencivicdata_billversionlink',
    'ddp_bill_version_document'
  );
-- For any row where relreplident='n', OR relreplident='d' AND no_primary_key=true: remediate
-- with (see 02-setup.sql for the exact statement, run per affected table):
--   ALTER TABLE <table_name> REPLICA IDENTITY FULL;
-- (or, if a suitable unique NOT NULL index exists on that table, the cheaper
--   ALTER TABLE <table_name> REPLICA IDENTITY USING INDEX <index_name>;
-- -- check per table rather than defaulting all seven to FULL.)

-- Confirm PostgreSQL major-version compatibility ahead of Phase 3 (rebuilding the Mac's local
-- Postgres, OPEN-272) -- the subscriber must be the same or newer major version than this
-- publisher; run this against the Mac's local Postgres too and compare:
SELECT version();
