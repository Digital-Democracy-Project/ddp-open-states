# UPDATE (not a GO) for your ~07:15 UTC rollout: **one core rollout at `59dbdaa2`**. **EC2 ddp-sync built from ddp-sync main `60791f5`** (SYNC-188 + SYNC-189) with `DDP_SCRAPERS_SHA=cc028db6…`. **v86 = `ddp-scrapers:88` / `ddp-scrapers-db:15`.** 2026-11-24 ~04:50 UTC (Mac side, Onboard New States)

**Not a GO.** Ramon confirms the target in your session, as you planned. This note replaces `eb197d74` as the target everywhere in `0940569` step 1. It adds to `31e0885`.

## v86 (Ramon's build, per the PM session), checked on the Mac
* **Tag `v86`: task definitions `ddp-scrapers:88`, `ddp-scrapers-db:15`.**
* The local image `ddp-scrapers:v86` (id `0d2247f55a13`):
    * `DDP_CORE_COMMIT` = **`59dbdaa2f3628821baa4cd45f1fabeb2cf936c7a`**;
    * the scrapers hold OPEN-819 (Washington `2027-28`) and OPEN-818 (New Mexico suffixes), so they are at scrapers **`cc028db6d4ccf5d85ea51b94473b3ce015ce2108`** or later.
* This answers your `82926a0` question: **rev 88 is v86.** Florida 2026 on it is fine (`31e0885`).

## The rollout (one, about 07:15 UTC; your windows)
1. **EC2 api-v3:** rollback tag, then build with `DDP_CORE_SHA=59dbdaa2f3628821baa4cd45f1fabeb2cf936c7a`, then `up -d --no-deps api`. Not 05:00–07:00 UTC.
2. **EC2 ddp-sync, now from ddp-sync main:**
    * `git -C /opt/ddp-sync merge --ff-only origin/main`. Expect **`60791f53f0ee9360229ee02c742d01e95a173dbf`**.
    * `85c8888..60791f5` is exactly:
        * #306 (SYNC-188: the build takes a scrapers commit and checks the pair);
        * #307 (SYNC-189: a run resumed after a restart releases its own lock, `pipelines/cloud_scrape_trigger.py`, plus a test).
    * **No** `.env`, yaml, schedule, requirements or manifest change.
    * Build with **`DDP_CORE_SHA=59dbdaa2f3628821baa4cd45f1fabeb2cf936c7a`** and **`DDP_SCRAPERS_SHA=cc028db6d4ccf5d85ea51b94473b3ce015ce2108`** (v86's scrapers; ddp-sync `132d8cf`).
        * The build runs `check-scraper-imports.sh` on that pair; **a failure stops the build. Report it, don't work around it.**
    * Tag the running image as the rollback point. Post the in-flight list. **Wait for any run that is loading** (your rule). `up -d --no-deps`.
3. **Mac api-v3:** `refresh-api-v3.sh` with `SCRAPERS_IMAGE_CORE=59dbdaa2…`. Ramon or me; I'll do it after your rollout note.
4. **Checks:**
    * healthy, `Redis connected`, 0 `Traceback`, the same `/schedule` jobs;
    * in ddp-sync, `cat /opt/openstates-scrapers/DDP_SCRAPERS_COMMIT` = `cc028db6…`;
    * `check-core-pin-drift.py --image-core 59dbdaa2…` exits 0 for every container.

## Rollback
* api-v3: re-tag its rollback image.
* ddp-sync: `checkout --detach 85c8888`, re-tag the rollback image, `up -d --no-deps`. The old image needs no `DDP_SCRAPERS_SHA`.

## After it
* Washington's 02:30 UTC nightly on v86 is the check (`4389222`).
* Then `0940569` steps 4–6 and the NM re-import (`a1c833f`) on v86, one heavy load at a time, each on Ramon's go.
* The PM merges ddp-open-states #478 (the drift check reports the scrapers commit) after your rollout report.

Tickets: OPEN-817, OPEN-819, OPEN-818, SYNC-188, SYNC-189 (OPEN-146).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
