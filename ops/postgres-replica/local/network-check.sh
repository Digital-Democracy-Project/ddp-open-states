#!/usr/bin/env bash
# OPEN-270: confirm the Mac Studio's real network path to RDS, over its WireGuard peer
# connection -- per PLAN-rds-local-postgres-replication.md §3.3/§7.1, this must be proven with
# a real connection test, never assumed from IAM/ECR access. Read-only, makes no changes.
#
# Usage: ops/postgres-replica/local/network-check.sh
set -euo pipefail

RDS_ENDPOINT="ddp-openstates.cvxdhm1ogxug.us-east-1.rds.amazonaws.com"
RDS_PORT=5432

echo "== DNS resolution =="
resolved_ip="$(dig +short "$RDS_ENDPOINT" | tail -1)"
if [ -z "$resolved_ip" ]; then
  echo "FAIL: could not resolve $RDS_ENDPOINT" >&2
  exit 1
fi
echo "$RDS_ENDPOINT -> $resolved_ip"

echo
echo "== Route =="
# A private (RFC1918) resolved address routed through a utunN interface indicates real VPC
# routing over the WireGuard tunnel, not just public-internet reachability with a permissive
# security group.
route get "$resolved_ip" 2>&1 | grep -E "route to|interface"

echo
echo "== TCP reachability (nc) =="
if nc -zv -w 5 "$RDS_ENDPOINT" "$RDS_PORT" 2>&1; then
  echo "PASS: TCP connect succeeded"
else
  echo "FAIL: TCP connect failed -- check (a) RDS security group inbound rule for the Mac's" >&2
  echo "WireGuard-peer CIDR on port 5432, (b) whether the Mac's WireGuard peer actually routes" >&2
  echo "into the VPC subnet RDS lives in (route alone above does not guarantee this)." >&2
  exit 1
fi

echo
echo "== Postgres wire-protocol reachability =="
# A deliberately-invalid login still proves full TCP+TLS+Postgres-protocol reachability if the
# server responds with a real auth failure rather than a timeout/connection-refused.
python3 -c "
import sys
try:
    import psycopg2
except ImportError:
    print('psycopg2 not installed -- skipping protocol-level check (nc result above still stands)')
    sys.exit(0)
try:
    psycopg2.connect(host='$RDS_ENDPOINT', port=$RDS_PORT, dbname='postgres',
                      user='__network_check_probe__', password='x', connect_timeout=8,
                      sslmode='require')
    print('UNEXPECTED: connection succeeded with a bogus user -- investigate')
except psycopg2.OperationalError as e:
    msg = str(e)
    if 'password authentication failed' in msg or 'role' in msg and 'does not exist' in msg:
        print('PASS: server responded with a real auth failure -- full protocol reachability confirmed')
        print(msg.strip())
    else:
        print('FAIL: unexpected error (may indicate a network issue, not just bad credentials):')
        print(msg.strip())
        sys.exit(1)
"
