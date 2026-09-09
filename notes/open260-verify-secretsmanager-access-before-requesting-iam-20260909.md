# OPEN-260: check whether the IAM grant this needs already exists before requesting a new one

*Follow-up to `notes/open260-secret-arn-and-iam-grant-needed-20260909.md`.* Found something that
might make this simpler: `notes/open193-rds-secretsmanager-access-verified-20260902.md` (2026-09-02)
already confirmed `secretsmanager:GetSecretValue` working on the RDS-managed secret's exact ARN,
from `EC2ServiceAccessReadOnlyRole` -- and `notes/open193-same-ec2-host-confirmed-20260902.md`
confirms that's the same role `ddp-sync` itself runs under, on the same box. So the permission
OPEN-260 needs may already exist -- it's just never been *called*, since every consumer up to
now read a cached `.env` value instead of hitting the API live.

That was a week ago, though, so please confirm it's still true rather than trust it, and get the
real ARN while you're at it (needed either way):

## Please run, from the ddp-sync host

1. Get the ARN:
   ```
   aws rds describe-db-instances --region us-east-1 \
     --db-instance-identifier ddp-openstates \
     --query 'DBInstances[0].MasterUserSecret.SecretArn' --output text
   ```
2. Confirm read access with that exact ARN:
   ```
   aws secretsmanager get-secret-value --region us-east-1 --secret-id <ARN> --query SecretString --output text
   ```
   (Don't print/log the actual SecretString anywhere persistent -- same discretion as the
   2026-09-02 note used.)

## Depending on what that shows

- **Works:** no IAM change needed at all. Set `RDS_CREDENTIALS_SECRET_ARN` to that ARN in
  `ddp-sync`'s real environment (same place `RDS_DATABASE_URL` lives today -- `.env` +
  `render-env.sh`, per earlier notes), restart the `ddp-sync` container so `services/
  rds_credentials.py` (now merged, PR #126) picks it up, then re-run the same direct-connection
  test from `notes/confirmed-stale-credential-not-fargate-plumbing-20260909.md` to prove the new
  path actually resolves a fresh credential. That also clears OPEN-260's "verify against a real
  rotation" acceptance criterion.
- **`AccessDenied`:** report that back here -- don't attach a new IAM policy statement yourself,
  same as the earlier security-group changes; Ramon can add the one-line
  `secretsmanager:GetSecretValue` statement (scoped to that exact ARN) once we know it's
  genuinely needed.
