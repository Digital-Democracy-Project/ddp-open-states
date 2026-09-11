#!/usr/bin/env bash
# OPEN-271: confirm the new ddp_local_replication role can actually connect and read the 7
# tables -- catalog checks (02-setup.sh) prove the role/grants/publication exist, not that the
# role can really authenticate and SELECT. Correction from pm-review round 1: this step was
# missing before.
#
# Usage: PGHOST=<rds-endpoint> PGDATABASE=<database_name> ./03-verify-role-can-read.sh
set -euo pipefail

SECRET_ID="ddp-openstates/ddp_local_replication"
REGION="us-east-1"

: "${PGHOST:?Set PGHOST to the RDS endpoint}"
: "${PGDATABASE:?Set PGDATABASE to the real database name}"

ROLE_PASSWORD="$(aws secretsmanager get-secret-value --region "$REGION" --secret-id "$SECRET_ID" --query 'SecretString' --output text)"

PGPASSWORD="$ROLE_PASSWORD" psql "host=$PGHOST dbname=$PGDATABASE user=ddp_local_replication sslmode=verify-full" -c "
SELECT
  (SELECT count(*) FROM public.opencivicdata_bill) AS bill,
  (SELECT count(*) FROM public.opencivicdata_legislativesession) AS legislativesession,
  (SELECT count(*) FROM public.opencivicdata_jurisdiction) AS jurisdiction,
  (SELECT count(*) FROM public.opencivicdata_organization) AS organization,
  (SELECT count(*) FROM public.opencivicdata_billversion) AS billversion,
  (SELECT count(*) FROM public.opencivicdata_billversionlink) AS billversionlink,
  (SELECT count(*) FROM public.ddp_bill_version_document) AS bill_version_document;
"
echo "PASS if all 7 counts above returned a real number (not a permission-denied error)."

# Also confirm the role genuinely cannot write -- it should have SELECT only.
#
# Found by actually running the equivalent check in OPEN-273's local loopback test: with
# `set -o pipefail` active, psql's own non-zero exit (expected here, since the INSERT should
# fail) becomes the pipeline's reported exit status even when grep DOES find "permission denied"
# in the output -- pipefail reports the rightmost command that failed, which is psql, not grep,
# even though grep itself succeeded. That made the old `... | grep -q ... && ... || ...` version
# of this check report FAIL even when the write was correctly refused. Capture output into a
# variable first, then grep on the variable, to sidestep this entirely.
write_check_output="$(PGPASSWORD="$ROLE_PASSWORD" psql "host=$PGHOST dbname=$PGDATABASE user=ddp_local_replication sslmode=verify-full" -c "
INSERT INTO public.opencivicdata_bill (id) VALUES ('__write_check_probe__');
" 2>&1 || true)"
if echo "$write_check_output" | grep -q "permission denied"; then
  echo "PASS: write correctly refused (permission denied)"
else
  echo "FAIL: write was NOT refused -- ddp_local_replication has write access it shouldn't." >&2
  echo "Actual output: $write_check_output" >&2
  exit 1
fi
