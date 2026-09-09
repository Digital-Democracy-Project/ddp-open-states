# Step 3 validation run: task ran, but can't reach RDS at all -- security group gap

*Replies to `notes/v15-built-pushed-taskdef19-registered-20260909.md`.* Launched the
single-jurisdiction `ut` archive validation run against task-definition `ddp-scrapers:19`
(RUN_ID `ut-archive-e2d0ae617ca2`, taskArn ending `...3c399402c48c436187e039ced7ad65d7`).
Real result, not clean: the task itself launched, ran, and exited on its own (not killed,
not a config error) — but never reached RDS.

## What happened

Task went `PENDING → RUNNING → DEPROVISIONING → STOPPED`, exit code 1, `stoppedReason:
"Essential container in task exited"` (ECS's own field, no detail). Pulled the actual
CloudWatch log (`/aws/ecs/ddp-scrapers`, stream `scraper/scraper/<task-id>` — confirmed
`logs:DescribeLogStreams`/`GetLogEvents` still work from this host even without
`DescribeLogGroups`):

```
psycopg2.OperationalError: connection to server at "ddp-openstates.cvxdhm1ogxug.us-east-1.rds.amazonaws.com"
(172.31.97.157), port 5432 failed: Connection timed out
```

Ran for 132 seconds (Django's own connection retry/timeout), then a clean
`ERROR: ut archive failed, exit 1` and a proper completion record — `cloud_archiver.py`'s error
handling itself worked exactly as designed, it's the network path underneath that's broken.

## Root cause, confirmed via `ec2:DescribeSecurityGroups`/`rds:DescribeDBInstances`

RDS (`ddp-openstates`, `PubliclyAccessible: false`) has three security groups attached:
`sg-08ece6ced1406e4a8`, `sg-09346518873d48a08`, `sg-03cc52bae0d7329d7`. Checked all three's
inbound rules:

- `sg-08ece6ced1406e4a8` — the only one with a port-5432 rule at all, and it only allows inbound
  from **`sg-0ef4eff23ae8c42a2`** (a different SG, description says "EC2 instances with
  `sg-0ef4eff23ae8c42a2` attached").
- `sg-09346518873d48a08` — this is `ddp-scraper-task`, the SG the Fargate task actually runs
  with. It's attached directly to the RDS instance, **but has zero inbound rules of its own** —
  being one of RDS's attached SGs doesn't grant it access; something still has to explicitly
  allow traffic *from* it.
- `sg-03cc52bae0d7329d7` — unrelated (SSH/HTTP/HTTPS/WireGuard rules, looks like a general
  admin-access SG).

Nothing anywhere allows `sg-09346518873d48a08` → RDS:5432. This is a real, previously-latent gap:
until `cloud_archiver.py`, no Fargate task ever needed a *direct* database connection to RDS —
collection and loading are separate steps (`cloud_collector.py` doesn't touch the DB; loading
happens via `cloud_loader.py` elsewhere). This is the first Fargate-side code that needs it, and
the security group was never provisioned for it.

## Next step

Needs an inbound rule added to one of RDS's security groups (most naturally
`sg-08ece6ced1406e4a8`, alongside the existing `sg-0ef4eff23ae8c42a2` rule) allowing TCP 5432
from `sg-09346518873d48a08`. Not doing this myself — it's a production RDS network-access change,
same category as the IAM gap from before, needs sign-off. Once it's added, re-run this exact
same validation (same RUN_ID pattern, `ut`, task-def `19`) to confirm the connection actually
succeeds and a document lands in `ddp-bill-archive` at `GLACIER_IR` — that part of Step 3 hasn't
been reached yet.
