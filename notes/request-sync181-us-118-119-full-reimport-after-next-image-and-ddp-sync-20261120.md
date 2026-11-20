# REQUEST (2026-11-20, NOT A GO): the US 118th/119th full re-import (OPEN-638 Part B), now startable through ddp-sync (SYNC-181)

Written by the State Specific Handling session (Mac side). **Nothing here has been run on production.** Each step waits for Ramon's go in your session. This replaces "how to start it" in `5836c52` Part B and answers your `e679d4f`. Ramon picked the ddp-sync route (SYNC-181).

## What changed
* **SYNC-181 merged:** ddp-open-states #431 (`8977cedf`) and ddp-sync #302 (`becbceb8`).
* **`POST /trigger/openstates-scrape/usa`** now takes:
  * `sessions=`: the sessions to run, written as `timing.usa.sessions` writes them;
  * `full=true`: no `start=` cutoff, so every bill is scraped again.
* **The state's lock is renewed for the whole run.** The 03:00 UTC `usa` nightly is refused (it logs `PipelineBusy`) until the re-import ends, however long it takes. Nothing in `sync_schedule.yaml` changes.
* **The collector reads `full=true`** (`cloud_collector.py`). It is never passed to the scraper or the load, so the sessions' ordinary watermarks are rewritten and the nightly continues from them afterwards.

## Order (after `eed0ebf` step 2, which your `ba66dd5` shows done except api-v3)
1. **The next scrapers image (Ramon).**
   * `deploy-scrapers-image.sh` clones ddp-open-states `main`, so any image built from now carries #431. `eed0ebf` step 3's release (`TASK_RDS_*`) is such an image; no separate build is needed if that comes first.
   * **Check (Mac side, before step 3 below):** the release names the ddp-open-states commit it built from, and it is `8977cedf` or later.
2. **ddp-sync on EC2 at `becbceb8` or later, only when nothing is running.** The same recipe as your `ba66dd5`:
   * `/opt/ddp-sync` fast-forward to main;
   * rebuild with the **same** `DDP_CORE_SHA=10f32ce08088e544e88d54ec64aa325aea80756f`;
   * tag the running image `ddp-sync:pre-sync181` first;
   * `up -d --no-deps ddp-sync`. Not `systemctl`.
   * **Checks:**
     * `git merge-base --is-ancestor becbceb8 HEAD` succeeds;
     * the drift check still exits 0 (`--image-core 10f32ce0... --container ddp-openstates-api-1 --sync-container ddp-sync-ddp-sync-1`), once api-v3 is also done;
     * **the new option is live, with no run started:** `POST /trigger/openstates-scrape/usa?sessions=118%3Bx` answers **400** "bad session entry". A bad entry is refused before any lock or launch. Read `redis-cli GET ddp:pipeline_lock:us` before and after: unchanged.
   * **Rollback:** retag `ddp-sync:pre-sync181`, then `up -d --no-deps ddp-sync`.
3. **The US re-import.**
   * **Gates:**
     * no `us` scrape, archive or text-extract task in ECS;
     * `GET ddp:pipeline_lock:us` is empty;
     * steps 1 and 2 are done.
   * **Start it** the way you call the trigger today (the ddp-sync API key, by setting name only):
     ```
     POST /ddp-sync/v1/trigger/openstates-scrape/usa?full=true&sessions=118%20chamber%3Dlower,118%20chamber%3Dupper,119%20chamber%3Dlower,119%20chamber%3Dupper
     ```
     The answer must be **202** with `"full": true` and the four sessions echoed. A 409 means a `usa` run holds the lock: wait, do not force.
   * **What runs:** four Fargate collections, one after another (`usa session=118 chamber=lower full=true`, and so on), each followed by its RDS load, then one archive and the usual LegBot hand-off, the same pipeline as the nightly.
   * **Expected, not failures:**
     * the "still running" alert at each collection's wait (OPEN-477);
     * the 03:00 UTC nightly logging `PipelineBusy` while the run holds the lock;
     * hours of run time: the Mac replica holds 19,315 bills for the 118th and 20,004 for the 119th.
   * **The Fargate task must report** the step 1 image's revision, or later.
   * **Report** (as `5836c52` Part B asked):
     * the run ids and the image revision;
     * each collection's completion record, which must say `"mode": "full"`;
     * each loader's final status (no `DuplicateItemError`), with bill and vote counts.
   * **Then `5836c52` Part C (C2, C3) unchanged:** the federal link counts by Congress and type, before and after.
   * **Stop rule:** a collection failing with an argument error (`full` handed to the scraper) means the image predates #431. Report it; do not retry.

## Not in this request
* Any `sync_schedule.yaml` change (none is needed).
* The broker's link reconcile (BROKER-548): it waits for Part C.
* Any other state.

Tickets: OPEN-638, SYNC-181. Plan: ddp-infra PLAN-companion-lineage §4.2.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
