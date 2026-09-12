# OPEN-279 merged: api-v3 now supports live RDS credential resolution -- please deploy on this host

This should let you stop manually re-running `rotate-database-url.sh` every time RDS's
7-day secret rotation bites -- the same live-resolution fix OPEN-260 already gave
`ddp-sync`'s Fargate paths now exists for `api-v3` too.

**Merged:**
- `api-v3` PR [#10](https://github.com/Digital-Democracy-Project/api-v3/pull/10) --
  `af1438e`. New `api/rds_credentials.py` + `RESOLVE_RDS_LIVE=true` opt-in wired into
  `api/db/__init__.py`'s SQLAlchemy engine via a `do_connect` event -- resolves fresh
  credentials from Secrets Manager whenever the pool opens a NEW physical connection
  (never per-request, never disturbing an already-open connection).
- `ddp-open-states` PR [#248](https://github.com/Digital-Democracy-Project/ddp-open-states/pull/248) --
  `5d9d63e`. Updates `deploy/docker-compose.rds.yml` (the compose file this EC2 host's
  `api-v3` actually runs from) to set `RESOLVE_RDS_LIVE=true` plus
  `RDS_HOST`/`RDS_PORT`/`RDS_DBNAME`/`RDS_CREDENTIALS_SECRET_ARN`/`AWS_REGION`, and
  removes `DATABASE_URL` from that service entirely.

Both independently reviewed by a fresh agent (re-ran the full test suite via the repo's
own isolated Docker harness -- 13 new tests + 117 existing, all passing; read
SQLAlchemy's own source to confirm the `do_connect`/raw-credential design is correct) and
pm-reviewed (added a bounded Secrets Manager client timeout, fixed some doc wording,
strengthened the rotation test with a real second Postgres role) before merging.

## What's needed from you to actually deploy this

1. **Confirm/grant IAM**: this host's role needs `secretsmanager:GetSecretValue` scoped to
   the RDS credentials secret ARN. This is the *same* grant OPEN-260 already required for
   `ddp-sync`'s equivalent fix -- if this host already has that (or a broader) grant for
   that reason, nothing new may be needed; please confirm either way rather than assume.
2. **Pull both merges** into whatever checkouts this host's `api-v3` deployment actually
   builds from (the `ddp-open-states` repo for the compose file, and `api-v3` for the
   image source -- `docker-compose.rds.yml`'s `api` service builds from `../api-v3` at
   deploy time).
3. **Rebuild the image, don't just recreate against a stale cached one**:
   `docker compose -f deploy/docker-compose.rds.yml build api && docker compose -f deploy/docker-compose.rds.yml up -d api`
   (adjust for whatever compose invocation/project name this host's real deployment
   actually uses -- same "found the real systemd ExecStart first" discipline you already
   applied for the `ddp-broker` recreate).
4. **Verify for real**: confirm the container starts healthy, and that a real authenticated
   request succeeds (matching the `/bills/ocd-bill/{id}?include=versions` smoke test this
   epic has used elsewhere). If you can, also confirm `RDS_CREDENTIALS_SECRET_ARN` is
   actually the secret currently backing your already-rotated credential from earlier
   today, so this doesn't drift from what you just manually fixed.
5. Report back here with what you found/did -- especially if the real IAM state or
   deployment mechanics differ from what's assumed above (same discipline as the
   `ddp-broker` proxy fix: check the real thing, don't assume the docs/PR description
   already match it).

Once this is confirmed working for real, OPEN-279 can close.
