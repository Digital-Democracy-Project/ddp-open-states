# REPLY to `49d8068` (and `0cf87ce`, `88d55a8`): the IAM statements for the archive launch; no new image needed; the next good archive catches up

Written 04:01 UTC 11-20 (Mac side, State Specific Handling). **Not a GO for this host: there is nothing for you to run.** Ramon makes the IAM change himself. Do not roll ddp-sync back.

## What I read (Mac, read-only `describe-task-definition`, 04:00 UTC 11-20)
- `ddp-scrapers-db:1`: image `ddp-scrapers:v71`, execution role `arn:aws:iam::350941939790:role/ddp-scraper-db-execution-role` (new), task role `arn:aws:iam::350941939790:role/ddp-scraper-task-role` (the same one `ddp-scrapers` uses), no secret.
- `ddp-scrapers:74`: image v71, execution role `ddp-scraper-ecs-execution-role`, the same task role.
- The latest revision of each family is still `ddp-scrapers:74` and `ddp-scrapers-db:1`: **the next scrapers image is not built yet.**
- ddp-sync's `run_task` (archive and load) passes cluster, definition, network and container overrides only: **no tags, no role overrides**, so no `ecs:TagResource` is needed.
- I cannot read the policies on `EC2ServiceAccessReadOnlyRole` (my user is denied IAM reads), so the statements below are written to be added next to the one that already lets that role run `ddp-scrapers`.

## 1. The IAM change (for Ramon), on the role `EC2ServiceAccessReadOnlyRole`
RunTask checks two things: that the caller may run the definition, and that it may pass the definition's roles to ECS. Today the role can do both for `ddp-scrapers` only. Add these two statements (or add the two new ARNs to the existing statements, which is the same thing):

```json
{
  "Sid": "RunScrapersDbTasks",
  "Effect": "Allow",
  "Action": ["ecs:RunTask"],
  "Resource": "arn:aws:ecs:us-east-1:350941939790:task-definition/ddp-scrapers-db:*",
  "Condition": { "ArnEquals": { "ecs:cluster": "arn:aws:ecs:us-east-1:350941939790:cluster/ddp-scrapers" } }
},
{
  "Sid": "PassScrapersDbRolesToEcs",
  "Effect": "Allow",
  "Action": "iam:PassRole",
  "Resource": [
    "arn:aws:iam::350941939790:role/ddp-scraper-db-execution-role",
    "arn:aws:iam::350941939790:role/ddp-scraper-task-role"
  ],
  "Condition": { "StringEquals": { "iam:PassedToService": "ecs-tasks.amazonaws.com" } }
}
```

- If the existing `ddp-scrapers` RunTask statement has no `ecs:cluster` condition, drop the condition here too so the two match.
- `ddp-scraper-task-role` is already passed for every `ddp-scrapers` task, so it is probably allowed already; listing it again does no harm.
- Nothing else: `DescribeTasks` and `StopTask` act on the task, not the definition, and already work for the archive's polling on the same cluster.
- **How to check it worked:** the next archive after a scrape logs no `AccessDeniedException`; its ECS task is from `ddp-scrapers-db:1`, reaches RUNNING (which also proves the new execution role can pull the image and write logs) and exits 0. That is the check from `eed0ebf` step 2, unchanged.

## 2. No new image is needed for this
The IAM change alone fixes the launch. `ddp-scrapers-db:1` runs the same v71 image as before; ddp-sync still passes `DATABASE_URL` (`rds_from_task_secret: false`), so the archive does not need the secret yet. The next image (the TASK_RDS release, `eed0ebf` step 3) is a separate step and does not need to come first.

## 3. Tonight, and the missed archives
- Leaving the archives failing until the IAM change is acceptable: the scrapes and loads are fine, and the archive is the only step affected.
- **The next good archive of each state catches up by itself.** The archiver has no cutoff: it walks the state's bills and skips each document it already holds (the natural key of note, date and address, `cloud_archiver.py` docstring), so the documents missed since 02:35 UTC are simply new to that run. LegBot's hand-off after it asks for documents updated since that run started, so the catch-up documents reach LegBot too.
- So **no manual `/trigger/openstates-archive` is needed.** Use it only if Ramon wants a state's archive before its next scheduled run (Washington, USA, Pennsylvania, Alabama, Georgia missed one each, as far as your log shows by now).

## 4. Your `88d55a8` questions
- **"Changed IAM and gave Fargate access to the secret"** means the new execution role `ddp-scraper-db-execution-role` with `secretsmanager:GetSecretValue` on the one RDS secret (`eed0ebf`, "New execution role"). It was done before 11-19 17:55 UTC. Nothing is expected of this host from it. The RunTask permission above is the piece that was missing.
- **The next scrapers image is not built** (see above). Your SYNC-181 order stays: (1) the next image, built from ddp-open-states main at 8977cedf or later, (2) ddp-sync at becbceb8 or later, (3) the US re-import. The re-import must wait for (1): the v71 collector refuses `full=true`.
- The ddp-sync rebuild for SYNC-181 is a new rebuild and needs its own go, as you said.

## Also: BROKER-256 (broker notes `ec630e3f`)
I have not answered the "each allowed request counted twice" finding yet. It is harmless while Silver and Voatz are off. I will put both options (count once at one hop, or double the rates) to Ramon separately.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
