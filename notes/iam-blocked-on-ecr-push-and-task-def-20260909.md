# v15 is built -- but this host's IAM role can't push to ECR or read/register the task-def

*Follows up on `notes/v15-build-arm64-emulation-missing-fixed-20260909.md` and Ramon's go-ahead
on tag/push + task-def.* `ddp-scrapers:v15` built successfully (confirmed via real exit code,
`docker images` shows it: `ca776bb3e6ac`, 2.21GB). Blocked on the next two steps — this is a
clean IAM gap, not a retryable error.

## What's missing, confirmed by direct invocation

- `aws ecr get-login-password` → `AccessDeniedException: ... not authorized to perform:
  ecr:GetAuthorizationToken`. Blocks `docker login`/`docker push` entirely.
- `aws ecs describe-task-definition --task-definition ddp-scrapers` → `AccessDeniedException:
  ... not authorized to perform: ecs:DescribeTaskDefinition`. Blocks reading revision 18 to build
  revision 19 from it. Never got far enough to test `ecs:RegisterTaskDefinition` too, but there's
  no reason to expect it's present if `DescribeTaskDefinition` isn't.

This host's role (`EC2ServiceAccessReadOnlyRole`) already has the ECS *runtime* actions from the
earlier OPEN-193 setup (`RunTask`/`DescribeTasks`/`StopTask`/`ListTasks`,
`logs:DescribeLogStreams`/`GetLogEvents`) — this is a different, narrower gap: build/deploy-time
actions (`ecr:GetAuthorizationToken`, `ecr:BatchCheckLayerAvailability`, `ecr:PutImage`,
`ecr:InitiateLayerUpload`, `ecr:UploadLayerPart`, `ecr:CompleteLayerUpload` scoped to the
`ddp-scrapers` repo; `ecs:DescribeTaskDefinition`/`ecs:RegisterTaskDefinition`, which per
`infra/fargate-spike/README.md`'s own IAM policy notes can't be scoped tighter than `Resource:
"*"` for those two specific actions — that's a real AWS limitation, not something to fight).

## Next step

Needs an IAM policy change on this host's role — not something I can self-grant. Once that's in
place, I'll pick up exactly where this left off: tag `v15`, push, read revision 18, register
revision 19 pointed at `v15`. The image itself doesn't need rebuilding either way, so no time
lost waiting on this.
