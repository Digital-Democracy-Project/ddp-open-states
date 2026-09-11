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

# Fail (not just note) if the resolved address isn't a private RFC1918 address -- pm-review
# round 1 correction: printing the address without checking it doesn't actually verify the
# "this is the real VPC-internal endpoint, not a public one" claim this script exists to make.
if ! python3 -c "
import ipaddress, sys
sys.exit(0 if ipaddress.ip_address('$resolved_ip').is_private else 1)
"; then
  echo "FAIL: $resolved_ip is not a private (RFC1918) address -- this is not the expected" >&2
  echo "VPC-internal RDS endpoint; investigate before trusting anything else this script reports." >&2
  exit 1
fi
echo "PASS: resolved address is private (RFC1918)"

echo
echo "== Route =="
route_output="$(route get "$resolved_ip" 2>&1)"
echo "$route_output" | grep -E "route to|interface"
# Fail (not just print) if the route isn't over a utunN interface -- pm-review round 1
# correction: the prior version accepted any interface, so it could pass over a default
# non-tunnel route and still report success. This checks the INTERFACE NAME PATTERN only
# (utun*, macOS's naming for any point-to-point tunnel, WireGuard included) -- it does not
# independently prove utun4 specifically carries WireGuard traffic rather than some other
# tunnel; if this Mac has more than one active tunnel, confirm manually which one is which
# (e.g. `ifconfig utunN` -- the WireGuard one carries a real point-to-point IPv4 address,
# unlike a link-local-only IPv6 tunnel).
route_iface="$(echo "$route_output" | awk '/interface:/ {print $2}')"
if [[ "$route_iface" != utun* ]]; then
  echo "FAIL: route to $resolved_ip goes over '$route_iface', not a utunN tunnel interface --" >&2
  echo "this would mean the connection below isn't actually going over a WireGuard-style tunnel." >&2
  exit 1
fi
echo "PASS: routed over tunnel interface $route_iface"

echo
echo "== TCP reachability (nc) =="
if nc -zv -w 5 "$RDS_ENDPOINT" "$RDS_PORT" 2>&1; then
  echo "PASS: TCP connect succeeded"
else
  echo "FAIL: TCP connect failed -- check (a) whether RDS's effective network controls (security" >&2
  echo "group or equivalent) permit the Mac's WireGuard-peer traffic on port 5432, (b) whether the" >&2
  echo "Mac's WireGuard peer actually routes into the VPC subnet RDS lives in (the route check" >&2
  echo "above confirms a tunnel interface is used, not that it reaches the right subnet)." >&2
  exit 1
fi

echo
echo "== Postgres wire-protocol reachability =="
# A deliberately-invalid login still proves full TCP+TLS+Postgres-protocol reachability if the
# server responds with a real auth failure rather than a timeout/connection-refused.
#
# Exit code contract (pm-review round 1 correction -- this was ambiguous before): 0 means
# everything through this point passed; 1 means a real failure; 2 means the TCP check above
# already satisfies the plan's own minimum bar (nc -zv) but this stronger protocol-level check
# could not run (psycopg2 missing) -- distinct from a clean pass, not silently folded into one.
set +e  # this next call's exit code is inspected deliberately (0/1/2 all mean something) --
        # `set -e` would abort the script on the 1 and 2 cases before we can read $?.
python3 -c "
import sys
try:
    import psycopg2
except ImportError:
    print('WARN: psycopg2 not installed -- protocol-level check skipped (TCP-level PASS above still stands)')
    sys.exit(2)
try:
    psycopg2.connect(host='$RDS_ENDPOINT', port=$RDS_PORT, dbname='postgres',
                      user='__network_check_probe__', password='x', connect_timeout=8,
                      sslmode='require')
    print('FAIL: connection succeeded with a bogus user -- this is not expected and needs investigating,')
    print('not treated as a pass just because it reached the server.')
    sys.exit(1)
except psycopg2.OperationalError as e:
    msg = str(e)
    if 'password authentication failed' in msg or ('role' in msg and 'does not exist' in msg):
        print('PASS: server responded with a real auth failure -- full protocol reachability confirmed')
        print(msg.strip())
    else:
        print('FAIL: unexpected error (may indicate a network issue, not just bad credentials):')
        print(msg.strip())
        sys.exit(1)
"
protocol_check_status=$?
set -e
if [ "$protocol_check_status" -eq 1 ]; then
  exit 1
fi
exit 0
