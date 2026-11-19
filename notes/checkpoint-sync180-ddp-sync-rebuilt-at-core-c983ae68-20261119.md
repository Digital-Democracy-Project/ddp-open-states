# CHECKPOINT (SYNC-180, request 125fc5e with update 0cfe8e5c3): EC2 ddp-sync rebuilt at core c983ae68; drift check exit 0

Written 16:08 UTC 11-19 (date -u at write time), from the production EC2 host. **The user's words in session (pop-up, stepping away, 05:30 UTC):** pre-approved the ddp-sync rebuild (SYNC-180) "only when nothing is running". No extra Oregon run was approved.

## Gates (16:01 to 16:06 UTC)
- Louisiana's pipeline had just finished (16:00:38, 0 failed; Nebraska 13:10, 0 failed); **ECS: 0 running tasks** at 16:01 and again at 16:06; no os-update, cloud_loader, os-text-extract or os-people process in ddp-sync-ddp-sync-1; the next scheduled run is WA 02:30 UTC. The Nebraska LegBot run is on the Mac (not through EC2's ddp-sync).
- #298: `/opt/ddp-sync` ff-only cb5eade -> **c5641c5** (the #298 merge), clean. **This also brought in #294 SYNC-177, #295 SYNC-178, #296 SYNC-179 and #297 BROKER-537**, which sit under #298's merge. #426: `/opt/ddp-open-states` ff-only 0440ed12a -> **20815be5b** (the #426 merge), clean; its 25 commits touch tools, tests and notes only (**no change to deploy/manifest**, which api-v3 mounts live). `2bb68bf2` is an ancestor (the Utah gate).
- Core: the update names `c983ae68599e94494a94edc23d576b483922302e` (v69, revision 72); api-v3 already runs it.

## Steps
1. Recorded: `DDP_CORE_COMMIT` in the running container: **none**. Running image **ebdb4eaf724c** tagged **ddp-sync:pre-sync180** (rollback). Log gzipped to /home/bitnami/ops/log-archive/ddp-sync-pre-sync180-*.log.gz.
2. **Build** (16:03:04 to 16:06:03, exit 0, 3 min): `DDP_CORE_SHA=c983ae68... docker compose -p ddp-sync -f infrastructure/docker-compose.prod.yml build ddp-sync`; the GitHub token read from /opt/ddp-open-states/.env into the build's environment only (never printed). New image **ddp-sync:prod = 2d5170d7071c**; `/opt/openstates-core/DDP_CORE_COMMIT` in it = c983ae68599e94494a94edc23d576b483922302e (no .git left).
3. **Recreate** (16:06:20): `docker compose -p ddp-sync -f ... up -d --no-deps ddp-sync` from /opt/ddp-sync (the unit's working directory); **healthy at 16:07:27**. Start-up log: `pipeline_locks_cleared_at_startup count=0`, `legbot_session_runs_stopped_at_startup locks=0 runs=0` (SYNC-179: nothing to stop), "Loaded sync config", **"Scheduler started with 22 jobs"**, 0 Tracebacks, 0 errors.
4. **Drift check** `check-core-pin-drift.py --image-core c983ae68... --container ddp-openstates-api-1 --sync-container ddp-sync-ddp-sync-1`: image, api-v3 and ddp-sync loader all **c983ae68599e...**; "OK: the scrapers image and 1 api-v3 container(s) and 1 ddp-sync container(s) all run core c983ae68...". **Exit 0.**

## Two findings for you (nothing changed for either)
1. **The systemd unit will now fail on a plain restart.** `/etc/systemd/system/ddp-sync.service` runs `ExecStartPre=render-env.sh` then **`docker compose ... up -d --build`**. Since #298 the build stops without `DDP_CORE_SHA` and without the GitHub token secret, so a plain `sudo systemctl restart ddp-sync` (what the 11-17 release used) would stop at the build step. The container itself is `restart: unless-stopped`, so a host reboot restarts it without building; but the next operator restart or release needs the variable and the token. Someone should decide the shape (a drop-in with the commit, or a build-free start); I have not touched the unit.
2. **/opt/ddp-open-states/.env is mode 644** (world-readable) and holds GITHUB_PERSONAL_ACCESS_TOKEN (the build reads it from there; /opt/ddp-sync/.env has no such variable). The other .env files on this host are 600. I did not change the mode.

## What waits, per your request
- **Oregon proof:** Oregon's next scheduled run is **Saturday 11-21 12:00 UTC** (with NV). I will report the 931 joint-committee votes linked and the unlinked share then; an extra run needs the user's fresh approval.
- Utah's stored-history steps (`2b0abe4f2`): gate 1 (this rebuild) is met; gate 2 (broker 81cce950) was already met. The user's earlier conditional approvals stand; I run the dry runs next and report before any commit.
- Not done: no scrape, relabel, schedule change, .env change or api-v3 change.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
