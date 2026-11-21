#!/usr/bin/env bash
# test-compose-ports.sh — AGENTS-251: which address each deploy compose file publishes its ports on, read from
# `docker compose config` (renders the file; starts, builds and connects to nothing).
#
# On the Mac (docker-compose.ddp.yml, and the stopgap rollback file) api-v3 and its Postgres are on 127.0.0.1 only:
# under Colima a 0.0.0.0 publish listens on every interface of the Mac (office network, WireGuard), and everything
# that calls them is on the Mac. The EC2 broker host's file (docker-compose.rds.yml) keeps 0.0.0.0:8002, because
# ddp-api, ddp-sync, the broker and VoteBot reach it over WireGuard as 10.0.0.11:8002.
#
#     bash test-compose-ports.sh      (needs docker with the compose plugin, python3)

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PASS=0
FAIL=0

check() {
    local desc="$1" expected="$2" actual="$3"
    if [ "$expected" = "$actual" ]; then
        PASS=$((PASS + 1)); echo "  ok   $desc"
    else
        FAIL=$((FAIL + 1)); echo "  FAIL $desc"; echo "       expected: $expected"; echo "       actual:   $actual"
    fi
}

# ports <compose file>: one "service host_ip:published->target" per published port, sorted, on one line
ports() {
    docker compose -f "$SCRIPT_DIR/deploy/$1" config --format json 2>/dev/null | python3 -c '
import json, sys
rows = sorted("%s %s:%s->%s" % (name, p.get("host_ip") or "*", p.get("published"), p["target"])
              for name, svc in json.load(sys.stdin)["services"].items() for p in svc.get("ports", []))
print(" | ".join(rows) or "(no config)")'
}

check "the Mac's stack publishes api-v3 and its Postgres on 127.0.0.1 only" \
    "api 127.0.0.1:8002->80 | postgres 127.0.0.1:5433->5432" "$(ports docker-compose.ddp.yml)"
check "the Mac's stopgap rollback publishes api-v3 on 127.0.0.1 only" \
    "api 127.0.0.1:8002->80" "$(ports docker-compose.stopgap.yml)"
check "the EC2 broker host's api-v3 stays on every interface (its callers come over WireGuard)" \
    "api *:8002->80" "$(ports docker-compose.rds.yml | sed 's/0\.0\.0\.0:/*:/')"

echo "$PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
