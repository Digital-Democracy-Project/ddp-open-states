# REQUEST (not a GO): **OPEN-633, the Arizona canary: the load runs as a Fargate task with the stored RDS secret.** Four steps in order, each on Ramon's go. The source of truth for every setting, pass rule and rollback step is the body of ddp-open-states **#488**. 2026-11-24 ~23:00 UTC (Mac side, Onboard New States)

**Not a GO.** Ramon's decisions (2026-11-24, via the PM session; please confirm each with him in your session): the loader moves to Fargate; the canary uses the **stored secret**, not a password at launch ("the IAM permissions allow the database to read from secrets manager directly"); and the clean-week rule below. Nothing in this note changes production by itself.

## What I need from you, numbered
1. **A read-only check of the `ddp-scrapers-db` task definition** (your host's role was denied `ecs:DescribeTaskDefinition`, so this may be Ramon's to run; he has my command from `60c18a2`): list the **names** (never values) under `secrets` and `environment` of the live revision (`db:19` per the PM). Expected if the release is already there: secrets `RDS_USERNAME`, `RDS_PASSWORD`; environment `RDS_HOST`, `RDS_PORT`, `RDS_DBNAME`. `ddp-scrapers` (collection) must list **none** of them.
2. **If those entries are missing:** an image release with `TASK_RDS_SECRET_ARN` and `TASK_RDS_HOST/PORT/DBNAME` set (a Mac-side step by Ramon with `deploy-scrapers-image.sh`; the permission half is done). Tell me the new revision.
3. **ddp-sync #311 (merged, `6d56c641`): pull it and restart ddp-sync.** It sets only the scrape-block `rds_from_task_secret: true` (`config/sync_schedule.yaml` line ~494); the archive block's flag (~810) stays **false**. The file is bind-mounted and read once at start, so it takes a pull and a restart, **not a rebuild**. Gates: no run in its load phase, no `ddp-scrapers-db` task up, checked twice 3 s apart; never 02:15–04:45 UTC. By itself it changes nothing (no state loads on Fargate yet).
4. **ddp-open-states #488 (not yet merged; waits for step 1's result and Ramon's go): the manifest rollout** (`rollout-manifest.sh --host ec2`) of one line, `scrape.load_on_fargate: true` for `az`. **Last.** Preflight in #488's body: EC2 ddp-sync runs a build with `state_loads_on_fargate` (`eefb1ba` or later qualifies), and `ddp-scrapers-db`'s live image has `cloud_loader.py` (v70 or later; v89/v90 do).

## If step 4 lands without step 2
The load task refuses to run, with an error naming only the missing variables (never a value); nothing is imported. Rollback: `az` back to `false` in the manifest and roll out. A run already in flight keeps its Fargate choice from its record; only the next launch loads locally.

## Pass rules (Arizona's first scheduled run after step 4; all for that run's `run_id`; the full list is in #488)
1. One load task (`ddp-scrapers-db`, `RUNNER_SCRIPT=cloud_loader.py`) exits 0; note its ARN.
2. Per table (bills, actions, versions, documents, sponsorships, votes, person votes): bills after = before + the loader's "N new"; no table lower; the loader's new/updated/noop lines equal the collection's bill count; a replay of the same run says "0 new". **You record the "before" counts before step 4.**
3. The in-flight record held `load_task_arn` equal to the ECS ARN during the load, and is gone afterwards.
4. `prod/az/_import_lock` is absent or expired afterwards.
5. **No password anywhere:** none in ddp-sync logs, the load task's CloudWatch log or #automation-errors, **and none in the load task's ECS start record or CloudTrail RunTask event** (its overrides list no `DATABASE_URL`). The archive tasks still carry it: out of scope.
6. No second Arizona load ran at the same time.
7. The archive ran and the broker signal went, for the same `run_id`.

**Roll back and tell me** on any of: a non-zero exit or timeout; a table losing rows or bills not matching "new"; two Arizona load tasks; the lock held after ECS says STOPPED; the archive or broker signal not following; a password in a log, alert or the task's start record (tell Ramon the same day; rotating the password is his call); a missing-variable refusal (then step 2 is incomplete).

## The clean-week rule (Ramon accepted, 2026-11-24)
**Two consecutive scheduled Arizona runs** (Wed 12:00 UTC weekly, incremental) with no errors and results matching the local load, **plus one full (non-incremental) Arizona load** (the same trigger used on 11-23, on his go, compared with that run's counts). Only then do the other states move. **Do not flip any other state.**

## Not authorized
Any step before its go; `rds_from_task_secret: true` in the **archive** block; any state other than `az`; a ddp-sync rebuild (not needed); any change to the people refresh, the archive or the unmatched-voter check; deleting a lock, S3 object or Redis key; any certificate exception.

## What I check on the Mac side
Arizona's per-table counts on the replica after each run, and I post "verified" or a stop. I cannot read AWS, ECS records or CloudTrail from here; those pass lines are yours to report with the evidence.

Tickets: OPEN-633, OPEN-639, OPEN-878 (merged). Plan: ddp-infra #579 §8.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
