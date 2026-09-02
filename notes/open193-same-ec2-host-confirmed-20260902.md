# OPEN-193 — confirmed: same EC2 host runs ddp-broker, api-v3, and ddp-sync

*Replies to `notes/open193-rds-secretsmanager-access-verified-20260902.md`.*

Asked Ramon directly about the open question in that note. Confirmed: the box you verified
`rds:DescribeDBInstances`/`secretsmanager:GetSecretValue` from — the one running
`EC2ServiceAccessReadOnlyRole` — **is** the same EC2 instance that runs `ddp-broker`, `api-v3`,
and `ddp-sync`. Not a different box. So the DB-access half of item 2 was verified from the
right place; no need to redo it elsewhere.

That clears the way for the rest of item 2: `ecs:RunTask`/`DescribeTasks`/`StopTask` and
`iam:PassRole` are on the same role, on the same box — testing those (and, once that's clean,
actually deploying the merged `ddp-sync` code and doing the canary run from items 3-4) can all
happen from right here, no cross-host uncertainty left.

One earlier note said this box had "no `ddp-sync` checkout or systemd unit present" — worth
squaring that against today's finding before assuming the deploy step is a clean pull. If
`ddp-sync` genuinely isn't checked out there yet, that's the next concrete step: clone it,
merge PR #104 is already on `main`, install the systemd unit
(`infrastructure/ddp-sync.service` in that repo), wire `RDS_DATABASE_URL` into its environment
from the secret you already confirmed you can read, and fill in `sync_schedule.yaml`'s
`cloud_path.fargate` block with the real cluster/task-definition/subnet/security-group values
before touching `cloud_path.enabled`.
