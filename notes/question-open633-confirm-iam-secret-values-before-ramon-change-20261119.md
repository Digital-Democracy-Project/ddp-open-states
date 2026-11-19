# QUESTION (OPEN-633, read-only): confirm five values before Ramon changes the scrapers' permissions. 2026-11-19 (Mac side, State Specific Handling)

**Not a GO. Read-only: change nothing.** Ramon will make the permission change himself (Part A of request `9ea0c4a`), then build v70 with the secret (Part B). He asked that you double-check these values first. Please report each one.

**Never print the secret's contents** (no `get-secret-value`). Identifiers, addresses and policy names only.

## 1. The execution role
* Run `aws ecs describe-task-definition --task-definition ddp-scrapers --query 'taskDefinition.{rev:revision,exec:executionRoleArn,task:taskRoleArn}'`.
* Our docs say the execution role is `arn:aws:iam::350941939790:role/ddp-scraper-ecs-execution-role`. Does it match? Report the revision too (72 = v69 expected).

## 2. The secret
Is ddp-sync's `RDS_CREDENTIALS_SECRET_ARN` on EC2 exactly this ARN, the one named in `deploy/rotate-database-url.sh`?
```
arn:aws:secretsmanager:us-east-1:350941939790:secret:rds!db-71d3d3d9-9466-4ce2-a4c1-22839edea60b-O0CMr6
```
* Compare the identifier only, for example `docker exec ddp-sync-ddp-sync-1 printenv RDS_CREDENTIALS_SECRET_ARN`.
* The full ARN, including the 6-character suffix, is what the task definition will name.

## 3. Its encryption key
* Run `aws secretsmanager describe-secret --secret-id <that ARN> --query KmsKeyId`. Report `KmsKeyId` only (`describe-secret` never returns the value).
* **Empty, or the AWS-managed `alias/aws/secretsmanager`:** no KMS grant is needed.
* **A customer-managed key:** the role also needs `kms:Decrypt` on that key ARN. Say which key.

## 4. Is the one-line permission enough?
The plan: one inline policy on the execution role allowing only `secretsmanager:GetSecretValue` on that one secret ARN (plus item 3's `kms:Decrypt` if that applies). The task definition's `secrets` will name it as `<ARN>:username::` and `<ARN>:password::`.

Please check, read-only:
* **What the role has today:**
  * `aws iam list-attached-role-policies --role-name ddp-scraper-ecs-execution-role`;
  * `aws iam list-role-policies --role-name ddp-scraper-ecs-execution-role`.
  * Does anything already grant `GetSecretValue` on this secret? Is anything denying it, such as a permissions boundary (`aws iam get-role ... --query Role.PermissionsBoundary`)?
* **Today's answer, before the change:** `aws iam simulate-principal-policy --policy-source-arn <role ARN> --action-names secretsmanager:GetSecretValue --resource-arns <secret ARN>`. We expect `implicitDeny`.
* **The secret's own resource policy:** `aws secretsmanager get-resource-policy --secret-id <ARN>`. Does it deny other principals?
* **Say if you see anything else** ECS would need to inject a Secrets Manager secret through the execution role that this plan misses.

## 5. The address values for Part B
ddp-sync's `RDS_HOST`, `RDS_PORT` and `RDS_DBNAME` on EC2 (the address only, no username or password), for `TASK_RDS_HOST`, `TASK_RDS_PORT` and `TASK_RDS_DBNAME`. For example, `docker exec ddp-sync-ddp-sync-1 printenv RDS_HOST RDS_PORT RDS_DBNAME`.

## Reply wanted
A short reply note on this branch with the five answers, each marked "matches" or "differs" against what is written here.

## Not authorized
No IAM change, no task-definition registration and no `get-secret-value`. Ramon makes the change himself.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
