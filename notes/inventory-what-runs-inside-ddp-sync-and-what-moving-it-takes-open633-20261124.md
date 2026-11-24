# INVENTORY (no build, no request): everything that still runs inside ddp-sync on EC2, what moving each to Fargate takes, and what must stay. Also **a correction to my own `581aedf`**. 2026-11-24 ~22:15 UTC (Mac side, Onboard New States)

Read-only, from `origin/main` of ddp-sync (`90eee20`), ddp-open-states (`3d1801a`) and ddp-infra `PLAN-cloud-load-on-fargate.md`. **Not production:** I did not read what is deployed on EC2. Ramon's goal: ddp-sync is a scheduler that starts jobs and orchestrates follow-ups (LegBot and the like). Ticket: OPEN-633.

## Correction first
In `581aedf` I wrote that archives "resume the same way" after a ddp-sync restart. **That was wrong.** The archive task is on Fargate, but **the wait for it is not in the in-flight record** (only scrapes and loads are: `cloud_scrape_trigger.py` `record_started` :1101 and `record_load_started` :626). If ddp-sync restarts while an archive runs:
* the Fargate task keeps running to the end;
* **the follow-ups for that run never fire** (LegBot, bill search refresh, embedding), and the archive's retry timing is lost;
* startup also clears every state's Redis lock (`app.py:46-47`), so that state's pipeline could start again while its archive still runs (the archive's own lock inside the task stops two archives overlapping).
So Ramon's question has a precise answer: **a running archive does matter for a restart, for the follow-ups, not for the archive's data.** The fix is the OPEN-633 pattern: record the archive's task ARN in the same record and have the restart path wait for it, then run the hooks.

## Short answers
* **Archive:** runs on Fargate (`ddp-scrapers-db`, `cloud_archiver.py`), `openstates_archive.use_fargate: true`. Text extraction and the `raw_text` write happen inside that task; ddp-sync never extracts text. A local fallback (`run-archive.sh` in the container) exists but is off (dead code).
* **Load:** **not** on Fargate yet. Every state loads as a child process inside the container (`_run_load`, `cloud_scrape_trigger.py:643`). The Fargate branch exists (:593) and is off for all 30 states.
* **What ties ddp-sync's image to openstates-core is exactly three jobs:** the load, the after-load unmatched-voter check, and the weekly people refresh. ddp-sync's Python never imports `openstates` or Django.
* All 30 states use the cloud path, so the local `run-scrape.sh` branch is dead for every state.

## Inventory
| # | Item | Where it runs today | Moves to Fargate? |
|---|---|---|---|
| 1 | Per-state pipeline (scheduler, locks, order of steps) | Inside ddp-sync (asyncio, one APScheduler job per state) | **Stays** |
| 2 | Collection | Fargate `ddp-scrapers`; ddp-sync launches (32-slot pool) and waits | Already |
| 3 | **Load** into RDS | **Inside the container** (subprocess); Fargate version built, off | **Next: OPEN-633, mostly built** |
| 4 | **People refresh** (weekly, Sun 10:00 UTC) | **Inside the container** (`run-people-refresh.sh`, `os-people`) | Decided (D3), **not built** |
| 5 | **Unmatched-voter check** (after each load) | **Inside the container** (`unmatched-voters.py` with the openstates venv) | **Not built**; two options below |
| 6 | Archive launch and wait | Fargate; ddp-sync launches and waits | Already (but see the restart gap) |
| 7 | Archive retry (30 min, 2 h, then alert) | Inside ddp-sync | **Stays** |
| 8 | LegBot dispatch | ddp-sync resolves changed sessions via api-v3, then calls the Mac's ddp-sync over WireGuard; the LegBot work runs on the Mac | **Stays** (orchestration) |
| 9 | Bill search refresh | Inside ddp-sync, an HTTP loop against api-v3 | **Stays** (HTTP only) |
| 10 | Knowledge-base embedding | Inside the container; hours long; OpenAI, Pinecone, api-v3 reads | Needs no core or database login; **leave unless Ramon wants a thin container** (restart risk: no in-flight record) |
| 11 | Broker signals (bill events, scorecard refresh) | Inside ddp-sync, small HTTP POSTs; both switches off today | **Stays** |
| 12 | Drift check (06:20 UTC) | Inside ddp-sync (manifest and its own yaml, Slack) | **Stays** |
| 13 | People pull (03:00 UTC, git only) | Inside ddp-sync | **Stays** |
| 14 | Patch refresh | Off on EC2 | Dead code to remove |
| 15 | Data-quality backfills (on demand) | Fargate | Already |
| 16 | "Smoke test", "QA sweep" | **Not found in ddp-sync** (nearest: probe-on-fargate and `quality_check.py`, run as Fargate or Mac tools) | If the PM means something else, I need its name |

## What each move takes
**The load (OPEN-633), mostly built:** the loader is in the scrapers image; `ddp-scrapers-db` is the one task definition allowed to carry the database login; ddp-sync waits with a 2 h hard stop and reads the exit code (90 = lock held); the task's ARN goes in the in-flight record, so a restarted ddp-sync waits for it. **Left:** the login route (ddp-sync passes it at launch today, or the stored secret with `rds_from_task_secret`, which needs the secret live on `ddp-scrapers-db`, not confirmed), one state flipped on, a clean week, then the rest.

**The people refresh (D3), not built:** a new runner `cloud_people_refresh.py` in the scrapers image, added to the image's file list; launched through the same launcher on `ddp-scrapers-db`; the task must fetch the `people` repo (a DDP fork; whether it is reachable from Fargate is **not verified**); ddp-sync needs a **per-state result** (today the script exits 1 without saying which state failed) so the broker scorecard signal fires only for states that worked; and the job needs an in-flight record. `people_pull` (git only) stays.

**The unmatched-voter check, not built.** Option A: a runner in the image launched on `ddp-scrapers-db`, writing its JSON to S3 for ddp-sync to read. Option B: a small read-only api-v3 route calling the same `qa_primitives.unresolved_voter_names`, fetched over HTTP, with no Fargate wait. B is smaller but is a second place the rule can drift, and PRIMITIVES says "do not add a second unmatched-voter query": **Ramon's decision.**

## What must stay in ddp-sync
All scheduler jobs and the cadence review; per-state locks, retry timing, status and in-flight records; launching, waiting on and reading Fargate tasks; Slack alerts; broker signals; bill search refresh; the drift check and people pull; LegBot dispatch and its hand-off; the manifest reader. Keep the `/opt/ddp-open-states` bind mount (the manifest and `people/`).

## The order that retires ddp-sync's own copy of openstates-core
1. Ship OPEN-633 (secret and permission live, `rds_from_task_secret`, one state, a clean week, the rest).
2. Build the unmatched-voter move (A or B).
3. Build the people refresh runner and move it.
4. Add the **archive** to the in-flight record (this note's correction), so a restart loses nothing.
5. Confirm nothing else needs `os-update`, `os-people` or the venv (my helper's search found nothing), then remove the dead code (local load, local scrape, local archive fallback, patch refresh) and the image layers (builder stage, `/opt/venv-openstates`, `/opt/openstates-core`, `/opt/openstates-scrapers`, `DDP_CORE_SHA` / `DDP_SCRAPERS_SHA`, the drift check's `--sync-container`).
6. Update PRIMITIVES and RUNBOOK in both repos (OPEN-633's fourth acceptance line).

## Not verified
Production state (which ddp-sync commit is on EC2, whether `rds_from_task_secret` or any `load_on_fargate` is on there, whether the secret and permission are live); whether `os-people` is in the scrapers image; fetching the people fork from a Fargate task; durations and cost on Fargate; whether a moved people refresh fits the Sunday 10:00 window; the Mac's ddp-sync jobs; any Jira or Slack text.

Tickets: OPEN-633, OPEN-639.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
