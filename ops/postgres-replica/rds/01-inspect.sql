-- OPEN-271, Phase 2 inspection (PLAN-rds-local-postgres-replication.md §7.2).
-- READ-ONLY. Makes no changes. Run against RDS as any role with enough privilege to read these
-- system views (the existing RDS admin role already used for other maintenance is sufficient).
--
-- Run this BEFORE 02-setup.sh. If any check below needs a parameter-group change (marked),
-- that requires a maintenance window and Ramon's explicit sign-off, separately from the plan's
-- own approval -- do not schedule that reboot unilaterally.

SHOW wal_level;                              -- must be 'logical'
SHOW rds.logical_replication;                -- must be '1' (may require a parameter-group change
                                              -- and a reboot -- confirm before assuming either;
                                              -- the change itself is trivially reversible, the
                                              -- reboot is the part needing a maintenance window)
SHOW max_replication_slots;
SHOW max_wal_senders;

-- The SHOWs above give configured maxima, not available headroom -- confirm there's room for
-- one more slot/sender before assuming there is. (max_logical_replication_workers is a
-- subscriber-side setting for the Mac's apply/tablesync workers -- checked separately in
-- OPEN-273, not here; the publisher-side constraints that actually matter for this step are
-- replication slots and WAL senders.)
SELECT count(*) AS slots_in_use FROM pg_replication_slots;
SELECT count(*) AS senders_in_use FROM pg_stat_replication;
-- If either count is already at its respective max shown above, this needs a parameter-group
-- bump (same reboot/maintenance-window caveat as above), not just enabling logical replication
-- and assuming a slot is free.

-- Confirm exactly the 7 real tables this plan replicates exist, in the expected schema, before
-- anything else runs -- correction from pm-review round 1: table names alone (unqualified) risk
-- matching the wrong object if a same-named table exists in another schema, and a missing table
-- should be caught here, not partway through 02-setup.sh after the role/grants already exist.
WITH expected(schema_name, table_name) AS (
  VALUES
    ('public', 'opencivicdata_bill'), ('public', 'opencivicdata_legislativesession'),
    ('public', 'opencivicdata_jurisdiction'), ('public', 'opencivicdata_organization'),
    ('public', 'opencivicdata_billversion'), ('public', 'opencivicdata_billversionlink'),
    ('public', 'ddp_bill_version_document')
)
SELECT e.schema_name, e.table_name,
  (c.oid IS NOT NULL) AS exists_as_expected
FROM expected e
LEFT JOIN pg_namespace n ON n.nspname = e.schema_name
LEFT JOIN pg_class c ON c.relname = e.table_name AND c.relnamespace = n.oid AND c.relkind = 'r';
-- Expect all 7 rows with exists_as_expected = true. Stop here (don't run 02-setup.sh) if any
-- row is false -- that table is missing or lives in a different schema than assumed, and every
-- schema-qualified statement in 02-setup.sh needs correcting first, not run against a guess.

-- For each of the 7, confirm a usable replica identity. 'n' (nothing set) is never usable for
-- UPDATE/DELETE replication; 'd' (default, uses the primary key) is only usable if a primary
-- key actually exists -- so 'd' with no primary key is just as unusable as 'n'. 'f' (full) is
-- already fine. 'i' (a specific index) needs that index identified and confirmed valid --
-- correction from pm-review round 1: the prior version flagged this case but didn't actually
-- surface which index or whether it's usable, so this now joins pg_index directly.
SELECT n.nspname, c.relname, c.relreplident,
  NOT EXISTS (SELECT 1 FROM pg_index i WHERE i.indrelid = c.oid AND i.indisprimary) AS no_primary_key,
  ri.indexrelid::regclass AS replica_identity_index,
  ri.indisvalid AS replica_identity_index_is_valid
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
LEFT JOIN pg_index ri ON ri.indrelid = c.oid AND ri.indisreplident
WHERE c.relkind = 'r'
  AND n.nspname = 'public'
  AND c.relname IN (
    'opencivicdata_bill', 'opencivicdata_legislativesession', 'opencivicdata_jurisdiction',
    'opencivicdata_organization', 'opencivicdata_billversion', 'opencivicdata_billversionlink',
    'ddp_bill_version_document'
  );
-- Remediate (see 02-setup.sh) any row where: relreplident='n'; OR relreplident='d' AND
-- no_primary_key=true; OR relreplident='i' AND replica_identity_index_is_valid is not true.

-- Confirm the executing role can actually perform the ownership-sensitive operations
-- 02-setup.sh needs (ALTER TABLE ... REPLICA IDENTITY, GRANT SELECT, CREATE PUBLICATION) --
-- correction from pm-review round 1: the README asserted "the existing RDS admin role is
-- sufficient" without a check; RDS's master/admin user is not automatically the owner of every
-- Django-created table. Confirm ownership or an equivalent grant path before assuming it:
SELECT c.relname, pg_get_userbyid(c.relowner) AS owner, current_user,
  has_table_privilege(current_user, c.oid, 'SELECT') AS can_select
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'r' AND n.nspname = 'public'
  AND c.relname IN (
    'opencivicdata_bill', 'opencivicdata_legislativesession', 'opencivicdata_jurisdiction',
    'opencivicdata_organization', 'opencivicdata_billversion', 'opencivicdata_billversionlink',
    'ddp_bill_version_document'
  );
-- If current_user isn't the owner of all 7 and isn't a superuser-equivalent RDS role, ALTER
-- TABLE/GRANT may fail partway through 02-setup.sh -- confirm the actual execution identity has
-- the needed authority before running it, don't assume the admin credential already used for
-- other maintenance covers this.

-- Confirm PostgreSQL major-version compatibility ahead of Phase 3 (rebuilding the Mac's local
-- Postgres, OPEN-272) -- the subscriber must be the same or newer major version than this
-- publisher; run this against the Mac's local Postgres too and compare:
SELECT version();
