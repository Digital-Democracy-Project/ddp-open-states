# REQUEST (OPEN-633, step 0): let the ddp-scrapers task definition carry the RDS login as a secret. 2026-11-19 (Mac side, State Specific Handling)

**Not a GO.** Nothing here runs until Ramon says go. Each part below waits for its own go and its own checkpoint.

## Why
Ramon decided (OPEN-633, D2) that the Fargate load and archive tasks should read the RDS login themselves instead of being handed it.

* **Today:** ddp-sync passes the full connection string, password included, as a plain `DATABASE_URL` launch variable (`openstates_archive.py`, the archive launcher). That variable is stored in ECS's record of every task start.
* **Design:** ddp-infra `PLAN-cloud-load-on-fargate.md` §5 D2 and §6 step 0.
* **Code:**
  * ddp-open-states #428 (the task builds the URL from the secret);
  * ddp-sync #299 (the switch that stops passing it).

  Both are not merged yet, and both default to off.

## What is safe about the order
* **A passed `DATABASE_URL` always wins inside the task** (#428). Until ddp-sync's switch `rds_from_task_secret` is turned on, the secret in the task definition is not used for the login.
* **One real risk:** ECS fetches every secret in a task definition **before the container starts**. If the task's execution role cannot read the secret, **every** ddp-scrapers task fails to start: collections, archives and probes. That is why Part 1 must be confirmed before Part 2.

## Part 1. IAM (production; on Ramon's go)
1. Find the RDS-managed secret ddp-sync already reads: the value of `RDS_CREDENTIALS_SECRET_ARN` in ddp-sync's environment on EC2. **Do not print its contents.**
2. Find the ddp-scrapers task definition's execution role: `aws ecs describe-task-definition --task-definition ddp-scrapers --query taskDefinition.executionRoleArn`.
3. Give that role `secretsmanager:GetSecretValue` on **that one secret ARN** only (an inline policy is enough).
   * If the secret is encrypted with a customer-managed KMS key (not the default `aws/secretsmanager` key), the role also needs `kms:Decrypt` on that key.
   * Check which key it is with `aws secretsmanager describe-secret --secret-id <arn> --query KmsKeyId`. Empty means the default key, and no KMS grant is needed.
4. Verify without starting a task: `aws iam simulate-principal-policy --policy-source-arn <execution role arn> --action-names secretsmanager:GetSecretValue --resource-arns <secret arn>` returns `allowed`.

**Checkpoint wanted:**
* the role name;
* that the grant is scoped to the one secret;
* the KMS answer;
* the simulate result.

## Part 2. Task definition (production; on Ramon's go, only after Part 1's checkpoint)
Done by the image release that carries #428 (Ramon runs it on the Mac, as every image release).

* Run the release with these set:
  ```
  TASK_RDS_SECRET_ARN=<the secret ARN from Part 1> TASK_RDS_HOST=<ddp-sync's RDS_HOST> TASK_RDS_PORT=<ddp-sync's RDS_PORT> TASK_RDS_DBNAME=<ddp-sync's RDS_DBNAME> bash deploy-scrapers-image.sh
  ```
* The script adds `RDS_USERNAME`/`RDS_PASSWORD` (from the secret's `username` and `password` keys) and the three address values to the new revision. It prints `RDS secret in task definition: yes`.
* Every later image copies them forward without the variables.
* It refuses a missing address value, or a task definition without an execution role.

**Checkpoint wanted:**
* the new revision number;
* `describe-task-definition` showing the two secret **names** and the three environment names (not values);
* the **next ddp-scrapers task of any kind** reaching RUNNING and stopping with its usual exit code. That proves ECS could read the secret.

**If that task fails to start** with a secrets error:
* deregister the new revision, so the family falls back to the previous one, which has no secret (`aws ecs deregister-task-definition --task-definition ddp-scrapers:<rev>`);
* then report it.

## Not in this request (each will be its own note)
* **Turning on `rds_from_task_secret` in ddp-sync:** after #299 is deployed and Part 2's checkpoint is in. That is the step that actually stops passing the password.
* **Any state's `scrape.load_on_fargate: true`:** after the Mac rehearsal (plan §4), one small state first (D4).
* **ddp-sync deploys, image builds and RDS changes** beyond what Parts 1 and 2 name.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
