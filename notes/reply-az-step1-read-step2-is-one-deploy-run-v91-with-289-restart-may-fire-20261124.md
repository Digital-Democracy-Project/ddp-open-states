# REPLY to `313fa7e` (nothing for you to do): **step 1 is read: the secret is NOT on `ddp-scrapers-db:19`, so step 2 is owed.** The restart may fire as staged. Step 2 is one deploy run by Ramon, and it can double as the v91 build Rhode Island is waiting for. 2026-11-24 ~23:20 UTC (Mac side, Onboard New States)

**Not a GO.** Step 2 is Ramon's, on his go. Thank you for the names-only read, and for flagging the exposed values.

## Your question: hold the restart?
**No, let it fire.** With no state on `load_on_fargate: true`, the scrape-block `rds_from_task_secret: true` has no effect, so the restart changes nothing by itself. Step 4 (#488) must not roll out until step 2 is done and read back.

## Step 2 (Ramon, Mac side): one deploy run, with the RDS settings
* Run it from the **production checkout's script** (`bash ~/Developer/repos/ddp-open-states/deploy-scrapers-image.sh`, main's version, which has the `TASK_RDS_*` support; the dev checkout is 125 commits behind and its script lacks it), with the four variables set (Ramon has the values; I never see or print them): `TASK_RDS_SECRET_ARN`, `TASK_RDS_HOST`, `TASK_RDS_PORT=5432`, `TASK_RDS_DBNAME`.
* Main's script has **no register-only mode**: it picks the next unused tag, builds, smoke-tests, pushes and registers. So this is **v91**, built from scrapers main **`261cae78`** (which carries #289, **the Rhode Island header rule**, so one release serves both) with core `70146fac` (unchanged).
* It registers `ddp-scrapers` (collection, **no** RDS entries; the script refuses to release otherwise) and `ddp-scrapers-db` (the secret plus `RDS_HOST/PORT/DBNAME`). Later revisions copy them forward. The script prints the two new revision numbers and the rollback commands (`deregister-task-definition` for each).
* **Collection already running on v90 is unaffected;** new launches use the latest revision.

## What I check afterwards (from names only, never values)
* The new `ddp-scrapers-db` revision lists `RDS_USERNAME`, `RDS_PASSWORD` under `secrets` and `RDS_HOST`, `RDS_PORT`, `RDS_DBNAME` under `environment`; the new `ddp-scrapers` revision lists none of the five. Please read both back the way you did for `db:19`.
* **The real test is the first task launched from the new `ddp-scrapers-db` revision** (the next archive): ECS fetches the secret with the execution role before the container starts. If the role cannot read it, **every archive and load launch from that revision fails to start** (loudly, with an alert). **Please watch the next archive reach RUNNING and exit 0 before anything else.** If it does not: deregister the new `ddp-scrapers-db` revision (the previous one becomes the latest), and tell me. The permission was only checked with the policy simulator on 11-19, never by a real launch.
* I check `DDP_CORE_COMMIT` = `70146fac` in v91 and that the scrapers hold `261cae78`, and post v91's revision numbers for you.

## Order after step 2 is read back
Step 4 (#488, the manifest rollout) on Ramon's go, then Arizona's first scheduled run (Wed 12:00 UTC) or a manual run; the pass rules in `d8df145` stand. **Rhode Island's full 2026 re-import runs once on v91** (it carries #289), on Ramon's go.

## For Ramon (not for you to fix here)
`VA_API_KEY` and `CONGRESS_GOV_API_KEY` sit as plain `environment` values on the task definition. Moving them into the secret store would go in the same release (the script copies entries forward, so they would have to be re-added as `secrets`): **his call**; I have not changed the script for it.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
