# UPDATE to `35b5cda` / `a9fbb18` (the next scrapers image after v78): **core is now `42b48982`** (adds OPEN-773, Kentucky's "Current/Final" stage), and the image is followed by a **`recompute-diff-order ky`** step. Scrapers main is unchanged at `3be4dfce`. 2026-11-22 (Mac side, Onboard New States)

**Not a GO.** Everything in `9e2caaa`, `a9fbb18` and `35b5cda` stands, except that **every `3ac06b6a` in `a9fbb18` now reads `42b48982`** (full sha `42b48982c3378c84f6c549ac9ac37be12bdbf2ae`).

## The core change added
* **OPEN-773**, openstates-core #139 (head `f38eda04`), reviewed and merged by the PM session as `42b48982`. It is the only core change since `3ac06b6a`.
* **What it does:** Kentucky's version name **"Current/Final"** is read as **chamber passage**. Ramon's decision is recorded on OPEN-773 (comment 22587): every one of the 652 such versions passed at least one chamber, and the order stays Introduced → Current/Final → Acts Chapter N. It is the same pattern as Pennsylvania's "Printer's No." (OPEN-482).
* **Change size:** one exact-name rule in `openstates/utils/version_ordering.py` (`note_stage()`), plus tests.
    * **No migration and no model change:** `git diff 3ac06b6a 42b48982 -- '*migrations*'` is empty.
    * On the Mac replica, Kentucky is the only state that uses this version name, so no other state's stages change.
* **Gate on the Mac replica** (`quality_check.py --structural ky`): versions with no stage went from **652 / 2,561 (25.5%, fail)** at core `3ac06b6a` to **0 / 2,561 (pass)** at `42b48982`.

## Release order (as in `a9fbb18`, with the new core; stop if a check fails)
1. **Build the scrapers image** at scrapers `main` `3be4dfce` or later, with core **`42b48982`** (the image takes core `main` at build). The Mac side checks `/opt/openstates-core/DDP_CORE_COMMIT` afterwards.
2. **Both api-v3 copies** at the image's core:
    * the Mac via `refresh-api-v3.sh`;
    * EC2 with `DDP_CORE_SHA=42b48982c3378c84f6c549ac9ac37be12bdbf2ae` (RUNBOOK).
    * Extra check: Kentucky HB 168 (2026RS) versions read "Introduced", then "Current/Final" with a chamber-passage stage.
3. **EC2 ddp-sync** rebuilt with `DDP_CORE_SHA=42b48982…` (SYNC-180). Then `check-core-pin-drift.py --image-core 42b48982… --sync-container …` must exit 0.
    * **This step meets the SYNC-186 release (ddp-sync notes `9825134`, ddp-sync main `b569cf2`).** If both are released, a single EC2 ddp-sync rebuild at `b569cf2` with this core covers both. I'll say so on that request when the image's revision is known.
4. **New: `recompute-diff-order ky` on RDS, after step 2.** It is the prod agent's step, and each half has its own GO.
    1. **Dry run** (read-only) at core `42b48982`, run as for NM (`request-release-core-7ab3303a-…-20261118.md`, part B2). Show that the rule is present: `note_stage('Current/Final')` gives chamber passage. Export Kentucky's stored comparisons first as the backup. Then run `os-text-extract recompute-diff-order ky --dry-run --list <file>`.
        * **Measured on the Mac replica** (read-only session, 11-22): 1707 bills checked, `unchanged=1750 corrected=811 nulled=0`; is_bill_version `set=0 changed=0`; diff_baseline_id **`set=652 changed=179 cleared=0`**.
            * The 652 Current/Final texts gain a comparison against Introduced.
            * 179 enacted bills' Acts Chapter texts are then compared against Current/Final instead of Introduced.
        * At core `3ac06b6a` the same run gives `corrected=0`.
        * **Stop and report if:**
            * `corrected` falls outside 760–860;
            * `set` falls outside 620–680;
            * any `nulled` or `cleared`;
            * any error.
            * The range allows for the replica's lag; a Kentucky run in between can move the counts a little.
        * Report the exact lines and the list's md5.
    2. **Commit** only on a GO note for it.
    * **Not while a Kentucky scrape or archive runs.** KY's weekly run is Sun 11-29 02:00 UTC by default (no timing entry).

## Not authorized by this note
* Building the image.
* Any api-v3 or ddp-sync rebuild.
* The KY dry run or commit before its GO.
* Any other state's recompute.
* LegBot for KY.
* Any manifest change.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
