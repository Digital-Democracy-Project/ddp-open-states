# OPEN-191/193 — question for whoever ran the 2026-08-29/30 per-jurisdiction Fargate rehearsal

*Replies to `notes/open193-fargate-config-values-landed-subnets-still-open-20260902.md`.*

Last piece blocking OPEN-193 item 4 (the canary run): `sync_schedule.yaml`'s `cloud_path.fargate.subnets`
is still blank, and it's a genuine disagreement, not just an unfilled field --

- The original OPEN-193 request said "the private subnet IDs the existing Fargate task already uses."
- `infra/fargate-spike/variables.tf`'s own comment on `public_subnet_ids` says the rehearsal deliberately
  used **public** subnets with auto-assigned public IP ("Option A," specifically to avoid every task
  sharing one NAT gateway's egress IP).

Can't resolve this from the verification host: `ecs:ListTasks` and CloudWatch Logs read access
aren't granted there, so there's no way to look up which subnet(s) the actual 2026-08-29/30
rehearsal task ran in, or pull its logged network config.

**Whoever ran that rehearsal** — which subnet(s) did it actually use? If it's easier to check than
to recall, the task's own `networkConfiguration` (from the `aws ecs run-task` invocation itself, or
its logged output) would settle it either way. Once that's confirmed, `sync_schedule.yaml`'s
`subnets: []` is the one remaining fill-in before the canary run in item 4 can happen.
