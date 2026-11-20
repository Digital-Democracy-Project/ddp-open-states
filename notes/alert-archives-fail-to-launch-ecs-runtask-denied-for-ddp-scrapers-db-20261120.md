# ALERT: since the ddp-sync rebuild (#301), every archive fails to LAUNCH: ddp-sync's AWS role may not `ecs:RunTask` the new `ddp-scrapers-db:1` (collection and load still work)

Written 03:13 UTC 11-20 (date -u at write time), from the production EC2 host. Read only so far; **nothing rolled back; I am asking the user which way to go.**

## What happened (ddp-sync log, all times UTC 11-20)
- **Collections work:** Washington 02:30:00 (`wa-75e7f462947d`, collection done 02:35:34, load done 02:35:38, 337.7 s); USA lower 03:00:00 (`usa-54fbfcba79aa`, 342.5 s) and upper 03:05:43 (`usa-2fbd40fb5d23`, 227.9 s). ECS: three stopped tasks on **ddp-scrapers:74** (v71), each exit **0** ("Essential container in task exited"). (So the nightlies are short, 5 to 9 minutes: the schedule comment's "WA ~5 h, USA ~6 h" is out of date.)
- **Every archive fails to launch:** at 02:35:38 (wa), 03:05:39 and 03:09:32 (usa):
  `openstates_archive: fargate launch failed detail='An error occurred (AccessDeniedException) when calling the RunTask operation: User: arn:aws:sts::350941939790:assumed-role/EC2ServiceAccessReadOnlyRole/i-033cd315ff240f2e5 is not authorized to perform: ecs:RunTask on resource: arn:aws:ecs:us-east-1:350941939790:task-definition/ddp-scrapers-db:1 because no identity-based policy allows the ecs:RunTask action'`
  followed by `archive_attempt_failed ... run_task_failed` and `operator_alert_sent_via_cams http_status=202 source=openstates_archive.archive_failure` (so the operators have been alerted). Pennsylvania (04:00 UTC) and Alabama and Georgia (12:00 UTC) will fail the same way.
- **Cause:** the instance role that ddp-sync's boto3 uses can run the `ddp-scrapers` family (collections and the old archive launches worked) but **no policy of that role names `task-definition/ddp-scrapers-db:*`**. #301 (my rebuild at 01:34 to 01:37 UTC, checkpoint ba66dd5a9) makes load and archive launch from `task_definition_db` = `ddp-scrapers-db`. Your step-2 check ("the next archive run's ECS task is from ddp-scrapers-db:1, reaches RUNNING with the new execution role") therefore **fails at RunTask, before the task exists.** The loads themselves are fine (they run in ddp-sync's own container, `rds_from_task_secret: false`).
- **Probably also needed (I cannot read IAM to confirm):** `iam:PassRole` for the role the launch passes, the new execution role `ddp-scraper-db-execution-role` (and the task role), with `iam:PassedToService = ecs-tasks.amazonaws.com`; RunTask checks both.

## What is not affected / what is
Not affected: collections, the RDS loads (`cloud_scrape: done`), the scorecard chain, the broker. **Affected:** the archive step after each scrape, therefore bill-version archiving and the LegBot hand-off that follows it, for every state from now on until this is fixed (the next archive that succeeds should pick up what is missing; I have not verified that the archive catches up).

## Options (the user decides; a person with AWS write access is needed for the first)
1. **Grant it** (clean): on EC2ServiceAccessReadOnlyRole add `ecs:RunTask` on `arn:aws:ecs:us-east-1:350941939790:task-definition/ddp-scrapers-db:*` (the policy that already covers `ddp-scrapers:*`) and `iam:PassRole` on the new execution role and the task role. Then the next archive just works; no change here.
2. **Roll ddp-sync back** to `ddp-sync:pre-open639` (80daf0635635: code d28bda2, core c983ae68; archives launch from `ddp-scrapers` again), `up -d --no-deps ddp-sync`: about 2 minutes and it reopens a drift (ddp-sync c983ae68, api-v3 and image 10f32ce0) that I would report. The SYNC-181 rebuild then waits too.
3. **A one-off fix in sync_schedule.yaml** (point `task_definition_db` back at `ddp-scrapers`) is **not** mine to change.

I will not roll back on my own (the user's standing rule: report first, then wait). I read this branch every 20 minutes.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
