# RDS_CREDENTIALS_SECRET_ARN: can't discover it independently from the Mac, need you to send the real value

Checked `ddp-sync`'s own code first: `RDS_CREDENTIALS_SECRET_ARN` (`services/
rds_credentials.py`) is genuinely unset on the Mac -- not in `.env`, no fallback. Traced
where the value would come from: `infra/rds/outputs.tf`'s `master_user_secret_arn` output
reads `aws_db_instance.openstates.master_user_secret[0].secret_arn` -- AWS's own
auto-managed RDS master secret, not a fixed/predictable name (typically `rds!db-<uuid>`),
so I can't just guess the string.

Tried to look it up independently rather than just ask: `ddp-scraper` IAM (the Mac's only
AWS credential) has neither `secretsmanager:ListSecrets` nor `rds:DescribeDBInstances` --
both came back `AccessDenied` when I tried. Also checked every past `notes/ops-handoff`
commit for this ARN ever being recorded -- nothing.

Since there's only one RDS instance for this whole project, your `render-env.sh` value
(written for OPEN-260, a different purpose) has to be the same secret -- there's no other
RDS master credential it could be. Can you send me the actual ARN string? I'll set
`RDS_CREDENTIALS_SECRET_ARN` in the Mac's `ddp-sync/.env` and get Ramon to kickstart the
process once you confirm it.
