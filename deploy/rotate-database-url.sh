#!/usr/bin/env bash
# OPEN-193: re-renders deploy/.env's DATABASE_URL from the current RDS master secret.
# One-off/idempotent -- rerun any time the secret rotates. Never prints the value.
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
