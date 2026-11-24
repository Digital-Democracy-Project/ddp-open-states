# UPDATE (not a GO) to `e30bb8e`: **recommend Nevada's re-import (step 4e) waits for the next image that contains scrapers #280** (OPEN-865), like Missouri (`c93134c`). Ramon decides the timing. 2026-11-24 ~17:00 UTC (Mac side, Onboard New States)

**Not a GO.** Everything else in `e30bb8e` stands; v88 is unchanged.

* **Why:** #280 (open, head `3e42f808`; State Specific Handling) takes each Nevada vote's result from NELIS ("Passed No" and "Rescinded" give fail; a rescinded vote loses its passage label and keeps its tally). Exactly 3 stored votes change (AB 5, SB 10, AB 4).
* **A scrapers image without #280 writes the old results back on a re-import.** So a Nevada re-import on v88 would have to be followed by a second one, or by the fix-up for those 3 votes.
* **Recommendation:** run Nevada's `2025Special36,84` re-import once, on the image that holds #280, together with its other fixes already in v88's scrapers (#265, #269, #272) and core `0d373728` (#164). The Nevada relabel, recompute dry runs and the scorecard (broker #824, which waits for OPEN-865's fix-up) follow that re-import.
* **If Ramon would rather not wait:** running Nevada on v88 is safe. Its other fixes are all in v88; the 3 wrong votes stay until the fix-up (a ddp-open-states fix-up for them is being built). I'd then verify everything else and run the second pass later.

Tickets: OPEN-865, OPEN-588 (OPEN-146).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
