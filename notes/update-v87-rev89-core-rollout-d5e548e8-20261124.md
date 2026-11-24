# UPDATE (not a GO): **v87 = `ddp-scrapers:89` / `ddp-scrapers-db:16`**, core **`d5e548e8`**, scrapers **`b2d0d4db`**. It needs a core rollout at `d5e548e8`. Small image: Wyoming chambers and North Dakota struck text only. 2026-11-24 ~09:50 UTC (Mac side, Onboard New States)

**Not a GO.** Ramon built v87 (relayed by the PM session). Each step below waits on his go in your session.

## What v87 is (checked on the Mac, local image `ddp-scrapers:v87` id `cf10e3f248d3`)
* `DDP_CORE_COMMIT` = **`d5e548e899c6f5825cb9ec360d15ffb579afba2d`**.
    * Since `59dbdaa2` the core gained only #162: OPEN-836, North Dakota's struck-out law dropped from extracted text. **No migration.**
* Scrapers main at build time = **`b2d0d4dbbeee3077e4fb103326ebd5d61fe7ddba`**.
    * Since v86's `cc028db6` it gained only #264: OPEN-820, Wyoming Senate bills get the Senate as origin.
    * Confirmed in the image: `scrapers/wy/bills.py` carries it.
* **Everything else in review isn't in v87.** That includes HI #266/#268, MS #270, MO #273, KY #274, MT #275, MD #271, ME #267, WA #276, and core #149–#161/#163/#165. They go in the next image (v88) with the next core rollout.

## Step 1: core rollout at `d5e548e8` (on a go; same as `deb1bc6`)
* **EC2 api-v3:** rollback tag, `DDP_CORE_SHA=d5e548e899c6f5825cb9ec360d15ffb579afba2d`, `up -d --no-deps api`. Not 05:00–07:00 UTC.
* **EC2 ddp-sync:** stays at `60791f5`. Rebuild with `DDP_CORE_SHA=d5e548e8…` and **`DDP_SCRAPERS_SHA=b2d0d4dbbeee3077e4fb103326ebd5d61fe7ddba`**. The import check must pass. Tag a rollback, post the in-flight list, wait for any loading run, then `up -d --no-deps`.
* **Mac api-v3:** mine, after your note.
* Then `check-core-pin-drift.py --image-core d5e548e8…` exits 0 everywhere.
* **If new tasks start on rev 89 before step 1:** that's fine. The only core change is in text extraction, which runs in the image. The loader's `59dbdaa2` loads the same way.

## After step 1
* **North Dakota (OPEN-836, must land before ND's public launch, Ramon), each on a go:**
    1. `os-text-extract refresh-extraction nd` dry run. Expect **1,431 changed, 1,259 unchanged, 0 errors** (State Specific Handling's measure). Then commit.
    2. `recompute-diff-order nd` dry run; I post its range. The commit waits on a second go.
* **Wyoming: still wait.** v87 fixes its chambers, but its action labels (core #150) and not-a-version papers (#160) aren't merged yet. One Wyoming re-import after those, not two.
* **Hawaii:** waits for v88 (its fixes aren't in v87 either), still once.
* **The v86 order (`f23fed3`) continues on whichever revision is live:** MD people, then MD, ME, NM, OK 2025+2026, IA 2026, then 2025.
* **MS:** `remove-stale-documents ms` before its recompute (`f23fed3`).

Tickets: OPEN-836, OPEN-820 (OPEN-146).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
