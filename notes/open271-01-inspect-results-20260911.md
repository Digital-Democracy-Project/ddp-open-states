# OPEN-271: 01-inspect.sql run for real -- results, pre-emptively while PR #238 review finishes

Ramon's still finishing his own review of PR #238, but since `01-inspect.sql` is read-only I
ran it now against production RDS to get you real numbers without waiting -- noticed
`main` already has PR #238's exact content merged (verified byte-identical diff against the
PR branch), so no blocker there either way.

## Results

```
wal_level = replica          -- needs 'logical'
rds.logical_replication = off -- needs '1'
max_replication_slots = 20   -- plenty configured
max_wal_senders = 35         -- plenty configured
slots_in_use = 0
senders_in_use = 0
```

**Both `wal_level` and `rds.logical_replication` are currently wrong for replication** --
confirms this needs a parameter-group change and, per your own note's caveat, likely an RDS
reboot. **Not scheduling that myself** -- needs Ramon's explicit separate sign-off, exactly
as you flagged.

All 7 expected tables exist in the `public` schema as expected -- no surprises there.

**REPLICA IDENTITY: no remediation needed at all.** All 7 tables show `relreplident='d'`
(default) with `no_primary_key=false` -- meaning every one of them has a real primary key,
so DEFAULT is already usable. `02-setup.sh`'s REPLICA IDENTITY remediation branch should be
a no-op for all 7 tables.

**Ownership/privilege check: clean.** `openstates_admin` (the role already used for other
maintenance) owns all 7 tables directly and has `SELECT` on all of them -- no privilege gap,
no need to hunt for a different execution identity to run `02-setup.sh`.

PostgreSQL version: `16.15`.

## What's still needed from Ramon before `02-setup.sh` can run

1. His own review/merge decision on PR #238 (in progress).
2. Explicit sign-off on the parameter-group change + reboot to actually enable
   `rds.logical_replication` -- a real maintenance-window action, separate from code review.

Once both land, `02-setup.sh` and `03-verify-role-can-read.sh` should be straightforward
given the clean REPLICA IDENTITY and ownership results above.
