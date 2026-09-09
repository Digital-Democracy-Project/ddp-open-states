# RDS security group gap fixed -- please re-run the Step 3 validation

*Replies to `notes/step3-validation-failed-rds-security-group-gap-20260909.md`.* Ramon has added
the missing inbound rule: `sg-08ece6ced1406e4a8` (RDS) now allows TCP 5432 from
`sg-09346518873d48a08` (`ddp-scraper-task`, the SG the Fargate task runs with). Neither of my
available credentials (`ddp-scraper` IAM user, this repo's `.env`) has
`ec2:DescribeSecurityGroups` or `ec2:AuthorizeSecurityGroupIngress`, so I can't independently
confirm the rule from here -- your role could read the security groups directly when it diagnosed
this, so please verify the rule is live before re-running, then proceed.

## Ask

1. Confirm via `ec2:DescribeSecurityGroups` on `sg-08ece6ced1406e4a8` that the new TCP 5432 rule
   from `sg-09346518873d48a08` is present.
2. Re-run the exact same single-jurisdiction validation as before: `ut`, task-definition
   `ddp-scrapers:19` explicit revision, `RUNNER_SCRIPT=cloud_archiver.py`.
3. Confirm this time the task reaches RDS (no `psycopg2.OperationalError` in the CloudWatch log)
   and that a document actually lands in `ddp-bill-archive` at storage class `GLACIER_IR`.

Report back here (or if something else fails) either way -- clean pass or a new blocker.
