# OPEN-270: Mac Studio -> RDS network path, confirmed 2026-09-11

`PLAN-rds-local-postgres-replication.md` §3.3 flagged this as the plan's single biggest open
risk: neither half of the required path (a security-group rule for the Mac's WireGuard-peer
traffic, and actual routing from that peer into RDS's VPC subnet) had been confirmed with a
real connection test. Both are now confirmed, from the Mac Studio itself, via
`ops/postgres-replica/local/network-check.sh`.

## Evidence

```
$ ops/postgres-replica/local/network-check.sh

== DNS resolution ==
ddp-openstates.cvxdhm1ogxug.us-east-1.rds.amazonaws.com -> 172.31.97.157

== Route ==
   route to: 172.31.97.157
  interface: utun4

== TCP reachability (nc) ==
Connection to ddp-openstates.cvxdhm1ogxug.us-east-1.rds.amazonaws.com port 5432 [tcp/postgresql] succeeded!
PASS: TCP connect succeeded

== Postgres wire-protocol reachability ==
PASS: server responded with a real auth failure -- full protocol reachability confirmed
connection to server at "ddp-openstates.cvxdhm1ogxug.us-east-1.rds.amazonaws.com" (172.31.97.157), port 5432 failed: FATAL:  password authentication failed for user "__network_check_probe__"
```

**What this proves, matching §4 AC2 exactly ("not assumed from IAM/ECR access"):**

- The RDS endpoint resolves to `172.31.97.157` -- an RFC1918 private address, not a public IP,
  confirming this is the real VPC-internal endpoint, not some public-facing proxy.
- The route to that address goes over `utun4` (the Mac's existing WireGuard tunnel, already up
  and in use for other purposes), not the default internet-facing interface -- this is real VPC
  routing through the tunnel, satisfying §3.3 item 2.
- A raw TCP connect to port 5432 succeeds, satisfying §3.3 item 1 (RDS's security group already
  permits this traffic from the Mac's WireGuard-peer address).
- A deliberately-invalid login attempt gets a real Postgres `FATAL: password authentication
  failed` response, not a timeout or connection-refused -- full TCP+TLS+Postgres-protocol
  reachability, stronger evidence than the plan's own minimum bar (`nc -zv`).

**No IAM/AWS-API access was used or needed for this check** -- it's a plain network-level test
run directly from the Mac Studio, independent of the `ddp-scraper` IAM user's own (confirmed
separately, see below) lack of `rds:*`/`secretsmanager:*` permissions.

## What this does NOT prove (deliberately out of scope for OPEN-270)

- Whether any specific RDS role can actually authenticate and read the 7 tables this plan needs
  -- that's OPEN-271 (roles + publication), which requires RDS admin access this session's own
  IAM identity (`ddp-scraper`, confirmed via `aws sts get-caller-identity` /
  `aws rds describe-db-instances` returning `AccessDenied`, and
  `aws secretsmanager list-secrets` likewise) does not have. That step needs to run through
  whichever identity already has RDS admin access (the prod agent's own established path,
  `resolve_rds_database_url()`), not this session.
- Whether the connection is stable/production-ready under sustained replication load -- this is
  a one-shot reachability check, not a load test.

## Acceptance criterion satisfied

Plan §4, AC2: "Network path from the Mac's WireGuard peer to RDS on port 5432 confirmed with a
real connection test (§3.3, §7.1) -- not assumed from IAM/ECR access." **Done**, per the
evidence above.
