# CHECKPOINT (eed0ebfdb step 2, your reply c0f3bfcfd): manifest rollout and ddp-sync rebuild at core 10f32ce0 DONE; api-v3 is the one step left

Written 01:37 UTC 11-20 (date -u at write time), from the production EC2 host. **The user's words in session:** the pre-approval of "the api-v3 and ddp-sync rebuild" (11-19 ~23:40 UTC) and, in a pop-up when you pointed out it was not named, **"Yes, include the manifest rollout"**. Your reply confirmed every fact and said the go is Ramon's.

## One change from the order I gave you: ddp-sync before api-v3 (api-v3 waits for the Nebraska run)
The manifest rollout and ddp-sync both need an idle gate (any ECS task running stops the rollout script; ddp-sync needs nothing running), and the schedule leaves only short gaps (Washington 02:30, USA 03:00, Pennsylvania 04:00 UTC run into about 11:00, Alabama and Georgia 12:00 today). **A gap opened at 01:33 UTC (ECS 0, ddp-sync idle, 57 minutes to the next slot), so I did those two now.** api-v3 has no such gate and I told you I would do it after the Nebraska LegBot run returns (the broker reads EC2's api-v3 when LegBot creates a bill), so **api-v3 is still on c983ae68 and the drift check reports exactly that**, as you said it would.

## Step 1: manifest rollout (01:34 UTC)
Dry run first (4 commits to pull, 17 valid, api copy equal), then `bash deploy/rollout-manifest.sh --host ec2 --ddp-sync-root /opt/ddp-sync`: **exit 0, revision 5c11b40b6 -> 1f7ad7b56** (#430 and #429), "OK: 17 jurisdiction(s) valid", "every list compared agrees", api-v3's copy and the checkout's file **equal, md5 668fe009aa1f57074b40daf6a249598e** in the checkout, the copy and the container (the state list itself did not change), container healthy, `load_on_fargate: true` count 0. api-v3 healthz 200 throughout.

## Step 2 (ddp-sync part), 01:34 to 01:37 UTC
- Gate: **ECS 0** running tasks, no os-update, cloud_loader, os-text-extract or os-people in the container, twice (01:34:16 and 01:35:46).
- Log gzipped (/home/bitnami/ops/log-archive/ddp-sync-pre-open639-*.log.gz); running image **80daf0635635** tagged **ddp-sync:pre-open639** (rollback).
- `/opt/ddp-sync` ff-only d28bda2 -> **4675299**, clean. **`git log --oneline d28bda2..HEAD` shows exactly the six commits** (#300: 26ea897, 7438f71, 544de73, merge 689071f; #301: fcaa3b5, merge 4675299). `task_definition_db: "ddp-scrapers-db"` **2**, `rds_from_task_secret: false` **2**; **both signal switches (broker_scorecard_signal, broker_bill_event_signal) `enabled: false`.**
- Core check: **10f32ce0 contains c983ae68: yes.** **Build** (01:34:29 to 01:35:32, exit 0): `DDP_CORE_SHA=10f32ce08088e544e88d54ec64aa325aea80756f docker compose -p ddp-sync -f infrastructure/docker-compose.prod.yml build ddp-sync` (GitHub token read from /opt/ddp-open-states/.env, mode 600, into the build environment only). New image **ddp-sync:prod = 4574b524130c**; its core record = 10f32ce08088e544e88d54ec64aa325aea80756f.
- **Recreate** (01:35:46): `up -d --no-deps ddp-sync` from /opt/ddp-sync: **healthy at 01:36:52**. Start-up log: `pipeline_locks_cleared_at_startup count=0`, `legbot_session_runs_stopped_at_startup locks=0 runs=0`, **"Scheduler started with 22 jobs"**, 0 Tracebacks, 0 errors. The running container's config has `task_definition_db: "ddp-scrapers-db"` 2 times and `rds_from_task_secret: false` 2 times.
- **Drift check** `--image-core 10f32ce0... --container ddp-openstates-api-1 --sync-container ddp-sync-ddp-sync-1`: image **10f32ce0**, ddp-sync loader **10f32ce0**, api-v3 **c983ae68** -> "DRIFT installed in ddp-openstates-api-1 is c983ae68..." exit 1: **the expected single line, api-v3 only**; it should read exit 0 after the api-v3 step.

## Still to come (approved; each posted)
1. **api-v3 at core 10f32ce0** (checkout stays at 9fba5a6, only DDP_CORE_SHA; tag :pre-open639) after the Nebraska run returns, not between 05:00 and 07:00 UTC; then the drift check should exit 0.
2. **The next archive run's ECS task must come from ddp-scrapers-db:1**, reach RUNNING with the new execution role and exit 0, and the next collection from ddp-scrapers (v71): I read both from ddp-sync's log and ECS (describe-tasks) after tonight's runs (Washington 02:30, USA 03:00, Pennsylvania 04:00 UTC) and post it.
3. The OPEN-554 dry runs after api-v3.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
