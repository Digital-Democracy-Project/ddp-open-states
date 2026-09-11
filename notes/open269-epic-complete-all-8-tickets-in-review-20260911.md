# OPEN-269 epic complete -- all 8 child tickets in review, PRs open

All 8 OPEN-269 child tickets (OPEN-270 through OPEN-277) now have a PR each, each pushed through
at least one round of `/pm-review` with real findings applied, and each set to Jira "In Review".
Nothing further needed from you on the epic build-out itself right now -- flagging in case you
want the PR list for your own awareness, and because one finding affects real RDS execution
sequencing.

## PR list

- OPEN-270 (network check): ddp-open-states #237, **merged**.
- OPEN-271 (RDS roles/publication/inspection SQL): #238 **merged**; follow-up #240 (pipefail bug
  fix) still open.
- OPEN-272 (rebuild local replica): #239, **merged**.
- OPEN-273 (subscription + readonly role): #241, open.
- OPEN-274 (health check + rebuild/recovery drill): #242, open.
- OPEN-275 (LegBot pre-dispatch freshness check): ddp-sync #136, open.
- OPEN-276 (RDS-replica jurisdiction allowlist): ddp-sync #137, open (branched on #136).
- OPEN-277 (schema-comparison script + migration procedure docs): #243, open.

## One finding relevant to your side: a real bug in the plan's own migration-ordering guidance

While building OPEN-277 I actually reproduced `PLAN-rds-local-postgres-replication.md` §7.9's own
documented additive-migration order ("RDS first, then local") on a Docker logical-replication
loopback, not just read it -- and it's wrong. Applying an additive column to RDS before the local
replica crashes the subscriber's apply worker in a loop (`ERROR: logical replication target
relation ... is missing replicated column`) until the local side catches up. Filed a correction:
ddp-infra PR #149 (plan v0.6) -- the plan is still DRAFT/unapproved, so this is caught before
approval, not after. If any future Django migration against these 7 tables gets applied to RDS
directly, the corrected order (local first, then RDS) is what to actually follow, not the original
text.

## Still the same hard blocker as before

RDS's `wal_level` is still `replica`, not `logical` (your own `01-inspect.sql` results), needing a
parameter-group change + reboot pending Ramon's sign-off. Every RDS-touching script/check across
all 8 tickets is built and tested via Docker loopback but not yet exercised against real RDS for
that reason -- nothing new to execute from your side beyond what's already in flight (the
parameter-group sign-off, and whatever's left of the US backfill dry-run/spot-check thread).
