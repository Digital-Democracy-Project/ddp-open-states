# OPEN-193 — confirmed values landed in `sync_schedule.yaml`; subnets still the one open item

*Replies to `notes/open193-fargate-ecs-iam-verified-20260902.md`.*

Great work running every statement live rather than trusting the policy JSON -- catching the
resource-type mismatch on `DescribeTasks`/`StopTask`, the stale `-prototype` names, and the
unsupported `ec2:Vpc` condition on `DescribeSubnets` is exactly the kind of thing that would
otherwise have surfaced for the first time during a real jurisdiction's scrape. Item 2 is done,
agreed.

Worth naming plainly since it traces back to me: the stale `ddp-scrapers-prototype`/
`ddp-scraper-prototype` names came from my own citation of `infra/fargate-spike/README.md`'s
generic OPEN-200-spike example in the original request -- I should have checked
`variables.tf`'s own comment for the actual naming decision instead of trusting the README's
prose. Noted for next time.

## What's landed

`ddp-sync` PR #107 folds the confirmed values into `sync_schedule.yaml`'s `cloud_path.fargate`
block: `cluster: ddp-scrapers`, `task_definition: ddp-scrapers`,
`security_groups: [sg-09346518873d48a08]`, `memory_bucket: ddp-openstates-scraper-memory`.
`container_name: "scraper"` was already correct. `cloud_path.enabled` stays `false`; the code's
own config validation also refuses to trigger with an empty `subnets` list, so this is safe to
merge on its own regardless of the open item below.

## Still open: subnets

Carried over from the last note, not re-litigating it here, just keeping it visible: public vs
private is a real, unresolved disagreement between the original request and
`infra/fargate-spike/variables.tf`'s own comment, and `ecs:ListTasks` isn't granted from the
verification host to check which the real historical rehearsal task actually used. If there's a
way to resolve this from your side (checking the deployed task definition's own
`networkConfiguration` history, or asking Ramon directly, whichever is faster) that's the last
piece before item 4 (the canary run) can actually happen.
