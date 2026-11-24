# UPDATE (not a GO) to `f9f1b5f`: **v93 is built and `ddp-scrapers-db:22` carries the stored RDS login.** What is left is your read-back and the first launch. 2026-11-25 ~03:10 UTC (Mac side, Onboard New States)

**Not a GO.** Please confirm each step with Ramon in your session. Revisions come from him via the PM session: **`ddp-scrapers:95`** and **`ddp-scrapers-db:22`**. His build output says: "ddp-scrapers-db: RDS secret entries set (RDS_USERNAME, RDS_PASSWORD, RDS_HOST, RDS_PORT, RDS_DBNAME)", "RDS secret in ddp-scrapers: no", "RDS secret in ddp-scrapers-db: yes".

## What I read on the Mac (the local copy of the image)
* **v93** = `ddp-scrapers@sha256:9883253b2db9…`; `DDP_CORE_COMMIT` = **`a7035d68d1344f99783042e2492ba120d110e603`** (unchanged); `/app/cloud_collector.py` has `apply_rds_task_secret`, and `cloud_archiver.py` and `cloud_loader.py` call it.
* **Both `ddp-scrapers-db:22` and its predecessors still carry the two plain API keys** (OPEN-880 is the cleanup; Ramon rotates them). **Ramon also deletes `/tmp/taskdef-*.json`** on the Mac (the deploy script wrote the task definitions there, with the plain key values).

## What the container does today when BOTH are present (from the code, `cloud_collector.py`)
ddp-sync still passes `DATABASE_URL` at launch for the archive and load tasks (`rds_from_task_secret` is false in the archive block and, until the ddp-sync restart, in the scrape block). The task definition now also injects `RDS_USERNAME`/`RDS_PASSWORD` (secrets) and `RDS_HOST`/`RDS_PORT`/`RDS_DBNAME` (environment). Then:
* **`apply_rds_task_secret()` returns at once** (`if env.get("DATABASE_URL"): return False`): a `DATABASE_URL` the launcher passed **always wins**, and the secret's values are never looked at or used. So **the first archive behaves exactly as today**; the new entries change nothing by themselves.
* **The one place the secret still matters is ECS itself:** ECS reads the secret with the execution role **before the container starts**. If `ddp-scraper-db-execution-role` cannot read it, the task **fails to start** (loudly; an alert), whatever the container would have done. That is the real test of the permission, which was only ever checked with the policy simulator.

## What is left (each on Ramon's go; your side)
1. **Read-back, names only, of `ddp-scrapers-db:22`:** `secrets` lists `RDS_USERNAME`, `RDS_PASSWORD`; `environment` lists `RDS_HOST`, `RDS_PORT`, `RDS_DBNAME`. And **`ddp-scrapers:95` lists none of the five.**
2. **The first task launched from `db:22` (the next archive, in about minutes: the HI and IA archives were already running on `db:20`)** reaches RUNNING and exits 0. **If it fails to start with a secrets or permission error: deregister `db:22` (the previous revision becomes latest again) and tell me.** Look at the archive's task launched **after** `db:22` exists: tasks already running keep their old revision.
3. **The ddp-sync restart with the core rollout at `a7035d68`** (staged, guarded) brings #311's scrape-block `rds_from_task_secret: true` with it. **After that restart, a load on a Fargate-loading state stops getting `DATABASE_URL` from ddp-sync**, but only Arizona would, and only after #488.
4. **The Hawaii people load and second re-import** (on Ramon's go), then **the Arizona canary (#488)** only after step 1 and a clean step 2.
5. Archives and loads keep passing `DATABASE_URL` until the canary; **do not turn on the archive block's `rds_from_task_secret`.**

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
