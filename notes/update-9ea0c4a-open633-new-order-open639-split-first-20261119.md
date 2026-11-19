# UPDATE to `9ea0c4a` (OPEN-633 release): new order, the task-definition split (OPEN-639) comes before the secret. 2026-11-19 (Mac side, State Specific Handling)

**Not a GO.** This replaces the order of `9ea0c4a`'s Parts A and B. Its Part C is done (checkpoint `745a8d1`). Ramon's decision (2026-11-19): v70 is built **without** the secret (done: tag v70, revision 73, image only). Next comes the split, then the secret, and it goes on the load/archive definition only.

## Why
ECS hands a task definition's secrets to **every** task started from it. The RDS secret is the database **owner's** login (reply `8c4315c`). With one `ddp-scrapers` definition, the collection and probe tasks would get it too, and those tasks parse outside websites. OPEN-639 splits the definition:
* `ddp-scrapers`: collection and probe tasks, **never** the login;
* `ddp-scrapers-db`: load and archive tasks, the only one that may carry it.

## The new order (each step on its own go, each with its check)
1. **Merge OPEN-639:** ddp-open-states #430 (the deploy script) and ddp-sync #301 (load and archive launch from `task_definition_db`). Merging changes nothing live.
2. **Image release with #430's script (Ramon, on the Mac), without `TASK_RDS_*`.**
   * It registers the image on `ddp-scrapers` and creates `ddp-scrapers-db` from it.
   * **Check:** `aws ecs describe-task-definition --task-definition ddp-scrapers-db` exists, has the same image, and shows no secrets. The script prints `RDS secret in ddp-scrapers: no` and `RDS secret in ddp-scrapers-db: no`.
3. **ddp-sync at #301's merge on EC2 (prod agent), only after step 2's check.** Use the same build-and-recreate procedure as Part C, `DDP_CORE_SHA` unchanged unless the image's core changed.
   * Before step 2, every archive would fail at launch, with an alert.
   * **Check:** the next archive run's `run_task` names `ddp-scrapers-db`, and the next scrape's collection names `ddp-scrapers`.
4. **Part A, the IAM grant (Ramon, in the console):** `secretsmanager:GetSecretValue` on the one RDS secret, for the execution role.
   * The prod agent could not confirm the role's name (`8c4315c`).
   * Check in KMS whether key `444425bb-…` is AWS-managed. If it is customer-managed, also grant `kms:Decrypt` on it.
   * **Option (Ramon's call):** a separate execution role for `ddp-scrapers-db`, so that only its role can read the secret. That needs a new role, and the deploy script would then set it on that family; not built.
5. **Image release with `TASK_RDS_SECRET_ARN` and `TASK_RDS_HOST/PORT/DBNAME` (Ramon):** the secret goes on `ddp-scrapers-db` only. The script refuses if `ddp-scrapers` carries any `RDS_*` or `DATABASE_URL` entry.
   * **Check:** the script prints `RDS secret in ddp-scrapers: no` and `RDS secret in ddp-scrapers-db: yes`.
   * **Check:** the next archive task (from `ddp-scrapers-db`) reaches RUNNING, which proves ECS could read the secret. The next collection task's settings have no `RDS_*`.
   * **Rollback:** deregister the new `ddp-scrapers-db` revision.
6. **Later, each its own note:**
   * `rds_from_task_secret: true` in ddp-sync;
   * then, after the Mac rehearsal (plan step 3, starting now on v70), the first state's `scrape.load_on_fargate: true`.

## Superseded
`9ea0c4a` Part A as written (grant before the split) and Part B as written (the secret on `ddp-scrapers`) are replaced by steps 4 and 5 above. Do not put the secret on `ddp-scrapers`.

Plan: ddp-infra `PLAN-cloud-load-on-fargate.md` (#538). Tickets: OPEN-633, OPEN-639.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
