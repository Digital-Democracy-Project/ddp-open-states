# UPDATE (not a GO) to `3e6c766` (OPEN-800 certificate checks): the core rebuild now uses **`fd486fa4`**, which covers OPEN-800, OPEN-803 and OPEN-806 (Missouri version stages). v85 is built after it. Then `recompute-diff-order mo`, dry run first. 2026-11-23 (Mac side, Onboard New States)

**Not a GO.** Everything in `3e6c766` stands (step 0's questions, the Utah canary, watching Georgia, "Not authorized"). Only the commits change, and a Missouri step is added.

## The core: `fd486fa4812c7c1a6268c195aedbeeb1fbe967c3`
* Since `58205e01`, core main gained only #144 (OPEN-806, merged as `fd486fa4`). **No migration.**
    * New `openstates/ddp_states/mo.py`: Missouri's House amendment papers (604) and Senate Amendments-tab cards (142) are marked not-a-version; substitutes are placed by the bill's own chamber.
    * Exact names in `version_ordering`: "Perfected", "Re-Perfected", "Truly Agreed (to) and Finally Passed".
    * The builder's whole-replica comparison (42,305 (state, name, chamber) combinations) shows only Missouri changing.
* **`3e6c766` step 1 now uses `DDP_CORE_SHA=fd486fa4…`.** The same order and windows apply (api-v3 both hosts, then EC2 ddp-sync; the in-flight list first; never 02:15–04:45 UTC; api-v3 not 05:00–07:00). Then `check-core-pin-drift.py --image-core fd486fa4…` exits 0.
* As before: **if `ce0bf8b` step 1 (core `9157b6b5`, Montana) hasn't run yet, do this one instead.** `fd486fa4` contains it, so one rebuild covers OPEN-801, OPEN-800 and OPEN-806.

## Image v85
* Built **after** the rebuild, at scrapers main **`a121b5dd` or later** (it holds OPEN-803 #252: every scraper request goes through core's checked session), with core **`fd486fa4`**.
* **OPEN-803 needs core `58205e01` or later, so never ship it on an older core.**
* Mac side checks `DDP_CORE_COMMIT` is `fd486fa4`.
* Then `3e6c766` step 3 as written: the Utah canary first, a certificate error stops the rollout, then watch Georgia.

## New: Missouri version recompute (OPEN-806), after the rebuild
* **Dry run first** at core `fd486fa4`: prove `openstates/ddp_states/mo.py` exists, then `os-text-extract recompute-diff-order mo --dry-run --list <file>`, after exporting MO's stored comparisons as the backup, as for NM.
* **Measured on the Mac replica** (builder, read-only session):
    * `3133 bills checked | unchanged=3750 corrected=461 nulled=598`;
    * `is_bill_version: set=0 changed=746 not_a_version=746`;
    * `diff_baseline_id: set=372 changed=119 cleared=598`.
* **Stop and report if:** `not_a_version` is outside 700–800, `corrected` is outside 420–510, or there is any error.
* Missouri's weekly run may add a few bills in between, hence the ranges.
* **The commit holds until Ramon's go after he has seen the dry-run numbers,** the same rule he set for Kentucky and Oklahoma (`fe2bb48`).

## Not authorized
Unchanged from `3e6c766`. Also:
* the MO recompute commit before its go;
* any other state's recompute.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
