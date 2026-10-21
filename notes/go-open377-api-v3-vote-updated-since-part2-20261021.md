# GO from Ramon: OPEN-377 Part 2 (deploy api-v3 `a2f5db8` on the EC2-broker host). (Mac side, 2026-10-21 EDT)

Ramon read your Part 1 reply (`reply-open377-api-v3-preflight-part1-done-20261021.md`, commit `5e91cb7`) and said GO for **Part 2** of `request-open377-api-v3-vote-updated-since-part1-now-deploy-HOLD-until-ramon-says-go-20261020.md` (commit `13db0e3`). That request's Part 2 is the procedure; this note starts it and adds the conditions below. A HOLD note from Ramon on this branch overrides this one. (Thanks for catching the `92d107c` typo.)

## What is authorized

**Part 2 as written**, on this host only, api-v3 only:
1. **Just before starting:** quiet check again (`ddp-openstates-api-1` healthy, only `/healthz` in the last 5 minutes, no ddp-sync job starting inside the next 10 minutes), and `git status --short` clean with HEAD still `ba0b646` in `/opt/ddp-open-states/api-v3`. Anything different: stop and report.
2. Tag the running image `ddp-openstates-api:pre-open377` (the rollback). `git pull --ff-only` to **`a2f5db8`** (expect exactly PR #32's three commits). Rebuild with `docker compose -p ddp-openstates-rds -f docker-compose.rds.yml build api` and recreate **only** `api` (`up -d --no-deps api`) from `/opt/ddp-open-states/deploy`. No other container, no database.
3. **Verify (all of it, from inside the ddp-sync container with its api-v3 key):**
   * `/healthz` 200, container healthy, **restarts 0**, ddp-sync healthy, **0** `apikey=` lines and no 5xx in api-v3's log.
   * **The equality check** against RDS (your G4 numbers): `GET /bills?jurisdiction=<J>&per_page=1&vote_updated_since=<cutoff>%2B00:00`, `total_items` must be: cutoff `2026-06-01T00:00:00` **Utah 739, Virginia 2,201**; cutoff `2026-08-01T00:00:00` **Utah 0, Virginia 6**; cutoff `2026-06-20T00:00:00` **Utah 5, Virginia 2,201**. If a number differs because RDS changed since Part 1, re-run the G4 SQL and compare to that, and say so.
   * `vote_updated_since=2099-01-01T00:00:00%2B00:00` returns **0**; the `...T00:00:00Z` form and a garbage date (`not-a-date`) return **400** (like `document_updated_since` already does); no offset (`2026-06-01T00:00:00`) gives the same answer as `+00:00`.
   * **Nothing else moved:** Utah unfiltered `total_items` still **1,021**; `document_updated_since=2099` still **0**; one existing bill read (`GET /bills/ocd-bill/<an id from your OPEN-361 checks>?include=versions`) returns the same `versions[].note` order as before.

## Window

**Not between about 04:55 and 05:30 UTC today** (the Virginia and Washington archives read api-v3 from 05:00). Any time after that today is fine, and before the next ddp-sync job at **2026-10-22 00:30 UTC**. The recreate is about 17 s; a broker search in those seconds can come back `partial`, which is expected, not an error.

## Stop conditions

A gate or number that does not match, restarts above 0, a 5xx, an error in the new container's log, or an unexpected change in the existing-bill read: **stop and report**. Do not retry the build in a loop. Rollback, only on Ramon's say-so or if the container will not come up healthy: `docker tag ddp-openstates-api:pre-open377 ddp-openstates-api:local`, `up -d --no-deps api`, and `git checkout ba0b646` in the checkout.

## Not authorized

Any other container, the database, ddp-sync, ddp-api or the broker; any flag, schedule, scrape, archive, embedding or LegBot run; changing `DDP_OPENSTATES_API_ROOT`, `OPENSTATES_SERVICE_URL` or any environment setting; the saved `RDS_DATABASE_URL` problem you found (a separate matter); the broker's BROKER-241 work.

## Reply

One `reply-open377-api-v3-deployed-...` note: the quiet check, the commit and image id before and after, the times (tag, pull, build, recreate, healthy), every number above with what it was expected to be, the log checks, and anything unexpected.
