# Confirmed: AWS-managed automatic rotation, every 7 days -- this is a recurring problem, not a one-off

*Replies to `notes/rotation-window-precisely-bounded-not-friday-20260909.md`.* Ramon checked the
Secrets Manager console directly. Confirmed exactly:

- **Rotation status: Enabled**
- **Rotation schedule: every 7 days**
- **Last rotated: Wed, September 9, 2026 at 12:15:27 UTC** -- squarely inside the
  03:35-13:37 UTC window the log-timeline analysis narrowed this down to.
- **Next rotation: on or before September 16, 2026.**

Nobody manually rotated anything. This is RDS's own "manage master credentials in Secrets
Manager" feature running its normal automatic schedule -- confirmed, not inferred.

## Why this matters beyond today

This isn't a one-time fix. `ddp-sync`'s `.env` (and this host's `deploy/.env`, and anything else
that holds a *rendered, static copy* of `RDS_DATABASE_URL` rather than reading Secrets Manager
live) will go stale again in another 7 days, and every 7 days after that, forever, until
something re-renders it on the same cadence. Today's whole investigation -- SG ingress, SG
egress, three failed validation runs, the timeline reconstruction -- would otherwise just repeat
identically next Wednesday.

## What actually needs to happen

1. **Immediate:** re-render `ddp-sync`'s `.env` with the current secret value (same mechanism as
   `deploy/rotate-database-url.sh`, just pointed at `ddp-sync`'s `.env`/`RDS_DATABASE_URL` key
   instead of `deploy/.env`/`DATABASE_URL`), then restart the `ddp-sync` container so its
   in-memory env picks up the fresh value (a `.env` edit alone does nothing for an already-running
   container -- confirmed today that its env is baked in at container start, not re-read live).
2. **Permanent:** something needs to run this re-render automatically on a matching cadence (a
   cron job invoking a `ddp-sync`-targeted version of `rotate-database-url.sh`, or -- better --
   have `_run_load()`/`_launch_archive_fargate_task()` resolve `RDS_DATABASE_URL` from Secrets
   Manager directly at call time instead of from a pre-rendered env var, which sidesteps the
   staleness question entirely at the cost of a `secretsmanager:GetSecretValue` call per
   invocation). Worth deciding which approach fits this codebase's existing patterns before
   picking one.
3. Once step 1 is done, I'll re-verify with the same direct-connection test before re-running the
   Fargate archive validation a fourth time -- and tonight's ~01:00-03:00 UTC scheduled cycle
   needs the same fix in place before then, or it fails the identical way.
