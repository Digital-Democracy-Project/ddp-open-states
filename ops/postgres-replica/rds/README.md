# RDS-side setup for LegBot's logical replication (OPEN-271)

Part of the [OPEN-269](https://digitaldemocracyproject.atlassian.net/browse/OPEN-269) epic,
building `PLAN-rds-local-postgres-replication.md`. **This session (the Mac-side dev checkout)
has no RDS or Secrets Manager access** — confirmed via `aws rds describe-db-instances` /
`aws secretsmanager list-secrets`, both `AccessDenied` for the `ddp-scraper` IAM identity
available here (see OPEN-270's own findings doc for the full check). These scripts are written
here for review, but **must be run by whichever identity already has RDS admin access** (the
same one `resolve_rds_database_url()` already resolves for other production work) — not from
this checkout.

## Order

0. **`00-generate-role-secret.sh`** — run once. Creates a new AWS Secrets Manager secret
   (`ddp-openstates/ddp_local_replication`) with a freshly Secrets-Manager-generated password —
   matching this repo's existing `deploy/rotate-database-url.sh` convention for the RDS master
   secret. The password never appears in this script, any file, or shell history at any point.
   Skip if the secret already exists (check with `aws secretsmanager describe-secret`).
1. **`01-inspect.sql`** — read-only. Confirms `wal_level`, `rds.logical_replication`, replication
   slot/sender capacity headroom, that all 7 expected tables actually exist in the expected
   schema, `REPLICA IDENTITY` status for each, and that the identity running `02-setup.sh` has
   the ownership/privilege it needs (don't assume the RDS admin role automatically owns
   Django-created tables). If `rds.logical_replication` needs enabling, that's a parameter-group
   change and an RDS **reboot** — needs a maintenance window and **Ramon's explicit sign-off**,
   separately from the plan's own approval. Do not schedule that reboot without it.
2. **`02-setup.sh`** — makes real changes, all in one transaction (so a late failure doesn't
   leave partial state). Fetches the secret from step 0 and pipes it straight to `psql` --
   remediates any `REPLICA IDENTITY` gap `01-inspect.sql` found (with a `lock_timeout` set so it
   fails fast rather than hanging against a busy production table), creates the dedicated
   `ddp_local_replication` role (never reused from an existing app/admin/Django account, never
   handed to a consumer), and creates the table-scoped `ddp_legbot_publication` naming exactly
   the real 7 tables — not `FOR ALL TABLES`.
3. **`03-verify-role-can-read.sh`** — confirms the new role can actually connect and `SELECT`
   all 7 tables (not just that the catalog rows exist), and that it genuinely cannot write.

**Correction from pm-review round 1**: the original version of `02-setup.sql` required an
operator to type a real password inline into a file before running it — directly contradicting
its own "never save a real password to a file" instruction. Fixed by generating and fetching the
password through Secrets Manager instead (step 0), so it's never typed or saved anywhere. The
original also had **no rollback boundary** (separate ungrouped statements) and checked
`pg_roles.rolreplication = true` to verify the role — which is wrong: `GRANT rds_replication`
grants role *membership*, it does not set that column, so a correctly-configured role would have
still shown `rolreplication = false` and could have been misread as a failure. Both fixed:
everything in `02-setup.sh` runs as one transaction, and verification checks
`pg_has_role(..., 'member')` instead.

## Usage

```bash
./00-generate-role-secret.sh   # once, skip if the secret already exists
psql ... -f 01-inspect.sql     # read the output carefully before proceeding
PGHOST=<rds-endpoint> PGUSER=<admin-identity-confirmed-by-01-inspect> PGDATABASE=<db-name> ./02-setup.sh
PGHOST=<rds-endpoint> PGDATABASE=<db-name> ./03-verify-role-can-read.sh
```

## Separately: confirm the dispatch-time freshness-query credential (needed later, OPEN-275)

`PLAN-rds-local-postgres-replication.md` §3.4 item 3 calls for a *third*, separate credential —
not `ddp_local_replication` above — for LegBot's own pre-dispatch freshness check (OPEN-275):
whatever `resolve_rds_database_url()` already resolves at call time (the same mechanism
OPEN-268's Fargate work uses), reused here rather than a new role created for it. Before OPEN-275
needs it, confirm concretely (not assumed from OPEN-268's precedent alone) that credential
actually has `SELECT` on `ddp_bill_version_document`:

```sql
-- Run as whatever role resolve_rds_database_url() resolves:
SELECT has_table_privilege(current_user, 'ddp_bill_version_document', 'SELECT');
-- Expect true.
```

## After running

Report back (e.g. via `notes/ops-handoff`) with:
- `01-inspect.sql`'s findings (particularly: did `rds.logical_replication` already show `1`, or
  did it need a parameter-group change + reboot; which tables if any needed `REPLICA IDENTITY`
  remediation; whether the exact-7-tables and ownership/privilege checks passed).
- `02-setup.sh`'s verification output (publication contents, the `pg_has_role` membership check)
  and `03-verify-role-can-read.sh`'s output — paste the actual output, not just "looked right."
- Whether the freshness-query credential check above passed.

This closes OPEN-271's acceptance criteria (plan §4 AC1/AC3) once confirmed.
