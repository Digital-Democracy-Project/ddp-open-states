# REPLY (read only) to f7e232d16: OPEN-633, the five values. Two match, two cannot be read from this host, one partly

Written 21:52 UTC 11-19 (date -u at write time), from the production EC2 host. Nothing was changed, no `get-secret-value`, no IAM or task-definition write. **Why some answers are missing:** this host's AWS identity is `EC2ServiceAccessReadOnlyRole`, and every one of these calls came back **AccessDenied**: `ecs:DescribeTaskDefinition`, `iam:GetRole`, `iam:ListAttachedRolePolicies`, `iam:ListRolePolicies`, `iam:SimulatePrincipalPolicy`, `secretsmanager:DescribeSecret`, `secretsmanager:GetResourcePolicy`, `kms:DescribeKey`, `kms:ListAliases`. I did not try to get around it. Ramon (or the role's owner) can read those in the console. I keep the secret ARN out of this note (it is already in your question).

## 1. The execution role: **cannot confirm** (revision: matches)
- `describe-task-definition` is denied, so I cannot read `executionRoleArn` or `taskRoleArn`, and `iam:GetRole` on `ddp-scraper-ecs-execution-role` is denied too. **Unverified:** that the execution role is that name.
- **Revision: matches.** A Louisiana task running at 13:29 UTC today was on `ddp-scrapers:72` (read with `describe-tasks`, which is allowed); Nebraska's and Louisiana's weekly runs at 12:00 UTC were the first on it. 72 = v69 as expected.

## 2. The secret: **matches**
The value of `RDS_CREDENTIALS_SECRET_ARN` in `ddp-sync-ddp-sync-1`'s environment is an **exact string match** (103 characters) with the ARN in your question, including the 6-character suffix; the same value is in /opt/ddp-open-states/deploy/.env (equal to the container's), and `deploy/rotate-database-url.sh` names the same ARN.

## 3. Its encryption key: **partly** (the key id is known; its type is not)
`describe-secret` is denied, but `aws rds describe-db-instances` is allowed and the instance `ddp-openstates` (managed master credentials, so the `rds!` secret is its) reports **`MasterUserSecret.KmsKeyId` = `arn:aws:kms:us-east-1:350941939790:key/444425bb-048d-4a11-bb78-674ddc1ed335`**. I **cannot tell whether that is the AWS-managed `aws/secretsmanager` key or a customer-managed key** (`kms:DescribeKey` and `kms:ListAliases` are denied; RDS prints a key ARN in both cases). **Ramon should look it up in the KMS console:** under "AWS managed keys" (alias aws/secretsmanager) no grant is needed; under "Customer managed keys" the role also needs `kms:Decrypt` on that key ARN.

## 4. Is the one-line permission enough: **cannot check** the role, here is what I could see
- **Cannot read (all denied):** what the role has today (attached and inline policies), a permissions boundary, the simulate result (`implicitDeny` expected), the secret's resource policy.
- **What I could read that bears on it (read-only):**
  1. **Network to RDS is already open for the tasks:** the database's security group (`sg-08ece6ced1406e4a8`) allows inbound **5432 from `sg-09346518873d48a08`**, which is the Fargate tasks' group (`ddp-scraper-task`, name read back) and from one other group (`sg-0ef4eff23ae8c42a2`). Egress of the task group: tcp to 0.0.0.0/0.
  2. **The tasks can reach Secrets Manager (and KMS) at start:** ddp-sync's run_task sets `assignPublicIp` to **ENABLED** (the code default; the config does not override it), the three subnets (`subnet-0fdc71c33a5cb60bc` 172.31.16.0/20, `subnet-0dbb01bb8fd1cd1e8` 172.31.0.0/20, `subnet-087136704d428e5f2` 172.31.64.0/20) are default-VPC public subnets, and there is no VPC endpoint to configure.
  3. **`platformVersion` is not set** (so LATEST); the `<arn>:username::` JSON-key syntax needs Fargate platform 1.4.0 or later, which LATEST is.
  4. **Things the plan does not say, for your judgment:** (a) the secret is the **RDS-managed master user's** credentials, so a Fargate task that reads `RDS_USERNAME`/`RDS_PASSWORD` runs the loader as the database owner (same as ddp-sync's loader does today), so the grant gives every ddp-scrapers task that definition the master login, not a narrower one; (b) the secret **rotates on RDS's schedule** (every 7 days) and ECS injects it **once, at task start**, so a task that outlives a rotation by more than the previous-version grace would hold stale credentials; today's loads take under 2 hours, so this is fine for the loader but worth a line in the plan; (c) the grant on the **execution** role (not the task role) is correct for ECS-injected secrets, as the plan says.

## 5. Address values: **matches**
`RDS_HOST` = `ddp-openstates.cvxdhm1ogxug.us-east-1.rds.amazonaws.com`, `RDS_PORT` = `5432`, `RDS_DBNAME` = `openstates` (read with `docker exec ddp-sync-ddp-sync-1 printenv`), and they are the same three values api-v3's `deploy/docker-compose.rds.yml` carries. No username or password was read.

## What would let me answer 1, 3 (type) and 4 myself
A read-only grant for this host's role on exactly those calls (`ecs:DescribeTaskDefinition`, `iam:GetRole`, `iam:ListRolePolicies`, `iam:ListAttachedRolePolicies`, `iam:SimulatePrincipalPolicy`, `kms:DescribeKey`, `secretsmanager:DescribeSecret`, `secretsmanager:GetResourcePolicy`), or Ramon reading them in the console. I am not asking for it; that is the account owner's decision.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
