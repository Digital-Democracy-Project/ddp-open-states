# read-back of `ddp-scrapers:95` (9e6ef40 step 1, collection half): PASSES, names only. Step 1 is complete.

Ramon pasted the JSON of revision 95 into my session (11-25 ~01:00 UTC). Names only; no value repeated.

- **No `secrets` section.** `environment` names: MEMORY_PREFIX, VA_API_KEY, CONGRESS_GOV_API_KEY, MEMORY_BUCKET. **None of RDS_USERNAME, RDS_PASSWORD, RDS_HOST, RDS_PORT, RDS_DBNAME.**
- Execution role is the older `ddp-scraper-ecs-execution-role` (not the db execution role), so a collection task cannot read the database secret. Task role `ddp-scraper-task-role`. Image tag v93, registered 2026-11-24 23:58:51 UTC, ARM64.
- With the `db:22` read-back (my previous note) and RI's archive starting from db:22 and exiting 0, **step 1 of 9e6ef40 is complete.** The two plain API keys remain on both families (OPEN-880).
- Still before Arizona step 4: #488 merged, the ddp-sync restart (core a7035d68 build, waiting for the Hawaii archive), and Ramon's go for the manifest rollout.
