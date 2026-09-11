#!/usr/bin/env bash
# OPEN-273 (pm-review round 1): generate and store ddp_local_readonly's password in AWS Secrets
# Manager, matching ops/postgres-replica/rds/00-generate-role-secret.sh's convention for
# ddp_local_replication -- the password never appears in this shell's history or as any command's
# argument (a bare `--secret-string "$PASSWORD"` would put it in this process's own argv, visible
# to anything that can list processes on this box while the command runs -- passed via a private,
# immediately-deleted temp file instead, see below). Run once, by an identity with
# secretsmanager:CreateSecret (the prod agent, same as the RDS-side scripts -- this Mac-side
# session confirmed it lacks this access, see ops/postgres-replica/NETWORK-PATH-CONFIRMED-OPEN-270.md).
set -euo pipefail

SECRET_ID="ddp-openstates/ddp_local_readonly"
REGION="us-east-1"

# Bug fix, found live during OPEN-273's real execution: `create-secret` has no
# `--generate-secret-string` flag at all (confirmed via `aws secretsmanager create-secret help`
# showing no such parameter, on the AWS CLI version installed for this project) -- this script as
# originally written would have failed outright. The correct two-step pattern is to generate the
# password server-side via `get-random-password`, then pass it to `create-secret`.
#
# Correction, found in this fix's own review: an earlier version of this fix passed the password
# as `--secret-string "$RANDOM_PASSWORD"` directly -- that puts the real password in this
# process's own argv, visible via `ps` (etc.) to anything that can list processes on this box
# while the command runs, which is exactly the exposure this script's header comment claims to
# avoid. Fixed by writing it to a private (mode 600), immediately-deleted temp file instead and
# passing `--secret-string file://...`, which AWS CLI reads directly without ever putting the
# content on the command line.
RANDOM_PASSWORD="$(aws secretsmanager get-random-password \
  --region "$REGION" \
  --password-length 32 \
  --exclude-punctuation \
  --query 'RandomPassword' --output text)"

password_file="$(mktemp)"
chmod 600 "$password_file"
trap 'rm -f "$password_file"' EXIT
printf '%s' "$RANDOM_PASSWORD" > "$password_file"

aws secretsmanager create-secret \
  --region "$REGION" \
  --name "$SECRET_ID" \
  --description "OPEN-273: password for the ddp_local_readonly role (the local Postgres replica's read-only consumer role, PLAN-rds-local-postgres-replication.md). Local-side only, SELECT-only, never the subscription-owner credential." \
  --secret-string "file://$password_file"

echo "Secret created at $SECRET_ID -- setup-subscription-and-readonly-role.sh reads this directly."
