# GO: rebuild EC2 api-v3 at core `71fd44d6` (v64 = `ddp-scrapers:67`), step 4 of `1dc37e5`. 2026-11-17 (Mac side)

**Ramon, 2026-11-17 12:57 EST (Slack DM, read by this session):** "Go on the api-v3 rebuild. Once it's done on the Mac, send the prod agent the request to do the same".

## The Mac is done (18:02 UTC)
* `SCRAPERS_IMAGE=…/ddp-scrapers:v64 ./refresh-api-v3.sh`, from the Mac checkout at ddp-open-states main `643f73d`, which includes #406's build step.
* The build's `import api.main` step passed. Only the `api` container was recreated; the Postgres container is untouched (start time unchanged).
* `/healthz` returns 200.
* `check-core-pin-drift.py`: "OK: the scrapers image and 1 api-v3 container(s) all run core 71fd44d61ce7f116a23933e29fbe9ea01372a99c".

## Steps on EC2
**Before:**
* No api-v3 restart during the broker's scorecard chain (05:00 to about 07:00 UTC): its calls to api-v3 retry only briefly.
* Note the time and confirm `/healthz` returns 200.

**Steps:**
1. Bring `/opt/ddp-open-states` to main at or after `22b6a00` (#406, the build-time import check), `--ff-only`. Report the commit.
2. Tag the running api image `ddp-openstates-api:pre-v64` for rollback, and report its image id.
3. Build: `DDP_CORE_SHA=71fd44d61ce7f116a23933e29fbe9ea01372a99c docker-compose -f /opt/ddp-open-states/deploy/docker-compose.rds.yml build api`.
   * **If the import step fails** (`ModuleNotFoundError` or `ImportError`), stop: the running container is untouched. Report the error.
4. `docker-compose -f /opt/ddp-open-states/deploy/docker-compose.rds.yml up -d --no-deps api`. Recreate `api` only.

**Gates:**
* `/healthz` returns 200.
* `python3 check-core-pin-drift.py --image-core 71fd44d61ce7f116a23933e29fbe9ea01372a99c --container ddp-openstates-api-1` exits **0**. This closes the one expected disagreement from `1dc37e5`.
* `/ddp/enrollment`, read from the broker's web container, returns 200 with 16 jurisdictions.
* Broker web and celery logs for the next 5 minutes show no Traceback.

**Rollback:** retag `ddp-openstates-api:pre-v64` as `:local` and recreate `api` only, as before.

## Report
The checkout commit, the rollback tag and its image id, the build's import-step line, the down time, `/healthz`, the drift check's output and exit code, enrollment, the log check, and the time.

## Not authorized
Any scrapers image, task definition, manifest, broker, ddp-sync or data change.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
