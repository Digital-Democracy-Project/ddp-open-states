# OPEN-200 Fargate spike — infrastructure

Terraform for the prototype described in `PLAN-scraper-execution-fargate-draft.md` and scoped
by OPEN-200: one ECR repository, one Fargate-only ECS cluster, the two IAM roles a task needs,
a CloudWatch log group, and a security group for public-IP-per-task egress (Option A in the
draft — no NAT, no shared gateway, so a WAF/egress comparison actually measures per-task
addresses rather than one shared one).

**Status: written, not applied.** This dev environment has no AWS credentials configured at
all (no profile, no access key, no `AWS_*` env vars — checked 2026-08-28), and creating IAM
roles/ECR/ECS resources needs permissions well beyond the scoped S3 access this pipeline
already has elsewhere. Applying this is Ramon's call: either run it from wherever real AWS
credentials live, or hand this environment a scoped IAM identity with the permissions listed
below.

`terraform validate`/`fmt` could not be run here either — `terraform` isn't installed, and
installing it (or docker's `buildx` component, hit for the same reason building the container
image) requires `sudo chown` on this machine's Homebrew directories, which is a system-wide
permission change on a shared machine and not something to do unilaterally for a dev-tool
install. Worth knowing if this comes up again elsewhere.

## What this does NOT do

- Does not push an image to the ECR repo it creates — that's a separate `docker build` /
  `docker push` step, using the `Dockerfile` at the repo root.
- Does not run a task or create an EventBridge schedule — Phase 12/15 of the draft, after
  manual execution is proven reliable. Scheduling is explicitly a later step in both the draft
  and OPEN-200's own scope.
- Does not decide the runtime. Provisioning this and running one task on it is what OPEN-200's
  spike needs in order to *make* that decision with evidence — it is not the decision itself.

## Minimum IAM permissions to apply this

`ecr:CreateRepository`, `ecs:CreateCluster`, `ecs:RegisterTaskDefinition`,
`logs:CreateLogGroup`, `ec2:CreateSecurityGroup` + `ec2:Describe*` (VPC/subnet lookups),
`iam:CreateRole`/`iam:PutRolePolicy`/`iam:AttachRolePolicy`/`iam:PassRole` scoped to role names
matching `ddp-scraper-*` (this config's own naming, so a policy can be scoped narrowly rather
than granted broadly).

## Variables that need real values before `apply`

See `variables.tf`. `vpc_id` and `public_subnet_ids` are not guessed here — they need whichever
VPC/subnets DDP's existing AWS resources (the S3 buckets referenced throughout this repo) live
in, or a new prototype VPC if isolation from those is preferred. That is exactly the kind of
call this document's own author should not make silently.

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
