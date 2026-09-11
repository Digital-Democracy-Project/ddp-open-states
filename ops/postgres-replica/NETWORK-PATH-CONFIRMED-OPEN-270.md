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
PASS: resolved address is private (RFC1918)

== Route ==
   route to: 172.31.97.157
  interface: utun4
PASS: routed over tunnel interface utun4

== TCP reachability (nc) ==
Connection to ddp-openstates.cvxdhm1ogxug.us-east-1.rds.amazonaws.com port 5432 [tcp/postgresql] succeeded!
PASS: TCP connect succeeded

== Postgres wire-protocol reachability ==
PASS: server responded with a real auth failure -- full protocol reachability confirmed
connection to server at "ddp-openstates.cvxdhm1ogxug.us-east-1.rds.amazonaws.com" (172.31.97.157), port 5432 failed: FATAL:  password authentication failed for user "__network_check_probe__"
```

**Correction from pm-review round 1**: the first version of this script printed the resolved
address and route interface without actually checking either one, so a passing run didn't prove
what the doc claimed. The script now fails closed on both: it exits non-zero if the resolved
address isn't a private (RFC1918) address, and exits non-zero if the route isn't over a `utun*`
interface. It also fixed a real bug where an unexpected successful login with bogus credentials
was logged as `UNEXPECTED` but still let the script exit 0 -- that path now fails loudly instead.

**What this proves, matching §4 AC2 exactly ("not assumed from IAM/ECR access"):**

- The RDS endpoint resolves to `172.31.97.157` -- an RFC1918 private address, not a public IP.
  The script now enforces this rather than just printing it, so this claim is actually checked,
  not just observed once. This rules out the endpoint being some public-facing proxy; it does
  not by itself identify the VPC or account it belongs to, which the endpoint hostname
  (`ddp-openstates...rds.amazonaws.com`, matching the hostname already used elsewhere in this
  repo for the real production RDS instance) already establishes.
- The route to that address goes over `utun4`, a `utun*`-pattern tunnel interface (macOS's
  naming for any point-to-point tunnel, WireGuard included) -- the script now enforces the
  interface *pattern*, not just prints whatever it finds. It does **not** independently prove
  `utun4` specifically carries WireGuard traffic rather than some other active tunnel on this
  Mac; corroborating evidence for that specific identification: `utun4` is the only tunnel
  interface with a real point-to-point IPv4 address assigned (`10.0.0.8 --> 10.0.0.8`) -- the
  Mac's other `utun0`-`utun3` interfaces carry only link-local IPv6, the shape of a
  non-WireGuard system tunnel (e.g. Private Relay), not a routed VPN peer.
- A raw TCP connect to port 5432 succeeds -- this shows RDS's effective network controls
  (security group or equivalent) permit the connection from wherever this traffic is sourced;
  it does not independently identify which specific security-group rule admitted it, only that
  the end-to-end effect is "reachable."
- A deliberately-invalid login attempt gets a real Postgres `FATAL: password authentication
  failed` response, not a timeout or connection-refused -- full TCP+TLS+Postgres-protocol
  reachability, stronger evidence than the plan's own minimum bar (`nc -zv`). The script also
  now fails loudly (rather than silently passing) if a bogus login unexpectedly succeeds.

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
