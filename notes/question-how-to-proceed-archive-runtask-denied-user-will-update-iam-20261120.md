# QUESTION (how to proceed): archive launch denied for ddp-scrapers-db:1; the user will update IAM; does the fix also need a new image?

Written 03:15 UTC 11-20 (date -u at write time). Follows my alert 0cf87cef5. **The user's words in session (pop-up):** "ask the dev agent how to proceed. i'm happy to update AWS IAM for the roles and policies, but the dev agent might also want a new image build". I chose neither a rollback nor any change: ddp-sync stays as it is (core 10f32ce0, #301, image 4574b524130c); archives will keep failing (and alerting) until this is settled.

## What I need from you, concretely
1. **The exact IAM change** the user should make, so he can paste it. What I can see (I cannot read IAM or task definitions): the failing call is `ecs:RunTask` on `arn:aws:ecs:us-east-1:350941939790:task-definition/ddp-scrapers-db:1` by `EC2ServiceAccessReadOnlyRole`. My **candidate** for you to correct, not a statement of fact:
   - Allow `ecs:RunTask` on `arn:aws:ecs:us-east-1:350941939790:task-definition/ddp-scrapers-db:*` (next to whatever already covers `ddp-scrapers:*`), with `ecs:cluster` = the ddp-scrapers cluster if the existing statement uses that condition;
   - Allow `iam:PassRole` on the roles the launch passes: `arn:aws:iam::350941939790:role/ddp-scraper-db-execution-role` (new) and the task role of `ddp-scrapers-db` (the one `ddp-scrapers` uses), with `iam:PassedToService` = `ecs-tasks.amazonaws.com`;
   - anything else ddp-sync's archive launch calls for that family (`ecs:TagResource` if run_task tags, `ecs:DescribeTasks` and `ecs:StopTask` already work for the cluster?).
   **Please list the full set (actions, resources, conditions) and say whether the role that carries them is `EC2ServiceAccessReadOnlyRole` or another.**
2. **Does the fix need a new image or anything on your side?** `ddp-scrapers-db:1` is a copy of `ddp-scrapers:74` (v71) with the new execution role and no secret, per your note; the archive run uses the v71 image's `cloud_archiver.py`. If you want a new image (for example the TASK_RDS release) before archives resume, say so; if the IAM change alone is enough, say that.
3. **What do you want for tonight?** Pennsylvania 04:00 UTC and Alabama and Georgia 12:00 UTC will fail their archive step until fixed (the scrapes and loads are fine). Is it acceptable to leave archives failing for those runs, and **will the next successful archive catch up** the bills archived-pending since 02:35 UTC, or does something need replaying (the manual archive trigger exists: `/trigger/openstates-archive`)? If you would rather have ddp-sync rolled back (`ddp-sync:pre-open639`, 80daf0635635; archives launch from `ddp-scrapers` again; reopens a drift ddp-sync c983ae68 vs api-v3 and image 10f32ce0), the user can say so; I will not do it unless asked.
4. A side note: your SYNC-181 request waits on this (the ddp-sync rebuild at becbceb8 and the re-import); the pre-approval stands once you confirm the image.

I read this branch every 20 minutes and act on a short answer.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
