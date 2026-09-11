# New goal: build out the OPEN-269 epic (LegBot RDS→Mac logical replication)

Ramon set a new goal: complete the [OPEN-269](https://digitaldemocracyproject.atlassian.net/browse/OPEN-269)
epic (8 tickets, OPEN-270 through OPEN-277, building the now-APPROVED
`PLAN-rds-local-postgres-replication.md`). One PR per ticket, each through at least one
`/pm-review` round, ticket set to In Review once done.

**Real constraint found early**: this Mac-side dev session has confirmed it has NO RDS or
Secrets Manager access (`aws rds describe-db-instances` / `aws secretsmanager list-secrets`
both return `AccessDenied` for the `ddp-scraper` IAM identity available here). So for any
RDS-side ticket, I write and pm-review the scripts here, but **you (or whoever has RDS admin
access) need to actually execute them** -- confirmed with Ramon this is the right split.

## Status so far

- **OPEN-270** (confirm network path): Done, already merged
  ([ddp-open-states #237](https://github.com/Digital-Democracy-Project/ddp-open-states/pull/237)).
  Turns out the Mac Studio already has a working WireGuard path to RDS -- confirmed with a real
  connection test (private-IP resolution, route over the tunnel interface, TCP connect, and a
  full Postgres-protocol-level probe). Nothing needed from you on this one.

- **OPEN-271** (RDS-side setup: replication role + table-scoped publication): PR open, not yet
  merged -- [ddp-open-states #238](https://github.com/Digital-Democracy-Project/ddp-open-states/pull/238).
  **This is the one that needs you.**

## What OPEN-271 needs from you

1. **Review and merge PR #238** if it holds up (it's mine, so per standing practice I'm not
   merging it myself -- this is exactly the independent-review case).
2. Once merged, pull `main` and run, in order, from `ops/postgres-replica/rds/`:
   - `00-generate-role-secret.sh` (once -- creates a Secrets Manager secret with a generated
     password for the new `ddp_local_replication` role; skip if it already exists).
   - `01-inspect.sql` (read-only -- checks `wal_level`, `rds.logical_replication`, replication
     slot/sender capacity, that all 7 real tables exist as expected, `REPLICA IDENTITY` status
     for each, and that your admin identity actually has authority over all 7 tables). **If
     `rds.logical_replication` isn't already `1`, that needs a parameter-group change + a real
     RDS reboot -- don't schedule that without Ramon's explicit sign-off first, separate from
     his plan approval.**
   - `02-setup.sh` (makes real changes -- fetches the secret from step 1, remediates any
     `REPLICA IDENTITY` gap, creates the role and the table-scoped publication, all in one
     transaction).
   - `03-verify-role-can-read.sh` (confirms the new role can actually connect, read all 7
     tables, and genuinely cannot write).
3. **Report back here** with: `01-inspect.sql`'s findings (especially whether the
   parameter-group/reboot question came up), and the verification output from `02-setup.sh` /
   `03-verify-role-can-read.sh` -- paste actual output, not just "looked fine."
4. Separately, confirm whatever `resolve_rds_database_url()` resolves at call time actually has
   `SELECT` on `ddp_bill_version_document` (README has the exact query) -- needed later for
   OPEN-275, worth checking now while you're in there.

The full runbook and reasoning is in `ops/postgres-replica/rds/README.md` in that PR -- read it,
don't just run the scripts blind, there are a couple of real gotchas documented there (a
`GRANT rds_replication` role-verification pitfall in particular).

I'll keep working through the remaining Mac-side tickets (272 onward, where I can) while this is
in your hands. Ping back here once you've run it, or if anything doesn't match what the scripts
expect.
