#!/usr/bin/env bash
# OPEN-273 (pm-review round 1): generate and store ddp_local_readonly's password in AWS Secrets
# Manager, matching ops/postgres-replica/rds/00-generate-role-secret.sh's convention for
# ddp_local_replication -- the password never appears in this script, a shell argument, shell
# history, or any file. Run once, by an identity with secretsmanager:CreateSecret (the prod agent,
# same as the RDS-side scripts -- this Mac-side session confirmed it lacks this access, see
# ops/postgres-replica/NETWORK-PATH-CONFIRMED-OPEN-270.md).
set -euo pipefail

SECRET_ID="ddp-openstates/ddp_local_readonly"
REGION="us-east-1"

aws secretsmanager create-secret \
  --region "$REGION" \
  --name "$SECRET_ID" \
  --description "OPEN-273: password for the ddp_local_readonly role (the local Postgres replica's read-only consumer role, PLAN-rds-local-postgres-replication.md). Local-side only, SELECT-only, never the subscription-owner credential." \
  --generate-secret-string '{"PasswordLength": 32, "ExcludePunctuation": true, "ExcludeUppercase": false}'

echo "Secret created at $SECRET_ID -- setup-subscription-and-readonly-role.sh reads this directly."
