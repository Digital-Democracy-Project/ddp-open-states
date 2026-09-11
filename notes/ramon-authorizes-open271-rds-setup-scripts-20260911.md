# Ramon: proceed with OPEN-271's remaining RDS-side setup scripts

Nice work on the reboot. Ramon's explicit go-ahead: proceed now with the rest of OPEN-271 --
`ops/postgres-replica/rds/00-generate-role-secret.sh` through `03-verify-role-can-read.sh`,
against real RDS. Full runbook is in that directory's own `README.md`; summarizing the order
and what to watch for below so it's all in one place.

## Order

0. **`00-generate-role-secret.sh`** -- creates the `ddp-openstates/ddp_local_replication`
   Secrets Manager secret with a freshly generated password. **Skip if it already exists**
   (`aws secretsmanager describe-secret --secret-id ddp-openstates/ddp_local_replication`) --
   I don't have confirmation either way whether this already ran before the reboot, so please
   check first rather than assume.
1. **`01-inspect.sql`** (read-only) -- worth re-running fresh now that `rds.logical_replication`
   is actually `on` (your last real run of this, `notes/open271-01-inspect-results-20260911.md`,
   was before the reboot and correctly showed it as the blocker). Confirm: `wal_level=logical`
   and `rds.logical_replication=1` both show live now, the exact-7-tables check still passes,
   REPLICA IDENTITY status per table (expect no remediation needed, matching your earlier
   result), and slot/sender capacity headroom.
2. **`02-setup.sh`** -- the real DDL: creates `ddp_local_replication` (dedicated role, never
   reused), the table-scoped `ddp_legbot_publication` (exactly the 7 tables, not
   `FOR ALL TABLES`), and any REPLICA IDENTITY remediation `01-inspect.sql` flags (none
   expected). All one transaction. Verification inside it checks `pg_has_role(...,'member')`,
   not `pg_roles.rolreplication` (that column doesn't get set by `GRANT rds_replication` --
   real gap found and fixed earlier this epic).
3. **`03-verify-role-can-read.sh`** -- confirms the new role can actually connect, `SELECT` all
   7 tables for real, and genuinely cannot write.

## Report back (same as the README's own "After running" checklist)

- `01-inspect.sql`'s full fresh output.
- `02-setup.sh`'s verification output (publication contents, the `pg_has_role` check) -- paste
  the actual output, not a summary.
- `03-verify-role-can-read.sh`'s output.

Once this lands, OPEN-272 (rebuild-local-replica.sh) can finally run against a real RDS
schema-only dump instead of just the Docker-loopback stand-in it was tested against, and
OPEN-273 (the local subscription) can stand up for real after that. Both are otherwise
merged and ready.

Separately, still open and not part of this ask: the ~56%-done `us refresh-extraction`
retry (holding on that specifically) and the IAM policy tightening Ramon flagged (narrowing
`pg:*` to the actual `ddp-openstates-logrep` parameter group once things settle) -- neither
blocks this.
