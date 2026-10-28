# Reply (read-only parts only): OPEN-318 on the EC2 host. Nothing changed; one thing in the plan needs your confirmation

Prod agent, Wed 2026-10-28 00:15 UTC. The operator said "Option A, run the read-only parts now": step 1 and the read-only reports for steps 5 and 6. **No pull, no rebuild, no recreate, no restart.** Steps 2 and 3 wait for the operator's go and a quiet window. Output saved in `/home/bitnami/ops/open318-readonly-*/`.

## Step 1: what is here now
* **`/opt/ddp-open-states`:** `9baa61ed59` (merge of #286, 2026-10-22), working tree clean, **13 commits behind** `origin/main` (`3b78732760`). The 13 commits change only: check/fix scripts and their tests, `lib/slack-alert.sh`, `check-replica-health.sh`, `validate_jurisdictions.py`, `RUNBOOK.md`, `PRIMITIVES.md`, `notes/*`, and **`jurisdictions.yaml`**. Nothing under `people/`, `api-v3/` or `deploy/`. The host `jurisdictions.yaml` (mtime 10-22 21:42:25 UTC) has **0** `scheduled:` lines now; `origin/main`'s has **10**.
* **IMPORTANT: api-v3 is its own git checkout** at `/opt/ddp-open-states/api-v3` (remote `Digital-Democracy-Project/api-v3`), HEAD **`a2f5db8`** (PR #32, OPEN-377, 2026-10-16), clean. `origin/main` is `d5b37dc`, **6 commits ahead**, and it is the only place the endpoint lives (PR #33: `api/ddp_enrollment.py`, `api/main.py`, 10-21). **Your step 2 says "pull `/opt/ddp-open-states`" only; that does not bring the endpoint, and a rebuild without pulling api-v3 would rebuild the same old code.** Please confirm that step 2 also means "fast-forward the api-v3 checkout to `main`" (the Mac script `refresh-api-v3.sh` does it).
* **How it is built and started:** compose project `ddp-openstates-rds`, file `/opt/ddp-open-states/deploy/docker-compose.rds.yml` (RDS-backed), service `api`, build context `../api-v3` with `../deploy/Dockerfile.ddp`, image `ddp-openstates-api:local`, `restart: unless-stopped`. The compose file already has `../jurisdictions.yaml:/app/jurisdictions.yaml:ro` (added by OPEN-329, `6daac2138c`).
* **The running container** `ddp-openstates-api-1`: created 2026-10-21 05:36:47, started 05:36:49, image built 05:36:41 (that is my OPEN-377 deploy), healthy. **It has no mounts at all and `/app/jurisdictions.yaml` does not exist inside it**, as on the Mac: it needs a recreate and a rebuild.
* **No Postgres container exists on this host** (api-v3 here uses RDS), so the "Postgres start time unchanged" check does not apply; the only other container in that project is `ddp-openstates-redis-1` (up 2 weeks), which `--no-deps` leaves alone.
* The compose directory `deploy/` is not changed by the 13 commits, so pulling does not alter the compose file.

## Step 5: ddp-sync on this host (read-only)
* `jurisdiction_manifest_unusable error="missing field 'scheduled'" feature=archive` appears **once**, at 13:46:25 UTC 10-27 (the container's start). It will clear at the next start after the pull; I did not restart it.
* The daily drift job (OPEN-330): `sync_schedule.yaml` has it `enabled: true` (06:20 UTC, every 7 days), **but the host's effective setting `jurisdiction_drift_check_enabled` is `False`**, so the job is **not registered** in the live scheduler (18 jobs, none named drift) and it has **never run**: no drift log lines. I did not enable it.

## Step 6: broker on this host (read-only)
* `DDP_ENROLLMENT_SOURCE` is **not set** in the broker `.env` or the web container; the effective value is the default **`env`** (the manifest only compared, never decides routing).
* After step 3: not applicable yet. For now: **no "enrollment drift" line** in the celery or web logs since the 19:56 UTC restart. I could not tell whether the hourly bill-event task runs here (it is not one of the 8 beat rows), so silence is not evidence either way.

## What I would do on the operator's go (writes)
1. Fast-forward `/opt/ddp-open-states` to `3b78732760`, and (if you confirm) `api-v3` to `d5b37dc`; report both HEADs.
2. `docker compose -p ddp-openstates-rds -f /opt/ddp-open-states/deploy/docker-compose.rds.yml up -d --build --no-deps api`, after checking `docker compose ... config` shows the mount and which env files it needs. About 1 minute without api-v3; anything that reads api-v3 (VoteBot, LegBot's candidate lookups, the broker's search path) fails for that minute; I have not listed every client.
3. Verify as in your step 4 and report `manifest_mtime` and the status only.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
