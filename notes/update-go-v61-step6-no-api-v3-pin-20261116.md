# Update to `e4a007a`: **skip step 6.** No api-v3 rebuild in this release; api-v3 PR #68 is closed. Steps 1-5 are unchanged. 2026-11-16 ~17:10 UTC (Mac side)

**Ramon, 2026-11-16 (pop-up): "Follow core's main".** api-v3 will take openstates-core's main at build time, like the scrapers image, instead of a pinned commit. That change is ticket **OPEN-586**, not built yet. So:
* **Do not rebuild api-v3** for this release. It stays on `306b4f5` (core pin `96445eb26`). That is safe: the parts of core api-v3 imports (version rules, state lookup, bill-id formatter) are identical between `96445eb26` and v61's `bcde78e2c`.
* **The core-version check** (`check-core-pin-drift.py --image-core bcde78e2c...`) would exit 1 today (api-v3 on `96445eb26`, the image on `bcde78e2c`). That is the known state until OPEN-586 ships, so **there is no need to run it now.** If you do run it, a `DRIFT` naming exactly those two commits is expected, not a stop.
* **Everything else in `e4a007a` stands as written:** 1 Alabama, 2 Virginia then Arizona, 3 Washington, 4 NC struck text and the VA people load, 5 the OPEN-539 baselines for every state.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
