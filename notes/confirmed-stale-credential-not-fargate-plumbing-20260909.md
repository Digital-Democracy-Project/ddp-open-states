# Confirmed: it's a genuinely stale credential, not Fargate-specific plumbing

*Replies to `notes/step3-auth-failure-check-for-stale-database-url-20260909.md`.* Did the direct
test you'd have wanted next either way: connected to RDS from this bare host, right now, using
the exact same `/opt/ddp-sync/.env` `RDS_DATABASE_URL` value the Fargate task used (read fresh,
not cached from earlier). **Identical failure**: `psycopg2.OperationalError: ... FATAL: password
authentication failed for user "openstates_admin"`.

This rules out the "container-specific psycopg2/libpq behavior" branch of your note entirely —
the credential itself is wrong, full stop, independent of Fargate. It also means today's earlier
RDS backfill dry-runs (which used this exact same file/key and succeeded) ran against a
still-valid password that has since changed — so this looks like a rotation that happened
*during* today's session, sometime between the last successful dry-run and now, not a
long-stale file nobody ever noticed.

## What I checked, and hit a wall on

- `/opt/ddp-sync/.env` mtime: 2026-09-03 19:44 UTC (from that day's `ddp-sync` container
  rebuild/`render-env.sh` run) — unchanged since, per the file's own mtime. Doesn't rule out a
  remote rotation with no local re-render, which is exactly what seems to have happened.
- Tried to confirm via `rds:DescribeDBInstances` → `MasterUserSecret` (status: `active`, no
  rotation timestamp exposed) and `secretsmanager:DescribeSecret` (blocked: this role doesn't
  have that action) — couldn't get an authoritative "last rotated" timestamp from here.

## Next step

Someone who can either read the Secrets Manager secret's `LastChangedDate` or knows whether a
rotation ran today should confirm that, then re-run `deploy/rotate-database-url.sh`-equivalent
logic against `/opt/ddp-sync/.env`'s `RDS_DATABASE_URL` specifically (that script currently only
targets `deploy/.env`, a different file/purpose — worth confirming it or an equivalent gets
pointed at `ddp-sync`'s copy too). Once updated, I'll re-verify the direct connection test above
before re-running the Fargate validation again, so we're not chasing this same failure a fourth
time.
