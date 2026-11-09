# Request (production change, GO given): `recompute-diff-order la` on RDS, then api-v3 on EC2 to `fe6532a9` (OPEN-510, OPEN-511, OPEN-496; OPEN-480). 2026-11-08 about 22:00 UTC (Mac side)

**Ramon's go** (2026-11-08, /onboard-state pop-up): "Go on all of it". It covers Louisiana's new scrapers image (done, below), **this recompute with stop conditions** (dry run first; the commit goes ahead only if the dry run is inside the numbers below; otherwise stop and report), and the api-v3 update. It does **not** cover switching Louisiana on: no session row, no flags, no #350.

## Why
The dev LegBot sample (OPEN-480 comment 19537) failed 15 of 26 Louisiana bills because the comparisons run backwards. Two fixes are merged in openstates-core:
* **OPEN-510** (#87, `6641dda7`): "<bill> Engrossed", "Reengrossed" and "Re-Reengrossed" were tied, and with no version dates they kept storage order. Measured on the Mac replica: 505 of 2,908 non-empty comparisons ran backwards, and 1,405 change predecessor.
* **OPEN-511** (#86, `2e49bd2d`): 55 conference committee reports were marked as bill versions. They become not-a-version, which drops 55 report diffs and rebases 48 Enrolled diffs.

The same recompute also applies **OPEN-496** (Louisiana's "Page N of M" footer cleaner, merged earlier and never recomputed on production).

**Code.** Image **`ddp-scrapers:v50`**, digest `sha256:017cf26ae2b13e29f12ce348a4aac9f86d98063b733746ab2a4356e8c93d5263`, **task-definition revision 52**. Ramon registered it at about 21:55 UTC; the one before was v49 / 51. It carries openstates-core `main` at `6641dda7`. I checked inside v50:
* `note_stage()` gives `(2,0.0) (2,1.0) (2,2.0)` for SB217 Engrossed / Reengrossed / Re-Reengrossed;
* `is_bill_version("Louisiana", "Conference Committee Report, #4594, House Adopted, Senate Adopted", …)` returns `False`.

v50 also carries **OPEN-508** (the Massachusetts scraper skips reports and orders). That ticket asks you to check its "OPEN-508: ... skipping" lines on the next Massachusetts run. This request does not run Massachusetts.

## Part 1: dry run (read-only)
1. **G1 (code):** you run from v50 / revision 52 (say how), or from an environment with openstates-core `6641dda7`. Never from an older image.
2. **G2 (quiet):**
   * RDS latest restorable time recorded;
   * no Louisiana task, lock or archive in flight;
   * no ddp-sync job in the last 10 minutes;
   * clear of 02:00 to 03:10 UTC.
   Pennsylvania's nightly starts 04:00 UTC and touches no Louisiana rows. Ramon may be running a Pennsylvania LegBot write-back; that does not block this.
3. **G3 (baseline, read-only), for Louisiana:**
   * documents in total;
   * `is_bill_version` true / false / null;
   * documents with a diff;
   * a diff fingerprint, using the same query as `request-recompute-diff-order-ma-flags-only-open498-20261107.md` G3 with `j.name='Louisiana'`.

   **Expect:** 10,468 documents, 7,140 true and 3,328 false, 0 null.
4. **Dry run:** `recompute-diff-order la --dry-run`. Report every line and the time taken.

   **Stop conditions. Report and do not commit if any is outside:**
   * `not_a_version` is **3,383** (3,328 + 55). Anything else: stop.
   * `corrected` is **between 1,411 and 2,400**. The order fix alone measures about 1,411 over all 4,541 comparisons. The footer cleaner adds some on top: about 22% of sampled comparisons carried a footer line, and they overlap. Below or above: stop.
   * `nulled` is **at most 80**. The 55 report diffs drop, plus a margin. More: stop.
   * No other state is mentioned, and no error or Traceback appears.

## Part 2: commit (Ramon's go covers it if Part 1 is inside every stop condition)
1. Post Part 1's lines as a short note **first** (`reply-recompute-diff-order-la-preflight-<date>.md`).
2. Then run `recompute-diff-order la --commit`. It must print the same numbers as the dry run. Any difference: stop after the commit and report.
3. Then `--dry-run` again. It must show `corrected=0` (or the tool's equivalent) and the same `not_a_version`.
4. Then G3 again: true 7,085, false 3,383, null 0.
5. **No search-index refresh** (a separate request if needed).

## Part 3: api-v3 on EC2 to `fe6532a9` (after Part 2)
api-v3 has its own copy of the ordering code. OPEN-510 is api-v3 **#52** (`fe6532a9`).
* Record the EC2 api-v3 checkout's current revision first, and list the commits this brings. #49 (OPEN-422) and #51 (OPEN-493) may also be new to EC2: say whether they are.
* Then follow api-v3's own runbook section 8: **ensure before recreate**, the **api service only, by name**, never an unscoped recreate.
* **Check:** `GET /bills/ocd-bill/<SB 217 Louisiana id>?include=versions` lists Original, Engrossed, Reengrossed, Enrolled, Act in that order; health 200; `/ddp/enrollment` unchanged.
* The Mac's api-v3 is Ramon's step (`refresh-api-v3.sh`); do not touch the Mac.

## Rollback
* **Recompute:** RDS restore to the recorded time is the only full undo. A rerun of `recompute-diff-order la` on the previous image (v49) puts the order back but cannot unflag the 55 reports. Say if you think a restore is needed; do not do it.
* **api-v3:** return the checkout to the recorded revision and recreate the api service the same way.

## Not authorized
* Any other state, or `all`.
* `--flags-only` or any other variant.
* Search refresh, scrape, archive, schedule change, LegBot run.
* Louisiana's or Nebraska's session row or flags (#350).
* Registering or deregistering a task definition.
* An unscoped recreate.
* Anything on the Mac.

## What I check on the Mac side
After the commit, on the Mac replica:
* the same counts as G3;
* SB 217's comparisons now run Original → Engrossed → Reengrossed → Enrolled → Act;
* none of the 55 reports has a diff;
* other states unchanged.

Then I post `reply-verified-recompute-diff-order-la-<date>.md`.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
