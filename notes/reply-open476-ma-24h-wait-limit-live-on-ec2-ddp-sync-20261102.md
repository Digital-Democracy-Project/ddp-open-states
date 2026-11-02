# Reply: OPEN-476, the 24-hour Massachusetts wait limit is LIVE on the EC2 ddp-sync host, 2026-11-02 00:36 UTC

Operator said go in this session ("Option A, run the gates now and restart at 00:35"). Nothing rolled back; no scrape launched or re-run; no change to the 11-08 schedule or the task definition.

1. **Commit now running:** **`476d6d4`** (`git pull --ff-only` from `32462f9`; two commits, four files; `/opt/ddp-sync` clean). **ddp-sync restarted 2026-11-02 00:36:01 UTC** (`sudo systemctl restart ddp-sync`, returned after 44 s), **healthy at 00:37:06**, restarts 0, `systemctl is-active` = active, health endpoint healthy (scheduler running, redis connected). Only the ddp-sync container was recreated: the broker, api-v3, VoteBot and Redis containers kept their uptimes.
2. **Live config read first:** before the pull the live `config/sync_schedule.yaml` was **byte-identical to the committed `32462f9` version** (`git diff` empty, no uncommitted file), so there was no hand edit to preserve and the pull applied your change as written.
3. **The live scrape `cloud_path.fargate` block as it reads now** (cluster, task definition, subnets, security group, container name, memory bucket and prefix unchanged and not repeated here):
   - `max_wait_seconds: 43200`   # 12 h for every state not named below
   - `max_wait_seconds_by_jurisdiction:` with `ma: 86400` (24 h)
   - `load_timeout_seconds: 7200` (unchanged)
   - The **archive block's own `max_wait_seconds: 43200` is untouched** (line 820).
4. **Started cleanly:** no `Traceback`, `ERROR` or error-level line in the startup log; the config file is bind-mounted into the container (`/opt/ddp-sync/config` to `/app/config`) and **identical (same sha256) inside and outside**.
5. **What the running code will use (asked of the loaded code, read-only, no job started):** `_fargate_config(config, jurisdiction)` returns **`ma` 86,400 s (24 h)** and **43,200 s (12 h) for wa, va, fl, usa, mi, ut, az and nc**. So the per-state key is read and the other states are unchanged.
6. **In flight at the restart:** nothing. The in-flight Fargate record was 0, no ddp-sync job lines in the 10 minutes before, no Mac writes in 3 minutes, and the newest scraper stream was last Sunday's MA task (11-01 14:00:54). The 00:30 cadence review had finished at 00:30:00 (`changed=0`), so I waited and restarted at 00:36.
7. **Scheduler:** **19 jobs**, the same count as before; the five I looked at keep their times (cadence review next 00:30 on the next night, WA 02:30, USA 03:00, people pull 03:00, drift check 06:20). My first in-container check of the job-list file used a host path by mistake and failed; I compared the counts and the five named jobs instead.
8. **Rollback point:** commit `32462f9` and the previous image tagged `ddp-sync:pre-open476` (`dca536879f5e`); the old container's log is gzipped at `/home/bitnami/ops/log-archive/ddp-sync-pre-476d6d4-20261102T0035Z.log.gz`. Rollback: `git checkout 32462f9` in `/opt/ddp-sync` and `sudo systemctl restart ddp-sync`.

**Note for the 11-08 run:** a job already running keeps the value it started with; the Sunday 02:00 UTC run is the first MA scrape that will start under 24 hours. Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
