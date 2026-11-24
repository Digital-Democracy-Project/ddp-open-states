# UPDATE (not a GO) to `277c191`: **v92 is built (core `a7035d68`, the OPEN-879 fixes) but has NO stored RDS login, so Step 1's secret half is still owed as a further build (v93). The order below changes only in that the core rollout and Hawaii no longer wait for the secret.** 2026-11-25 ~01:10 UTC (Mac side, Onboard New States)

**Not a GO.** Please confirm each step with Ramon in your session. Revisions come from him via the PM session: **`ddp-scrapers:94`** and **`ddp-scrapers-db:21`**; his output says "RDS secret in ddp-scrapers: no" and "RDS secret in ddp-scrapers-db: no" (the `TASK_RDS_*` values were not set again).

## What I read on the Mac (the local copy of the image)
* **v92** = `ddp-scrapers@sha256:9cfcb6fb18d6…`. `DDP_CORE_COMMIT` = **`a7035d68d1344f99783042e2492ba120d110e603`**. The OPEN-879 changes are in it: core #174's before-session-start fallback in `importers/base.py`, scrapers #290's ".." fix in `scrapers/hi/bills.py`, and #289 and the earlier ones. (The image has no scrapers-commit record, so I checked content.)
* **The Mac api-v3 is now on core `a7035d68`** (Ramon ran the refresh; healthy per the PM). **EC2 api-v3 and EC2 ddp-sync have NOT had the core rollout.**

## The order now
1. **Core rollout at `a7035d68…` on EC2** (api-v3, and the ddp-sync rebuild with `DDP_CORE_SHA=a7035d68…`, `DDP_SCRAPERS_SHA=79c25838290d4bfe76880dd960884155e59bffe3`): **no longer waits for the secret.** Rules unchanged from `277c191` Step 2: rollback tags, import check, no run in its load phase and no `ddp-scrapers-db` task up, never 02:15–04:45 UTC (api-v3 not 05:00–07:00). The rebuild replaces the staged `#311` restart.
2. **Hawaii people load** (`c59386b9…`, expect 0 created, 1 updated), then **Hawaii's second re-import** on Ramon's new go, on **v92's revision (94) or later**; the pass lines in `277c191` Step 4 stand. **It needs Step 1 first**: the load runs with ddp-sync's core.
3. **The secret release is a further build, v93,** with the four `TASK_RDS_*` values set (`277c191` Step 1's read-back and first-archive watch apply to it). It is independent of Steps 1 and 2: **core does not change** between v92 and v93 unless something new is merged, so **no second core rollout is needed**. To keep it that way, **please do not merge or roll out any core change before v93** (I have no other core or scrapers PR open; the PM says none is).
4. **The Arizona canary** (`d8df145`, #488) after v93's read-back, as before. OPEN-880 (#490) rides after v93.

## Why not wait for the secret before the core rollout
The core rollout does not touch the task definitions, and Hawaii's fix needs only the new core on the loader. Waiting would delay Hawaii for no reason; doing the secret later as v93 on the same code costs one more build, not a second rollout.

## Not authorized
Any step before its go; a core rollout at any sha other than `a7035d68…`; a third Hawaii run; `rds_from_task_secret: true` in the archive block; the `#310` endpoint.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
