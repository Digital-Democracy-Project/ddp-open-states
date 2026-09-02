# OPEN-193 — item 2 (IAM) fully verified by direct invocation, three real bugs caught along the way

*Replies to `notes/open193-same-ec2-host-confirmed-20260902.md`.*

Ramon confirmed this box's `EC2ServiceAccessReadOnlyRole` is the right host, and asked for every
statement to actually be exercised, not just read as policy JSON. Went through all of it live.
Three real problems surfaced and got fixed (all fixes applied directly to the role by Ramon,
iterating with a description of each failure):

1. **`ecs:DescribeTasks`/`ecs:StopTask` were scoped to the task-*definition* ARN** — the same
   resource used for `ecs:RunTask`. That's the wrong IAM resource type for those two actions;
   they need a task ARN (`.../task/<cluster>/*`), which is a distinct resource type from
   `.../task-definition/<family>:*`. Split into two statements (`ECSRunTask` keeps the
   task-definition scoping; new `ECSPollAndStopTasks` uses the task ARN pattern). Caught this
   the direct way: `DescribeTasks` on a fake task ID returned `AccessDeniedException`, not a
   clean not-found.
2. **The granted policy (and my first proposed fix) both named the wrong cluster/task-definition
   family** — `ddp-scrapers-prototype`/`ddp-scraper-prototype`, copied from
   `infra/fargate-spike/README.md`'s generic OPEN-200-spike bootstrap example. The real
   deployed names are both `ddp-scrapers` (no suffix) — `infra/fargate-spike/variables.tf`'s own
   comment records this as Ramon's actual naming decision from 2026-08-28, explicitly *not* the
   `-prototype`/`ddp-scraper` guesses. Worth flagging plainly: **the original OPEN-193 request
   note itself cited that same stale README as its scoping reference**, so this wasn't just a
   typo in the IAM policy — the request's own "same scoping pattern as..." pointer was already
   out of date when it was written. Caught via `ClusterNotFoundException` once the resource-type
   fix above stopped masking it.
3. **`ec2:DescribeSubnets` doesn't support the `ec2:Vpc` condition key I originally suggested** —
   EC2 `Describe*` actions are bulk, account/region-wide reads and generally don't carry
   resource-level conditions the way mutating actions do; the condition just evaluated false and
   silently blocked the whole statement even though it read correctly. Dropped the condition
   entirely (`Resource: "*"`, unconditioned), matching the existing `DescribeSecurityGroupsAndInstances`
   statement's own pattern in policy 1. My mistake to suggest it in the first place.

(One more purely transcription-side hiccup, not a real bug: a manual re-paste round introduced a
singular/plural typo, `task-definition/ddp-scraper:*` instead of `ddp-scrapers:*`, caught the
same way — `AccessDeniedException` on the correct family name.)

## Confirmed working by direct invocation (not just reading the JSON)

- `rds:DescribeDBInstances`, `ec2:DescribeSecurityGroups`, `ec2:DescribeInstances`,
  `ec2:DescribeSubnets` — all clean reads.
- `secretsmanager:GetSecretValue` on the RDS master credential — pulled it and did a live `psql`
  connection to `ddp-openstates`/`openstates_admin` (see the prior note on this branch).
- `secretsmanager:GetSecretValue` on the two `ddp-api/*` secrets and `ddp-sync/credentials` —
  confirmed each resolves and is readable (fetched only the `ARN` field each time, never the
  secret content, and only Fargate-relevant testing was in scope this round —
  `secretsmanager:PutSecretValue` on `ddp-api/api-keys` deliberately **not** exercised, since
  that would write a new version into a live production secret; left unverified by direct
  invocation on purpose).
- `ecs:RunTask` + `iam:PassRole` (both `ddp-scraper-ecs-execution-role` and
  `ddp-scraper-task-role`) — launched two real Fargate tasks on the real cluster, container
  command overridden to a harmless no-op (`echo ... && sleep N`) rather than the real scraper
  entrypoint, so nothing hit a legislature site or wrote to RDS/S3. First task reached `RUNNING`
  then self-stopped with container exit code 1 — reads like an `ENTRYPOINT`/command-override
  interaction quirk in the scraper image itself (not IAM: if either role had failed to pass, the
  task would never have reached `RUNNING` at all, and it did). Second task launched the same way
  and was explicitly stopped with `ecs:StopTask` (`StopCode: UserInitiated`, custom reason string
  came through), confirming that action directly rather than relying on the first task's
  self-stop.
- `ecs:DescribeTasks` — polled both test tasks through their full lifecycle.

**Item 2 of the original request is done and independently verified, not just granted.**

## One open discrepancy worth resolving before item 3 (real `sync_schedule.yaml` values)

The original OPEN-193 note said "the private subnet IDs the existing Fargate task already
uses." `infra/fargate-spike/variables.tf`'s own comment on `public_subnet_ids` says the
opposite: the actual rehearsal deliberately used **public** subnets with auto-assigned public
IP ("Option A," specifically to avoid every task sharing one NAT gateway's egress IP). Couldn't
resolve which is right from here — `ecs:ListTasks` isn't granted, so there's no way to look up
which subnet the real historical rehearsal task actually used. Used this box's own public subnet
for the two test tasks above (they only needed to reach ECR/CloudWatch Logs for a no-op command,
which worked fine), but didn't treat that as confirmation of the *right* subnet for real
jurisdiction scrapes — flagging rather than guessing into `sync_schedule.yaml`.

Confirmed real values otherwise, ready for item 3: `cluster: ddp-scrapers`,
`task_definition: ddp-scrapers`, `security_groups: [sg-09346518873d48a08]` (named
`ddp-scraper-task`), `memory_bucket: ddp-openstates-scraper-memory`, `container_name: "scraper"`
(matches `sync_schedule.yaml`'s own default).
