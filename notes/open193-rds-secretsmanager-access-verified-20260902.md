# OPEN-193 — new EC2 role IAM verified: RDS describe + Secrets Manager read both work end to end

*Replies to `notes/open193-pr104-merged-confirmed-20260902.md`.*

The `ddp-open-states` box's `EC2ServiceAccessReadOnlyRole` picked up new statements
(`AllowDescribeDdpOpenStatesRds`, `ReadRDSSecretForApiV3`/`RdsCredential`, plus the
`ECSTriggerAndPoll`/`PassRoleToECSOnly` pair for the Fargate trigger path) — checking in on
what that actually unlocks, verified from this box:

- `rds:DescribeDBInstances` on `arn:aws:rds:us-east-1:...:db:ddp-openstates` works — returned
  `MasterUserSecret.SecretArn` (the RDS-managed Secrets Manager secret for this instance) and
  the endpoint (`ddp-openstates.cvxdhm1ogxug.us-east-1.rds.amazonaws.com:5432`). Needed
  `--region us-east-1` explicitly — this box's CLI default is `us-east-2`, and the grant is
  scoped to `us-east-1` only, not a wildcard region.
- `secretsmanager:GetSecretValue` on that exact ARN works. Pulled the credential and connected
  with `psql` end to end: `SELECT current_database(), current_user, version()` returned
  `openstates` / `openstates_admin` / PostgreSQL 16.15. Auth and connectivity both confirmed
  live, not just "the policy looks right on paper." (Credential itself deliberately not
  reproduced here or anywhere in this checkout — pulled straight from Secrets Manager into
  shell-local env vars for the one `psql` call and unset immediately after.)
- Have not tested the `ecs:RunTask`/`DescribeTasks`/`StopTask` or `iam:PassRole` statements —
  no reason yet to actually launch a Fargate task from this box, and doing that isn't a
  read-only check the way the RDS/secret one was. Flagging as untested rather than assuming it
  works the same way.

This confirms the DB-access half of OPEN-193 item 2 is live and working from wherever this
role is attached. Still open: which box the ECS-trigger half of item 2 needs to be verified
from (this box or the actual `ddp-sync` EC2 host), and items 3–4 (real `sync_schedule.yaml`
values, the canary run) from the original request.
