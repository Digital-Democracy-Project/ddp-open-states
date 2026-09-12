#!/usr/bin/env bash
# OPEN-193: re-renders deploy/.env's DATABASE_URL from the current RDS master secret.
# One-off/idempotent -- rerun any time the secret rotates. Never prints the value.
#
# NOT the steady-state mechanism as of OPEN-279: docker-compose.rds.yml's api-v3 no longer
# reads DATABASE_URL at all -- it resolves the credential live from Secrets Manager at
# connection time instead (RESOLVE_RDS_LIVE=true, api/rds_credentials.py), so it never goes
# stale between rotations and this script never needs to be rerun for that deployment. Kept
# as a manual break-glass tool only -- e.g. rendering a one-off DATABASE_URL to `psql` into
# RDS by hand for debugging -- not as something any deployment's steady-state config depends
# on. If you're reaching for this to "fix" a stale api-v3 credential, that's a sign
# RESOLVE_RDS_LIVE isn't actually enabled/working for that deployment, not a reason to rerun
# this instead of finding out why.
set -euo pipefail

RDS_SECRET_ID="arn:aws:secretsmanager:us-east-1:350941939790:secret:rds!db-71d3d3d9-9466-4ce2-a4c1-22839edea60b-O0CMr6"
OUT_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.env"

echo "[rotate-database-url] fetching current RDS master credential..."
RDS_JSON=$(aws secretsmanager get-secret-value --region us-east-1 --secret-id "$RDS_SECRET_ID" --query 'SecretString' --output text)
export RDS_JSON

python3 - "$OUT_FILE" <<'PYEOF'
import json, os, sys, urllib.parse

out_file = sys.argv[1]
d = json.loads(os.environ["RDS_JSON"])
user = d["username"]
password = urllib.parse.quote(d["password"], safe="")
url = f"postgresql://{user}:{password}@ddp-openstates.cvxdhm1ogxug.us-east-1.rds.amazonaws.com:5432/openstates"

with open(out_file, "w") as f:
    f.write(f"DATABASE_URL={url}\n")
os.chmod(out_file, 0o600)
print(f"[rotate-database-url] wrote DATABASE_URL ({len(url)} chars) to {out_file}")
PYEOF

unset RDS_JSON
