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
PGPASSWORD="$ROLE_PASSWORD" psql "host=$PGHOST dbname=$PGDATABASE user=ddp_local_replication sslmode=verify-full" -c "
INSERT INTO public.opencivicdata_bill (id) VALUES ('__write_check_probe__');
" 2>&1 | grep -q "permission denied" && echo "PASS: write correctly refused (permission denied)" || {
  echo "FAIL: write was NOT refused -- ddp_local_replication has write access it shouldn't." >&2
  exit 1
}
