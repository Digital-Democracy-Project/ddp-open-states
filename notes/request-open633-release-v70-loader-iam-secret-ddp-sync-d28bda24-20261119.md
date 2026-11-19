# REQUEST (OPEN-633 release): image v70 with the loader, the RDS secret (IAM, then task definition), ddp-sync at d28bda24. 2026-11-19 (Mac side, State Specific Handling)

**Not a GO.** Each part waits for Ramon's go and posts its own checkpoint.

**This note replaces request `53dd191`.** Its Parts 1 and 2 are folded in below as Parts A and B, unchanged in substance.

**Every switch stays off throughout:**
* no state gets `scrape.load_on_fargate: true`;
* ddp-sync's `rds_from_task_secret` stays `false`.

After this release, production behaves exactly as today. The only differences:
* the image can run the loader;
* the task definition carries the login, unused while ddp-sync still passes `DATABASE_URL`.

## What is merged
| Repo | Merge | What |
|---|---|---|
| ddp-open-states | `5c11b40b` (#428) | `cloud_loader.py` in the image. The runners build `DATABASE_URL` from the task secret **only when none is passed**. Manifest field `scrape.load_on_fargate` (false for all 17). `deploy-scrapers-image.sh` can add the secret. |
| ddp-sync | `d28bda24` (#299) | The Fargate load branch (only for a state whose manifest says true). `cloud_path.fargate.rds_from_task_secret: false` in both the scrape and archive blocks. Connection strings cut from failure messages. |

* **The image changes by #428 only.** Checked:
  * the files the image copies changed on ddp-open-states main only in #428 since v69 was built (11-19 ~04:30 UTC);
  * openstates-core main is still `c983ae68599e94494a94edc23d576b483922302e`;
  * openstates-scrapers main is still `65815f3df68a1e1d635e0cc8072b9d2319909847`.
* **So v70 keeps core `c983ae68`.** api-v3 (both hosts) and ddp-sync need **no core rebuild**, and the SYNC-180 drift check should stay at exit 0.

## Part A. IAM (production; first; on Ramon's go)
**Why first:** ECS fetches every secret in a task definition **before the container starts**. If the execution role cannot read it, **every** ddp-scrapers task fails to start (collection, archive, probe).

1. **The secret:** the one ddp-sync already reads, the value of `RDS_CREDENTIALS_SECRET_ARN` in ddp-sync's environment on EC2. Never print its contents.
2. **The role:** `aws ecs describe-task-definition --task-definition ddp-scrapers --query taskDefinition.executionRoleArn`.
3. **The grant:** `secretsmanager:GetSecretValue` on that one secret ARN only (an inline policy).
   * If `aws secretsmanager describe-secret --secret-id <arn> --query KmsKeyId` names a customer-managed key, also `kms:Decrypt` on that key.
   * An empty answer means the default key, and no KMS grant is needed.
4. **Verify:** `aws iam simulate-principal-policy --policy-source-arn <role arn> --action-names secretsmanager:GetSecretValue --resource-arns <secret arn>` returns `allowed`.

**Checkpoint wanted:**
* the role name;
* that the grant names that one secret;
* the KMS answer and the simulate result;
* **the secret ARN and ddp-sync's `RDS_HOST`, `RDS_PORT`, `RDS_DBNAME`** (identifiers, not credentials), which Ramon needs for Part B.

## Part B. Image v70 + the task definition (Ramon on the Mac; after Part A's checkpoint)
1. Run the usual release, with Part A's four values:
   ```
   TASK_RDS_SECRET_ARN=<arn> TASK_RDS_HOST=<host> TASK_RDS_PORT=<port> TASK_RDS_DBNAME=<db> bash deploy-scrapers-image.sh
   ```
   * It builds from main, so the next tag (v70 expected) at ddp-open-states `5c11b40b` or later.
   * Its usual image checks run, and it should print `openstates-core c983ae68599e...`.
   * It prints `RDS secret entries set` and `RDS secret in task definition: yes`.
   * Later images copy the entries forward without the variables.
2. **If Part A is not done yet:** run the release **without** the four variables. The image still carries the loader. The secret then goes in at a later image, after Part A.
3. **Checks:**
   * `docker run --rm --entrypoint ls <image> /app/cloud_loader.py` lists the file;
   * `describe-task-definition` shows the secret **names** `RDS_USERNAME`, `RDS_PASSWORD` and the environment **names** `RDS_HOST`, `RDS_PORT`, `RDS_DBNAME` (not their values);
   * the **next ddp-scrapers task of any kind** reaches RUNNING and stops with its usual exit code. This proves ECS could read the secret.
4. **If that task fails to start with a secrets error:**
   * `aws ecs deregister-task-definition --task-definition ddp-scrapers:<new rev>` (the family falls back to revision 72, v69, which has no secret);
   * report it. The script prints this rollback line too.

**Checkpoint wanted:**
* the tag, the digest, the revision and the core line;
* the three checks above.

## Part C. EC2: ddp-open-states and ddp-sync (prod agent; on Ramon's go; can follow Part B in either order)
**Only when nothing is running:** 0 ECS tasks, and no `os-update`, `cloud_loader`, `os-text-extract` or `os-people` process in `ddp-sync-ddp-sync-1`. That is the same gate as the SYNC-180 rebuild (checkpoint of 16:08 UTC 11-19).

1. **ddp-open-states:**
   * run `bash deploy/rollout-manifest.sh --host ec2 --ddp-sync-root /opt/ddp-sync`;
   * it fast-forwards `/opt/ddp-open-states` to `5c11b40b` or later, validates, drift-checks and refreshes api-v3's copy;
   * it should report 17 valid states;
   * `grep -c 'load_on_fargate: true' /opt/ddp-open-states/jurisdictions.yaml` gives 0;
   * the local loader's behaviour does not change: ddp-sync passes `DATABASE_URL` and no `RDS_USERNAME` exists in its container, so the new step returns at once.
2. **ddp-sync:**
   * `/opt/ddp-sync` fast-forward to **`d28bda24`**;
   * rebuild with the **unchanged** core, exactly as the SYNC-180 checkpoint did it:
     ```
     DDP_CORE_SHA=c983ae68599e94494a94edc23d576b483922302e docker compose -p ddp-sync -f infrastructure/docker-compose.prod.yml build ddp-sync
     docker compose -p ddp-sync -f infrastructure/docker-compose.prod.yml up -d --no-deps ddp-sync
     ```
     The GitHub token goes into the build's environment only, as before.
   * **Do not use `systemctl restart ddp-sync`.** That checkpoint's finding 1: the unit's `up -d --build` stops without `DDP_CORE_SHA`.
   * Tag the running image `ddp-sync:pre-open633` first, for rollback.
3. **Checks:**
   * the container is healthy, with "Scheduler started with 22 jobs" and no tracebacks;
   * `rds_from_task_secret: false` appears twice in the running config (`grep -c 'rds_from_task_secret: false' /opt/ddp-sync/config/sync_schedule.yaml` = 2);
   * `check-core-pin-drift.py --image-core c983ae68599e94494a94edc23d576b483922302e --container ddp-openstates-api-1 --sync-container ddp-sync-ddp-sync-1` exits 0;
   * the **next scheduled scrape** (any state) still loads locally: the log shows `cloud_scrape: collection done, loading into RDS` and **no** `cloud_scrape: load task started`.
4. **Rollback:** retag `ddp-sync:pre-open633` as `ddp-sync:prod`, then `up -d --no-deps ddp-sync`.

**Checkpoint wanted:**
* the two checkout commits;
* the image ids (new and rollback);
* the checks above, including the first scheduled run's load lines.

## Not authorized here (each will be its own note, on its own go)
* **Turning on `rds_from_task_secret`:** after Part B's checkpoint shows a task started with the secret.
* **Any state's `scrape.load_on_fargate: true`:** after the Mac rehearsal (plan step 3), one small state first (D4).
* Anything else: no data change, relabel, schedule change, `.env` change, or api-v3 rebuild.

Design: ddp-infra `PLAN-cloud-load-on-fargate.md` §5–§6 (PR #538). Ticket: OPEN-633.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
