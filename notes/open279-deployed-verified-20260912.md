# OPEN-279 deployed on this EC2 host and verified for real

Deployed with Ramon's explicit go-ahead, after he reviewed the PRs directly.

**Steps taken:**
1. Fast-forwarded this checkout (`ddp-open-states`) from `bf3025b` to `origin/main`
   (`5d9d63e`) -- checked all 4 intervening commits first; only `5d9d63e` itself touches
   anything this host uses (`deploy/docker-compose.rds.yml`), still pointed at the same real
   `openstates` database, no repoint hidden in there. The others touch the Mac's own
   `docker-compose.ddp.yml` or unrelated `ops/postgres-replica/*` scripts.
2. Fast-forwarded the nested `api-v3` checkout to `af1438e` (PR #10) -- picked up one more
   commit along the way (`5c762ad`, the "unlimited tier" rate-limit fix), which is directly
   relevant since that's the tier `ddp-broker`'s new profile row uses.
3. Added `RDS_CREDENTIALS_SECRET_ARN` to `deploy/.env` -- reused the exact same secret ARN
   already used by `deploy/rotate-database-url.sh` (`rds!db-71d3d3d9-...-O0CMr6`), which is
   also the same ARN `ddp-sync`'s own OPEN-260 fix already reads successfully from this host's
   IAM role. **No new IAM grant was needed** -- confirmed via the prior successful
   `rotate-database-url.sh` run against this exact ARN earlier today, not just assumed.
4. Rebuilt the image for real (`docker compose build api`), not just recreated against the
   stale cached one.
5. Recreated just the `api` service (`--force-recreate --no-deps`), explicitly passing
   `-p ddp-openstates-rds` (this compose file already declares its own `name:` field, so this
   one didn't have the orphan-project risk `ddp-broker`'s did -- confirmed no stray containers
   after recreate).

**Verified for real:**
- Container health: `healthy`.
- `RESOLVE_RDS_LIVE=true`, `RDS_CREDENTIALS_SECRET_ARN`/`RDS_HOST`/`RDS_DBNAME` all present and
  correct in the running container's env.
- A real authenticated `GET /bills?jurisdiction=ut&per_page=1&include=versions` returned `200`
  with a real bill (UT HB 337, 17 versions) -- confirms both the live credential resolution and
  the include=versions path work end to end.
- No errors in the container's logs.

OPEN-279 is done and confirmed working on this host. This should end the "stale RDS
credential after 7-day rotation" incident class for this deployment for good -- a future
stale-credential 500 here would now be a real regression worth flagging, not something to
route around with `rotate-database-url.sh` again.
