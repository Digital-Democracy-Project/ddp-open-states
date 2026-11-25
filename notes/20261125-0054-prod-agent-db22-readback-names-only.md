# read-back of `ddp-scrapers-db:22` (9e6ef40 step 1): PASSES, names only. `ddp-scrapers:95` still to read.

Ramon pasted the JSON of revision 22 into my session (11-25 ~00:55 UTC). I report names only; no value is repeated.

- `secrets`: **RDS_USERNAME** and **RDS_PASSWORD** (each a `valueFrom` into the RDS secret by JSON key, `username` and `password`).
- `environment` names: **RDS_HOST, RDS_DBNAME, RDS_PORT**, plus MEMORY_BUCKET, MEMORY_PREFIX, VA_API_KEY and CONGRESS_GOV_API_KEY. The two API keys are still **plain `environment` values** (as you said; OPEN-880 is the cleanup).
- Image tag v93; execution role is the `ddp-scraper-db-execution-role`; task role `ddp-scraper-task-role`; registered 2026-11-24 23:58:51 UTC; ARM64; the revision carries the `ecs.capability.secrets.asm.environment-variables` requirement ECS adds for secrets.
- Together with RI's archive launching from this revision and exiting 0 (my earlier note), that settles the db half of step 1.
- **Not yet read: `ddp-scrapers:95`** (it must list none of the five). I asked Ramon for yes or no per name without pasting the JSON (the pastes carry the plain API key values, which are now in my session twice; he treats them as exposed).
