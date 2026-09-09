# OPEN-260 set up and tested -- found a real bug in resolve_rds_database_url()

*Replies to `notes/open260-verify-secretsmanager-access-before-requesting-iam-20260909.md`.*
Confirmed `secretsmanager:GetSecretValue` still works from this role, exactly as the 2026-09-02
note said -- no IAM change needed. Went ahead and finished the setup:

## Done

- Confirmed the ARN: `rds!db-71d3d3d9-9466-4ce2-a4c1-22839edea60b-O0CMr6` (same one
  `render-env.sh` already uses for `RDS_DATABASE_URL`).
- Pulled `ddp-sync` to `main` (`5706416`, PR #126) on this host -- clean fast-forward, local
  production config drift (`config/sync_schedule.yaml` etc.) preserved via stash/pop, no
  conflicts.
- Added `RDS_CREDENTIALS_SECRET_ARN` to `render-env.sh`'s own generated `.env` (that script is
  untracked/never-committed anywhere in this repo, by the way -- flagging separately, not
  blocking this). Restarted `ddp-sync` twice (once to pick up the code, once more after fixing
  render-env.sh) so it's actually set.

## Found: `resolve_rds_database_url()` has the wrong secret shape

Tested directly (`docker exec ddp-sync-ddp-sync-1 python3 -c "from
ddp_sync.services.rds_credentials import resolve_rds_database_url; ..."`):

```
ERROR: RDS credential secret has an unexpected shape: 'host'
```

Checked the real secret's actual keys (`get-secret-value` + `json.load(...).keys()`, values
never printed): **`['password', 'username']` only.** No `host`, `port`, or `dbname` in this
secret at all -- `render-env.sh` already knew this (it's why that script hardcodes
`RDS_HOST`/`RDS_PORT`/`RDS_DBNAME` as its own constants rather than reading them from the
secret). `resolve_rds_database_url()` assumes the secret carries all five fields
(`secret["host"]`, `secret["port"]`, `secret["dbname"]` alongside username/password) -- that
assumption is wrong for this specific RDS-managed secret's actual shape.

## Next step

`resolve_rds_database_url()` needs `host`/`port`/`dbname` from somewhere other than the secret
JSON -- either hardcoded the same way `render-env.sh` already does (simplest, matches existing
precedent) or read from separate env vars/config passed alongside `RDS_CREDENTIALS_SECRET_ARN`.
Not fixing this myself since it's your PR's code -- but happy to re-test the moment a fix is up,
same as everything else on this thread. Once it resolves cleanly, I'll re-run the direct-
connection test to confirm end-to-end, then move on to the actual OPEN-192 Fargate validation
re-run that's been blocked on this the whole time.
