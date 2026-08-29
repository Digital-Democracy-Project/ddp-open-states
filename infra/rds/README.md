# OPEN-191 (Phase 2) — the real ddp-openstates RDS instance

Documents `ddp-openstates`, created by hand via the AWS console on 2026-08-29 — **not** a
throwaway rehearsal copy. Ramon's standing decision: *"we won't throw it away. it becomes real
infrastructure."* This directory captures its actual configuration as Terraform, in the same
spirit as `infra/fargate-spike`: written after the fact to document a real resource, never
applied against it (this account's credential has no `rds:CreateDBInstance`/`iam:*` access at
all, by design).

## What's real and already working

- **Seeded** from the nightly `pg_dump -Fc` backup (`s3://ddp-openstates-backups/db/openstates_<ts>.dump`)
  via `pg_restore` — real production row counts confirmed (US 37,784 / MA 11,406 / FL 7,685 /
  VA 4,380 / MI 3,924 / WA 3,411 / AZ 2,190 / AL 1,507 / UT 1,021 bills).
- **Verified against a real cloud-collected run**: Florida's full `2026` session (1,897 bills /
  2,728 vote events, collected via OPEN-190's `cloud_collector.py` on a real Fargate task) was
  loaded on top via `cloud_loader.py` — `150 updated, 1,747 noop` bills, `157 new, 31 updated,
  2,540 noop` vote events, zero duplicates (row count unchanged before/after: 7,685 both times).
- **Reachable only through the existing WireGuard EC2 jump box** — not publicly accessible. That
  box's security group is an allowed source on this instance's own security group, and it also
  already hosts production `ddp-sync`/`ddp-api`, so those services get direct in-VPC access with
  no extra networking work once Phase 2's actual cutover happens.

## Two deliberate deviations from the plan this ticket originally wrote

1. **Not a throwaway instance** (see above) — this ticket's own text described rehearsing "into a
   throwaway RDS instance." Superseded by Ramon's explicit decision to build the real target now.
2. **A wrong-database mistake, caught and corrected.** An earlier attempt at this rehearsal used
   `pgdump-readonly.sh` (a different, `/usr/local/ddp-db-proxy/`-scoped wrapper) assuming its name
   meant it dumped the OpenStates production database. It doesn't — verified by checking
   `django_migrations` for app names (`common`, `django_celery_beat`, `slackbot`) that don't
   belong to `openstates-core` at all; it resolves to the dev `ddp-broker` database instead, and
   silently ignores any `-h`/`--host` override passed to it. No production data was lost (the
   dump was read-only against its own wrong source), but the `openstates` database on this
   instance had to be dropped and recreated once the mistake was found. See
   `Production_S3_Wrappers.md`'s new section on this, and use `ddp-prod-s3-openstates-backups` +
   `pg_restore` for the actual OpenStates database, not `pgdump-readonly.sh`.

## Operational gotcha worth knowing before touching this again

RDS's auto-generated Secrets Manager password can contain `:` and `[`, both of which break a
naive `postgresql://user:pass@host` connection string — Python's `urllib.parse.urlparse` fails
with `ValueError: Invalid IPv6 URL`. URL-encode the password
(`urllib.parse.quote(password, safe="")`) before building `DATABASE_URL`/`DATABASE_URL_OVERRIDE`.

## What this does NOT do

- Does not create the security group or DB subnet group it references — both pre-created out of
  band, same reasoning as `infra/fargate-spike`'s security group.
- Does not point `api-v3` or any request-time traffic at this instance. No read replica exists
  yet. The rollback policy decision (keep loading to both vs. a stated staleness window) is still
  open — see `PLAN-scraper-execution-migration.md`'s Phase 2 section.
- Does not decide the cutover date. This documents the rehearsal that Phase 2 named as a
  prerequisite before any cutover date is set — the rehearsal itself, not the migration.

## Variables that need real values

See `variables.tf`. `vpc_security_group_ids` and `db_subnet_group_name` come from what was
already created by hand in the console; they're not guessed here any more than
`fargate-spike/variables.tf`'s `security_group_id` was.
