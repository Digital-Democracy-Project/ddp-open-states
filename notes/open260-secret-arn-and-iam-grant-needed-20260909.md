# OPEN-260: need the real RDS Secrets Manager ARN + one IAM grant to actually enable this

Three PRs are up fixing today's RDS-credential-rotation incident properly (resolve live from
Secrets Manager at call time, instead of a cached env var that goes stale every 7 days):

- `ddp-sync` [#126](https://github.com/Digital-Democracy-Project/ddp-sync/pull/126)
- `openstates-core` [#43](https://github.com/Digital-Democracy-Project/openstates-core/pull/43)
- `ddp-open-states` [#227](https://github.com/Digital-Democracy-Project/ddp-open-states/pull/227)

All three passed a `/pm-review` round (real correctness fixes applied: client-construction error
handling, dbname URL-encoding, a truthiness bug in the opt-in flag -- see each PR's own comments).
None of them can do anything live yet, though -- they need:

1. **The real ARN of the RDS-managed master secret** -- the one whose rotation caused today's
   incident. I don't have permission to look this up myself (`rds:DescribeDBInstances` denied
   for my `ddp-scraper` credential, confirmed via a real `AccessDeniedException`). You (or the
   prod agent, if its role can already read this) can get it via `aws rds describe-db-instances
   --db-instance-identifier ddp-openstates --query 'DBInstances[0].MasterUserSecret.SecretArn'`.
2. **`secretsmanager:GetSecretValue` granted on `ddp-sync`'s EC2 instance role**, scoped to that
   one secret's ARN -- nothing broader needed.
3. Once both are in place: set `RDS_CREDENTIALS_SECRET_ARN` to that ARN in `ddp-sync`'s own
   process environment (same place `RDS_DATABASE_URL` currently lives).

## What to do with this once it's set up

- Merge order matters for one pair: `openstates-core` #43 before `ddp-open-states` #227 (#227
  imports a module #43 adds -- documented in both PR bodies).
- `ddp-sync` #126's fix is always-on for the two call sites that actually caused today's
  incident (the Fargate archive launch, the scrape-trigger's loader) -- once merged and
  `RDS_CREDENTIALS_SECRET_ARN` is set, those stop depending on `RDS_DATABASE_URL`/`.env` at all.
- `openstates-core`/`ddp-open-states`'s fix is opt-in (`RESOLVE_RDS_LIVE=true`) for the
  `os-text-extract`/`quality_check.py` ad-hoc tooling -- doesn't change default behavior, safe
  to merge independently of the ddp-sync timing.
- This doesn't retroactively fix today's immediate incident (that's already handled on the
  OPEN-192 thread via a manual `.env` re-render) -- this is the permanent fix so it can't recur
  every 7 days going forward.
