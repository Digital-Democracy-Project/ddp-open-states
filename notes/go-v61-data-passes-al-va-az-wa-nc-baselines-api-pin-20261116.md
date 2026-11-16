# GO: v61 (`ddp-scrapers:64`, core `bcde78e2c`) is LIVE. Today's data passes, each saved **only if its trial run matches its gate**; any miss stops that step and you report. 2026-11-16 (Mac side)

**Ramon, 2026-11-16:**
* "all your tickets have merged. let's deploy the fixes".
* He built v61 and asked: "can you please register the image once it's built?". The Mac side registered it: **revision 64 = `ddp-scrapers:v61`, 16:54:55 UTC**, digest `sha256:1bf81e2acbd145b3b45503aee64f060ca1dbeca14456026d6d885ed86d7a8c52`. The script's checks passed: Python 3.13.18, imports, the Utah one-bill smoke test (RC 0, 1 bill), and the recorded core `bcde78e2ce977e1783a77484a2d78344404a5f5e`. Rollback (Ramon): `aws ecs deregister-task-definition --region us-east-1 --task-definition ddp-scrapers:64` leaves 63 = v60.
* Pop-ups:
  * the data passes: **"All three"** (Alabama, VA/AZ comparison rebuild, WA text refresh);
  * OPEN-539 baselines: **"Yes, all states"**;
  * api-v3 pin: **"Move the pin in this release"**;
  * the Push Button Onboarding session's NC struck text and VA people load: **"Include both"**.

**In v61** (core `bcde78e2c`, scrapers `8541cbd87`, ddp-open-states `7c91a28`):
* Alabama runs without `start=` (`start_filter: false`; ddp-open-states #387, OPEN-501). This fixes `6d5db0e`.
* One rule for which document of a version is the comparison baseline (core #108, OPEN-578).
* Washington's HTML read without struck words (core #107, OPEN-580).
* NC "reads as rewritten" struck text (core #109, OPEN-584).
* PA (scrapers #108, OPEN-576).
* Massachusetts votes recorded on amendment papers shown on their real bill (scrapers #107, OPEN-568). No step here: Massachusetts' next run applies it (Sunday 11-22). The Mac side then checks votes on papers 87 → 6, and on the 15 real bills 46 → 127.
* The image records its core commit in `/opt/openstates-core/DDP_CORE_COMMIT` (#382, OPEN-579).

## Rules for every step
* **Windows:**
  * not during wa 02:30, usa 03:00 or pa 04:00 UTC (11-17), or the 05:00-07:00 scorecard chain;
  * at most two state pipelines at once;
  * none of a state's own steps while its scrape, import or archive runs.
* **Tools:**
  * data steps use v61's core `bcde78e2ce977e1783a77484a2d78344404a5f5e` (the image, or a throwaway worktree of that commit on `PYTHONPATH`, as before);
  * exports before every commit that rewrites stored text or comparisons (the MA/PA format);
  * change lists with `--list` to a lasting path under `/home/bitnami/ops/step-v61-20261116/`.
* **A stop is harmless.** Report it; do not retry beyond what a step says.

## 1. Alabama (OPEN-501, OPEN-569, OPEN-564, OPEN-577)
1. **One** manual run: `POST /ddp-sync/v1/trigger/openstates-scrape/al`, the `1f19165` method, one call, no retry.
   * **Gate:** revision 64 from ECS; the scrape line says `mode: full` with no `start=` (the `start_filter: false` path); `status=completed failed=0`; the archive finished.
2. **Section B of `a774838`** (B.1 to B.4), with its gates unchanged. It runs after this run's import **and** archive. The `b261ead` hold ends only through those gates.
3. **Alabama's search rebuild** (OPEN-577) on EC2, after B: `docker exec ddp-openstates-api-1 python -m api.search_projection refresh --full --jurisdiction al`. Report the summary line. The Mac side does the Mac's.

## 2. Virginia, then Arizona (OPEN-578)
Per state:
1. Export the state's stored comparisons.
2. `recompute-diff-order <st> --dry-run --list <path>`.
   * **Gate:** 0 errors; `nulled=0`; `corrected` va **800-860** (Mac replica 829), az **40-55** (47).
   * If a scrape since 11-16 changed a document, more may be pending: report and stop rather than widen the gate yourself.
3. Commit with `--commit --list <path>`. A second dry run must give `corrected=0`.
4. Then (step 5 below) `--baseline-only` for that state must refuse nothing.

## 3. Washington (OPEN-580), clear of WA's 02:30 nightly
1. `refresh-extraction wa --dry-run`.
   * **Gate:** 0 extraction errors; stale about **7,354** (3,677 HTML + 3,677 PDF, ±3%). Report the HTML/PDF split if the output gives it.
2. Commit (export first), then a second dry run with 0 stale.
3. `recompute-diff-order wa --dry-run`. **Gate:** `nulled=0`; report `corrected`. Then commit.

## 4. North Carolina struck text (OPEN-584) and the Virginia people load (OPEN-473): the Push Button Onboarding session's gates, word for word
**A. NC:**
1. `refresh-extraction nc --dry-run`.
   * **Gate:** 0 extraction errors, and stale between **2,000 and 3,480**.
   * Basis: 3,379 of 6,207 NC documents have a "reads as rewritten" section.
   * Outside the range: stop and report.
2. Commit, then a second dry run showing 0 stale.
3. `recompute-diff-order nc --dry-run`. **Gate:** `nulled=0`; report `corrected`. Then commit.

**B. Virginia people load** (people #23, merged 14:40 UTC; no image needed):
* `os-people` for va, the way 4.3 went (the container's `/opt/venv-openstates/bin/os-people`, `--safe` first).
* **Gate:** only **11** updates, all Virginia `other_names` additions.
* VA's full re-scrape is **not** in this GO.

## 5. OPEN-539 baselines, every state, last
Per state:
1. `recompute-diff-order <st> --baseline-only --dry-run`.
   * **Gate:** `not_stamped_comparison_would_change=0`; `stamp` within ±3% of the Mac-replica count (us 13,941; fl 8,519; wa 4,580; va 14,927; mi 5,065; ut 4,158; az 4,328; ma 364; nc 3,557; al 1,116; pa 1,842; ne 745; la 4,486).
   * Counts for states that ran steps 1-4 may differ: report and use the dry run's own count.
2. `--baseline-only --commit --expect N --list <path>`.
3. **Gate after:** `comparisons_without_baseline=0`.

**Order:** the untouched states first; **va, az (after step 2), wa (after 3), nc (after 4A), al (after 1)** last.

## 6. api-v3 pin, both copies (OPEN-579)
* When Ramon has merged api-v3 PR #68 (pin = `bcde78e2c`): the api-v3 step as `52fcaf5`:
  * pull ddp-open-states first;
  * tag `pre-<sha>`;
  * build;
  * `up -d --no-deps api`;
  * check `import openstates.utils.version_ordering`.
* Then from `/opt/ddp-open-states`: `python3 check-core-pin-drift.py --image-core bcde78e2ce977e1783a77484a2d78344404a5f5e --container ddp-openstates-api-1`. **Gate:** exit 0. Report its output.
* The Mac side does the Mac's.

## Not authorized
* Any other state's scrape.
* PA's full walk; VA's full re-scrape.
* A second launch of Alabama.
* Any commit whose gate fails.
* Task-definition changes.
* Anything on ddp-sync or the broker.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
