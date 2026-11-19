# ADDENDUM 2 to `05a7643` (after `abef131`): Part B runs on **v69 only, not v68**. api-v3 at core `c983ae68`, then ONE `recompute-diff-order nm` with a new gate (about 129 corrected, about 85 cleared, 85 unflagged). 2026-11-19 (Mac side)

**Why:**
* Ramon decided OPEN-637 on 11-19 (comment 21544): New Mexico's "Amendments in Context" files stay documents only and are **not bill versions**.
  * 79 of the 85 are "Print To PDF" files whose text extracts as the page header only.
  * In the dev LegBot sample, every changelog INTO one said "the bill no longer amends the law".
* core #132 (merged `c983ae68599e94494a94edc23d576b483922302e`) adds that name to the existing not-a-version table, `_PROCEDURAL_DOCUMENT_NOTES`.
* **Ramon is building v69 from main now, with this core.** The PM session will send the digest.
* So NM's comparisons are rebuilt **once**, on v69, with both NM rules: OPEN-635 (Final Version = final passage) and OPEN-637.

**Core since v68's `5c1455e1`:** only #132 (`version_ordering.py` and tests). **No migration, no model change.**

## What I need from you (Part B, replacing `05a7643` / `abef131` Part B)
0. **Do not run Part B on v68.** If you already started it, stop and report what ran.
1. **Gate:** ddp-scrapers' latest ACTIVE revision is **v69**, as the PM session's or my `update-` note names it, and the image records core `c983ae68`. Any other core: stop.
2. **EC2 api-v3 at core `c983ae68`,** the same method as `a630172`:
   * tag the running image (`:pre-v69`);
   * build with `DDP_CORE_SHA=c983ae68599e94494a94edc23d576b483922302e` (`docker-compose.rds.yml`);
   * `up -d --no-deps api` only.

   **Gates:**
   * healthz 200 before and after;
   * `check-core-pin-drift.py --image-core c983ae68599e94494a94edc23d576b483922302e --container ddp-openstates-api-1` exits 0.
3. **`recompute-diff-order nm`, dry run first** (read only), core `c983ae68`:
   * Export NM's stored comparisons and flags first (the backup, as in `e4a007a` step 2).
   * `os-text-extract recompute-diff-order nm --dry-run --list /home/bitnami/ops/step-open635-637/nm-dry.csv`. Use the full recompute: **not** `--flags-only`, because the comparisons change too.
   * **Baseline and expectation.** NM, Mac replica, measured by running core's own recompute in memory, read only (OPEN-637 comment 21548):

     | | Today | After |
     |---|---|---|
     | Bill versions | 1,113 | 1,028 |
     | Comparisons | 171 stored | 215 |

   * **Expected lines:**
     * `corrected` about **129**: each Final Version gains its comparison (OPEN-635);
     * about **85 cleared** (`nulled`): comparisons into the Amendments in Context files go;
     * **`is_bill_version` changed = 85**: those 85 documents become not-a-version;
     * 0 errors.

     It may report the comparisons that used to be measured *against* an AIC file (about 41) as corrected rather than cleared; report the exact split.
   * **Stop and report if:** `corrected` is outside 100 to 175; cleared is outside 70 to 100; `is_bill_version` changed is not 85; anything is touched outside `nm`; or there is any error.
   * Report the exact lines and the list's md5. **The commit holds until a GO note.**
4. **After the commit (on its GO):** a second dry run must give `corrected=0` and `nulled=0`.
   * A `--full` search-index refresh may be needed afterwards; say if the tool asks for it. Don't run it without the GO.

## Timing (real reasons only)
* api-v3: not 05:00 to 07:00 UTC (the scorecard chain).
* The NM recompute: not while an NM scrape runs; best before NM's Sunday 11-22 02:00 UTC run.

## Not authorized
* The recompute commit (needs a GO).
* `--flags-only`.
* Any other state.
* LegBot for NM.
* Any manifest change.
* ddp-sync's rebuild (SYNC-180's own request).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
