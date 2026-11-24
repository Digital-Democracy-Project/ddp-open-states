# AZ canary step 1 RESULT (d8df145): `ddp-scrapers-db:19` has NO stored RDS secret; step 2 is owed

Ramon pasted the JSON of `ddp-scrapers-db` revision 19 from the AWS console into my session (11-24 ~22:40 UTC). I report names only; I do not repeat any value.

- Revision 19, registered 2026-11-24 21:15:17 UTC, image tag v90 (ddp-scrapers:v90), ARM64, cpu 1024, memory 2048, FARGATE.
- **`secrets`: absent** (no such section). **`environment` names: MEMORY_PREFIX, VA_API_KEY, CONGRESS_GOV_API_KEY, MEMORY_BUCKET.** None of RDS_USERNAME, RDS_PASSWORD, RDS_HOST, RDS_PORT, RDS_DBNAME.
- Roles: executionRoleArn is the `ddp-scraper-db-execution-role` (the permission half Ramon created on 11-19/20), taskRole `ddp-scraper-task-role`.
- I did **not** see `ddp-scrapers` (the collection definition); the paste was only the db one.
- **So, per your reading rule: the release with TASK_RDS_* is still owed (your step 2, a Mac-side deploy by Ramon).** Until then step 4 (`load_on_fargate: true` for az) must not roll out: the load task would refuse for the missing variables.
- **For Ramon, not for you to fix here:** VA_API_KEY and CONGRESS_GOV_API_KEY sit as plain `environment` values on the task definition (readable with ECS describe access), and the whole JSON is now in my session transcript. I told him to treat both as exposed; rotating or moving them into the secret store is his call. If your next image release changes how these are set, that is the moment.
- My step 3 (ddp-sync pulled to #311, guarded restart, scrape-block `rds_from_task_secret: true`) is staged and still changes nothing by itself. Say if you would rather I hold the restart until step 2 is done; otherwise it fires when no run is loading.
