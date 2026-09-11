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

1. **`01-inspect.sql`** — read-only. Confirms `wal_level`, `rds.logical_replication`, replication
   slot/sender/worker capacity headroom, and `REPLICA IDENTITY` status for the 7 tables this plan
   replicates. If `rds.logical_replication` needs enabling, that's a parameter-group change and
   an RDS **reboot** — needs a maintenance window and **Ramon's explicit sign-off**, separately
   from the plan's own approval. Do not schedule that reboot without it.
2. **`02-setup.sql`** — makes real changes. Remediates any `REPLICA IDENTITY` gap
   `01-inspect.sql` found, creates the dedicated `ddp_local_replication` role (never reused from
   an existing app/admin/Django account, never handed to a consumer), and creates the
   table-scoped `ddp_legbot_publication` naming exactly the real 7 tables — not `FOR ALL TABLES`.

## Before running 02-setup.sql

- Generate the role's password with a real secret generator (`openssl rand -base64 32` or
  equivalent) — never type a real password into a file that gets saved, never commit one.
- Store it through this project's existing credential convention (Secrets Manager / `.env`,
  matching how other production credentials are already handled) — not inline in this repo.
- Fill in `<database_name>` with the real RDS database name.

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
  remediation).
- The verification queries at the bottom of `02-setup.sql` (publication contents, role's
  `rolreplication` flag) — paste the actual output, not just "looked right."
- Whether the freshness-query credential check above passed.

This closes OPEN-271's acceptance criteria (plan §4 AC1/AC3) once confirmed.
