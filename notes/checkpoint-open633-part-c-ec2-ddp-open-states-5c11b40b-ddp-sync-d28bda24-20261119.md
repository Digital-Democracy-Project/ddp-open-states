# CHECKPOINT (OPEN-633 release request 9ea0c4aff / 6430322a0): Part C done on EC2; Part A cannot be done from this host

Written 21:41 UTC 11-19 (date -u at write time), from the production EC2 host. **The user's words in session (pop-up):** "Yes, do it now" for Part C. Production behaves as before: no `load_on_fargate` is true anywhere and `rds_from_task_secret` is false.

## Part A (IAM): NOT done, cannot be done from this host
The grant needs an IAM write (`iam:PutRolePolicy` on the scrapers execution role). This host's role is `EC2ServiceAccessReadOnlyRole` and it cannot even read the task definition (`ecs:DescribeTaskDefinition` is denied: "not authorized ... because no identity-based policy allows"), so I did not try, and I do not work around it. **Someone with AWS write access (Ramon, or whoever owns the role) must do Part A.** The values Part A's checkpoint asks for (the secret ARN, `RDS_HOST`, `RDS_PORT`, `RDS_DBNAME`) I will give **to the user directly in the session, not in this note**: I keep secret ARNs out of git notes (hygiene rule). The ARN is the value of `RDS_CREDENTIALS_SECRET_ARN` in the ddp-sync container's environment (and /opt/ddp-open-states/deploy/.env, mode 600).

## Part C gates (21:33 to 21:34 UTC)
ECS **0** running tasks; no os-update, cloud_loader, os-text-extract or os-people in `ddp-sync-ddp-sync-1`; no scheduled job running; the next run is Washington 02:30 UTC. (The Nebraska LegBot run is a call from this host to the Mac; it does not go through EC2's ddp-sync.)

## C.1 ddp-open-states (21:33:55 UTC)
Fast-forward origin/main was fetched over SSH (origin is HTTPS without credentials); a **dry run first** showed every step: the 5 commits (#428 and #427), 17 valid states, api-v3's copy of the list differing (it still lacked the OPEN-555 fields: 242 lines of difference; the checkout's root list differs from the incoming one by 19 lines, only the `load_on_fargate` field). Then `bash deploy/rollout-manifest.sh --host ec2 --ddp-sync-root /opt/ddp-sync`: **exit 0, revision 20815be5b -> 5c11b40b6 (the #428 merge)**, "OK: 17 jurisdiction(s) valid", "every list compared agrees with jurisdictions.yaml (17)", api-v3's copy synced (**md5 668fe009aa1f57074b40daf6a249598e** in the checkout, in the api copy and inside the container), container healthy (directory mount: no recreate needed). Live: az fl ma mi nc us ut va wa; scraping: al ga la ne nm nv or pa. `grep -c 'load_on_fargate: true'` = **0**. Broker read through its own client: /ddp/enrollment **17 jurisdictions, none without chambers**; no enrollment warnings in the web log.

## C.2 ddp-sync (21:34 to 21:36 UTC)
- Log gzipped (/home/bitnami/ops/log-archive/ddp-sync-pre-open633-*.log.gz); running image **2d5170d7071c** tagged **ddp-sync:pre-open633** (rollback). `/opt/ddp-sync` ff-only c5641c5 -> **d28bda2** (the #299 merge, 2 commits; main has since moved to #300 and I did not take it), clean. `rds_from_task_secret: false` appears **2** times in config/sync_schedule.yaml, no `true`.
- **Build** (21:34:27 to 21:35:16, exit 0): `DDP_CORE_SHA=c983ae68599e94494a94edc23d576b483922302e docker compose -p ddp-sync -f infrastructure/docker-compose.prod.yml build ddp-sync`, the GitHub token in the build's environment only. New image **ddp-sync:prod = 80daf0635635**; core record in it c983ae68599e94494a94edc23d576b483922302e; the Fargate load branch is in `pipelines/cloud_scrape_trigger.py`.
- **Recreate** (21:35:36): `up -d --no-deps ddp-sync` from /opt/ddp-sync (not systemctl, per your note): **healthy at 21:36:42**. Start-up log: `pipeline_locks_cleared_at_startup count=0`, `legbot_session_runs_stopped_at_startup locks=0 runs=0`, **"Scheduler started with 22 jobs"**, 0 Tracebacks, 0 errors. The **running** container's config has `rds_from_task_secret: false` twice.
- **Drift check** `check-core-pin-drift.py --image-core c983ae68... --container ddp-openstates-api-1 --sync-container ddp-sync-ddp-sync-1`: all three at c983ae68599e...; "OK: ..."; **exit 0**.

## Owed (not yet seen)
The **next scheduled scrape** is Washington at 02:30 UTC (then US 03:00, PA 04:00). I will read its log and post whether it shows `cloud_scrape: collection done, loading into RDS` and **no** `cloud_scrape: load task started`.
Rollback if ever needed: retag `ddp-sync:pre-open633` as `ddp-sync:prod`, `up -d --no-deps ddp-sync` from /opt/ddp-sync.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
