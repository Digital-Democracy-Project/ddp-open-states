# OPEN-200 Fargate spike — infrastructure

Terraform for the prototype described in `PLAN-scraper-execution-fargate-draft.md` and scoped
by OPEN-200: one ECR repository, one Fargate-only ECS cluster, a CloudWatch log group, and a
task definition. **Deliberately split in two, so a credential handed to an agent working this
ticket can never create an IAM role or touch a security group, even by mistake:**

- **This module** — everything below — creates only `ecr:*`/`ecs:*`/`logs:*` resources.
- **Your part, done separately with your own broader access** — the two IAM roles and the one
  security group. Neither is a Terraform resource in this directory at all; both are plain
  input variables (`execution_role_arn`, `task_role_arn`, `security_group_id` in
  `variables.tf`). That isn't just a permissions boundary on paper — the resource blocks that
  used to create them were deleted, so there is nothing here that *could* create or modify them
  even with a broader credential.

## Setup — do this part yourself first

Three resources, by CLI (or console, or your own Terraform elsewhere — whichever you already
have set up). Fill in `<region>`/`<account-id>`/`<vpc-id>`.

```bash
# 1. Execution role — pulls the image, writes logs. Nothing about the scraper's own data.
aws iam create-role --role-name ddp-scraper-ecs-execution-role \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ecs-tasks.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
aws iam attach-role-policy --role-name ddp-scraper-ecs-execution-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# 2. Task role — what cloud_collector.py's boto3 client actually runs as. Scoped to one bucket.
aws iam create-role --role-name ddp-scraper-task-role \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ecs-tasks.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
aws iam put-role-policy --role-name ddp-scraper-task-role --policy-name ddp-scraper-memory-access \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Sid":"MemoryAndWorkingTierReadWrite","Effect":"Allow","Action":["s3:GetObject","s3:PutObject","s3:ListBucket"],"Resource":["arn:aws:s3:::ddp-prod-s3-openstates-backups","arn:aws:s3:::ddp-prod-s3-openstates-backups/*"]}]}'
# If that bucket uses a customer-managed KMS key (check its default encryption setting), this
# role also needs kms:Decrypt/kms:GenerateDataKey scoped to the key's ARN, or every GetObject/
# PutObject fails with AccessDenied for a reason this policy alone won't explain.

# 3. Security group — outbound HTTPS only, no inbound. The one new network resource this spike needs.
aws ec2 create-security-group --group-name ddp-scraper-task --vpc-id <vpc-id> \
  --description "OPEN-200 prototype Fargate task -- outbound HTTPS only, no inbound"
aws ec2 authorize-security-group-egress --group-id <output sg-id> \
  --protocol tcp --port 443 --cidr 0.0.0.0/0
```

Note the three ARNs/ID this produces — they're what `terraform.tfvars` (or `-var` flags) below need.

## The credential to hand me for the rest

Minimal, auditable, and specifically **no `ec2:*` and no `iam:Create*`/`Put*`/`Attach*`** —
only `iam:PassRole` scoped to the two exact ARNs from step 1/2 above, which lets ECS attach a
role you already created to a task; it grants no ability to create, modify, or assume anything.
A session token (`aws sts get-session-token` or an assumed role) is preferable to a long-lived
IAM user key, so it just expires rather than needing manual cleanup afterward.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECRAuth",
      "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken",
      "Resource": "*"
    },
    {
      "Sid": "ECRRepo",
      "Effect": "Allow",
      "Action": [
        "ecr:CreateRepository", "ecr:DescribeRepositories", "ecr:PutImageTagMutability",
        "ecr:PutImageScanningConfiguration", "ecr:TagResource", "ecr:ListTagsForResource",
        "ecr:BatchCheckLayerAvailability", "ecr:InitiateLayerUpload", "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload", "ecr:PutImage", "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer", "ecr:DescribeImages"
      ],
      "Resource": "arn:aws:ecr:<region>:<account-id>:repository/ddp-scrapers"
    },
    {
      "Sid": "ECSCluster",
      "Effect": "Allow",
      "Action": [
        "ecs:CreateCluster", "ecs:DescribeClusters", "ecs:DeleteCluster",
        "ecs:PutClusterCapacityProviders", "ecs:TagResource"
      ],
      "Resource": "arn:aws:ecs:<region>:<account-id>:cluster/ddp-scrapers-prototype"
    },
    {
      "Sid": "ECSTaskDefinition",
      "Effect": "Allow",
      "Action": ["ecs:RegisterTaskDefinition", "ecs:DeregisterTaskDefinition", "ecs:DescribeTaskDefinition"],
      "Resource": "*"
    },
    {
      "Sid": "ECSRun",
      "Effect": "Allow",
      "Action": ["ecs:RunTask", "ecs:DescribeTasks", "ecs:StopTask", "ecs:ListTasks"],
      "Resource": "arn:aws:ecs:<region>:<account-id>:task-definition/ddp-scraper-prototype:*",
      "Condition": { "ArnEquals": { "ecs:cluster": "arn:aws:ecs:<region>:<account-id>:cluster/ddp-scrapers-prototype" } }
    },
    {
      "Sid": "Logs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup", "logs:PutRetentionPolicy", "logs:DescribeLogGroups",
        "logs:DescribeLogStreams", "logs:GetLogEvents", "logs:FilterLogEvents"
      ],
      "Resource": "arn:aws:logs:<region>:<account-id>:log-group:/aws/ecs/ddp-scrapers*"
    },
    {
      "Sid": "PassRoleToECSOnly",
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": [
        "arn:aws:iam::<account-id>:role/ddp-scraper-ecs-execution-role",
        "arn:aws:iam::<account-id>:role/ddp-scraper-task-role"
      ],
      "Condition": { "StringEquals": { "iam:PassedToService": "ecs-tasks.amazonaws.com" } }
    }
  ]
}
```

**Two actions above can't be scoped tighter than `Resource: "*"` — this is an AWS limitation on
those specific actions, not a gap in this policy:** `ecr:GetAuthorizationToken` is
account-level by design (it returns a token valid for every repo the caller can otherwise
reach — which here is just the one `ECRRepo`/`ECRPush` statement above), and
`RegisterTaskDefinition`/`DeregisterTaskDefinition` don't support resource-level permissions at
all (the definition doesn't have an ARN until it's registered). Neither grants access beyond
what the rest of the policy already allows.

**Zero `ec2:*` anywhere in this policy.** Nothing here can create, modify, describe, or delete
a security group, an instance, or anything else EC2-shaped, production or otherwise.

## What this does NOT do

- Does not push an image to the ECR repo it creates — that's a separate `docker build` /
  `docker push` step, using the `Dockerfile` at the repo root.
- Does not run a task or create an EventBridge schedule — Phase 12/15 of the draft, after
  manual execution is proven reliable. Scheduling is explicitly a later step in both the draft
  and OPEN-200's own scope.
- Does not decide the runtime. Provisioning this and running one task on it is what OPEN-200's
  spike needs in order to *make* that decision with evidence — it is not the decision itself.

## Variables that need real values before `apply`

See `variables.tf`. `execution_role_arn`, `task_role_arn`, `security_group_id` come from the
setup step above. `public_subnet_ids` is not guessed here either — it needs whichever subnets
DDP's existing AWS resources live in, or a new prototype VPC's subnets if isolation is
preferred. That is exactly the kind of call this document's own author should not make
silently.

## After `apply`

The task definition declares `runtime_platform.cpu_architecture = "ARM64"`, matching the image
actually built and run locally during this PR's validation -- build for the same architecture,
or change that block (and rebuild on x86_64) first. ECR's tags are IMMUTABLE (`ecr.tf`), so
each rebuild during the spike needs a new tag, matched with `-var image_tag=<same tag>` on the
next `terraform apply` (`variables.tf` explains why this is a variable rather than convenience
`:prototype` reuse).

```
docker build --platform linux/arm64 -t ddp-scraper:<tag> .
docker tag ddp-scraper:<tag> <output.ecr_repository_url>:<tag>
aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com
docker push <output.ecr_repository_url>:<tag>
terraform apply -var image_tag=<tag>   # updates the task definition to point at it
aws ecs run-task --cluster <output.cluster_name> --task-definition <output.task_definition_arn> \
    --launch-type FARGATE --network-configuration "awsvpcConfiguration={subnets=[<output.public_subnet_ids>],securityGroups=[<output.security_group_id>],assignPublicIp=ENABLED}"
```

`assignPublicIp=ENABLED` and the subnet list are `run-task`-time arguments, not task-definition
fields -- there is nothing to misconfigure in Terraform here, only to remember at launch time,
which is why `public_subnet_ids` is surfaced as an output rather than only an input.

Then watch CloudWatch Logs under `/aws/ecs/ddp-scrapers`, exactly as the draft's Milestone 3
describes.

## Before trusting `readonlyRootFilesystem`

A plain local `docker run` does not enforce it. Before the first real AWS task, run the image
locally the way Fargate will actually run it:

```
docker run --rm --read-only --tmpfs /tmp <image> <source> [key=value ...]
```

If it fails somewhere other than `/tmp`, that is a second writable path this container
actually needs and this task definition does not yet grant.

## One environment note, unrelated to credentials

`terraform validate`/`fmt` still can't be run in the dev session that authored this — `terraform`
isn't installed there, and neither is Docker's `buildx` (needed for `docker build --secret`).
Installing either requires `sudo chown` on that shared machine's Homebrew directories, which
that session declined to do unilaterally. Worth knowing if this comes up again.
