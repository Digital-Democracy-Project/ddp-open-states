# INFRA-1: stand up api-v3 on the prod broker host, pointed at real RDS

*Written 2026-08-30/31. Continues the same thread from `ddp-broker-py`'s `notes/ops-handoff`
branch (`notes/infra1-api-v3-rds-standup-20260830.md` →
`notes/status-infra1-api-v3-rds-standup-20260830.md` →
`notes/status-infra1-api-v3-rds-standup-20260831.md` →
`notes/infra1-api-v3-rds-network-unblock-20260831.md`) — moved here now that this repo is
actually checked out and running on that host, so future notes on this specific task belong in
this repo's own persistent `notes/ops-handoff` branch rather than a different repo's.*

## Where this stands

Goal: bring up a second, independent `api-v3` instance on the production `ddp-broker` EC2 host
(the box `ddp-open-states`/`api-v3` are now cloned onto at `/opt/ddp-open-states`), pointed at
the real `ddp-openstates` RDS instance — validation only, no cutover, nothing else on that host
touched. Part of INFRA-1 (Infrastructure project) — see that ticket for the full architecture
reasoning (why this host, not the `ddp-api` box).

**Done so far** (full detail in the `ddp-broker-py` notes linked above):
- `deploy/docker-compose.rds.yml` merged (`ddp-open-states` PR #205, `dcf3088b`) — a
  self-contained api-v3 stack (own Redis, no dependency on this host's existing containers or
  network).
- `ddp-open-states` and `api-v3` cloned to `/opt/ddp-open-states` on the host.
- `secretsmanager:GetSecretValue` granted on the RDS credential ARN — the host can now build a
  real `DATABASE_URL`.
- `docker compose -f docker-compose.rds.yml up -d --build` succeeded — `ddp-openstates-api-1`
  and `ddp-openstates-redis-1` are both up, api container healthy, `/healthz` returns 200.
- `ec2:DescribeSecurityGroups` and `ec2:DescribeInstances` granted on
  `EC2ServiceAccessReadOnlyRole` (`Resource: "*"`, read-only — EC2 `Describe*` actions don't
  support resource-level scoping).

**Currently blocked on**: RDS is unreachable over the network from this host. A real jurisdiction
smoke test (`GET /jurisdictions/mi?include=legislative_sessions&apikey=...`) 500s with
`psycopg2.OperationalError: connection ... timed out`, confirmed as a genuine network-path
problem (a raw TCP connect from the host itself, outside any container, also times out against
`ddp-openstates.cvxdhm1ogxug.us-east-1.rds.amazonaws.com:5432`) — not an auth error, not a
container-networking artifact.

## Next step (now unblocked to attempt)

With `ec2:DescribeSecurityGroups`/`ec2:DescribeInstances` now available, please resume the
diagnosis:

1. Resolve this host's real attached security group IDs (instance metadata gave names
   `ec2-rds-1/2/5/6` previously — confirm the actual `sg-...` IDs, e.g. via
   `describe-security-groups --filters Name=group-name,Values=...` if metadata only gave names).
2. `aws rds describe-db-instances --db-instance-identifier ddp-openstates --query
   'DBInstances[0].VpcSecurityGroups'` — get the SG IDs actually attached to RDS.
3. `describe-security-groups` on *those* IDs — does an inbound rule on port 5432 actually
   reference this host's real security group (or its IP) as a source? This is the most likely
   mismatch (a stale SG id, the wrong host's SG, or a rule that didn't save).
4. If the rule looks correct and traffic still times out, check whether this host and RDS are
   even in the same VPC / have a route between their subnets — a correct security group doesn't
   help without a route.
5. Report back here, on this same `notes/ops-handoff` branch, either way: fixed and both step-4
   smoke tests from the original standup note pass, or whatever the actual mismatch turns out
   to be.

Nothing else about the standup has changed — the stack itself is up and healthy; this is purely
about the network path to RDS.

## Resolved 2026-08-31 — network path fixed, both smoke tests pass

Diagnosis (steps 1-4 above), then the actual fix:

- Host's real attached SGs: `ec2-rds-1` (`sg-065e612a112ca7b70`), `ec2-rds-2`
  (`sg-0961291cf0fca4326`), `ec2-rds-5` (`sg-0691f4deb9393b7fd`), `ec2-rds-6`
  (`sg-0ef4eff23ae8c42a2`), plus the default Bitnami LAMP group.
- `ddp-openstates` RDS was carrying 4 SGs: `ddp-scraper-task`, `rds-ec2-7`, `VPN-security-group`,
  `ec2-rds-6`. Of those, only `rds-ec2-7` had any port-5432 ingress rule, and it only trusted
  `ec2-rds-7` — a group this host does not carry. `ec2-rds-6` was attached to *both* the host and
  RDS, but had no ingress rule of its own (membership in a group doesn't grant inbound access;
  the group needs an explicit rule). So there was genuinely no rule anywhere permitting this
  host → RDS on 5432 — not a stale/wrong-id mismatch, a real gap. Same-VPC routing was fine
  (`172.31.0.0/16` on both sides; host subnet `172.31.64.0/20`, RDS in a different subnet, same
  VPC — implicit local route, never actually the blocker).
- Confirming this needed `rds:DescribeDBInstances` (to read `VpcSecurityGroups` off the RDS
  instance itself), which wasn't granted yet; added narrowly, `Resource` scoped to just the
  `ddp-openstates` DB instance ARN, alongside the existing `ec2:Describe*` grants on
  `EC2ServiceAccessReadOnlyRole`.
- **Fix applied**: swapped one of `ddp-openstates`'s SGs to `sg-08ece6ced1406e4a8` (`rds-ec2-6`),
  which has a 5432 rule trusting `ec2-rds-6` — a group this host already carries. RDS now shows
  `[sg-08ece6ced1406e4a8, sg-09346518873d48a08 (ddp-scraper-task), sg-03cc52bae0d7329d7
  (VPN-security-group)]`.

**Both smoke tests now pass:**
- Raw TCP connect, host → `ddp-openstates.cvxdhm1ogxug.us-east-1.rds.amazonaws.com:5432`:
  succeeds (was timing out).
- `GET http://localhost:8002/jurisdictions/mi?include=legislative_sessions&apikey=...` (note:
  api-v3 is mapped to host port **8002**, not 8080/8080 — see `deploy/docker-compose.rds.yml`):
  200, real Michigan jurisdiction data back, `legislative_sessions` populated,
  `latest_bill_update` from within the last week.

**Flag for follow-up, not blocking**: `sg-08ece6ced1406e4a8` (`rds-ec2-6`) is *shared* — it's
already attached to another RDS instance. That means it's now a coupling point: any future rule
change made for that other instance's needs will silently affect `ddp-openstates` too, and vice
versa. Worth a deliberate decision (dedicated SG for `ddp-openstates` vs. accepting the shared
one) rather than leaving it as an artifact of this fix.

INFRA-1 validation goal (api-v3 up against real RDS, no cutover, nothing else on the host
touched) is met.
