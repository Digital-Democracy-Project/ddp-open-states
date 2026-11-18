# ADDENDUM to `05a7643` (each part still waits on Ramon's go): image v68 now also carries Utah's two fixes, so its core is `5c1455e1`, not `7ab3303a`. 2026-11-18 (Mac side, State Specific Handling)

**Not a GO.** It changes the scope of request `05a7643` (OPEN-635, New Mexico's "Final Version"). Everything else in that note stands, with the commit replaced as below.

## What changes
`deploy-scrapers-image.sh` builds from each fork's main, and two Utah fixes merged after `05a7643` was written. So v68 carries:

| Repo | v68 commit | Since `05a7643`'s scope | Ticket |
|---|---|---|---|
| openstates-core | **`5c1455e1679bbdac8f00fe050d57c0152e17c648`** (#130) | on top of `7ab3303a` (#131, OPEN-635): `openstates/ddp_states/ut.py` and its test only | OPEN-547 |
| openstates-scrapers | **`dca8e7a6920cac2a4133af61fec8d9e2ca0817c6`** (#131) | on top of v67's `7fa39511`: `scrapers/ut/bills.py` and tests only | OPEN-622 |

* **Core, OPEN-547.** Utah's action rule keeps `passage` on "<chamber> Conference Committee - Final Passage" lines: each chamber's floor vote on a conference report. Without it, HB 136's scorecard score falls from 50 to 0.
* **Scrapers, OPEN-622.** Utah's floor-vote lines (passed 3rd reading, concurrence, failed, conference final passage) are stored under the chamber that voted, read from the line's text. Before this fix they went under the office that holds the bill next.
* **Approved:** Ramon, 11-18. "Move Utah to new rules"; the combined Utah list: "Approve, after N/A fix".
* **No migration, no model change.** api-v3 does not read Utah's action rule, so its pages are unchanged by the extra core commit. It still must match the image's core.

## What to use instead of `7ab3303a`
* **Part A (Mac):** v68 records core `5c1455e1…` and scrapers `dca8e7a6…`. The `update-` note names both.
* **Part B1 (EC2 api-v3):** build with `DDP_CORE_SHA=5c1455e1679bbdac8f00fe050d57c0152e17c648`, and check with `check-core-pin-drift.py --image-core 5c1455e1679bbdac8f00fe050d57c0152e17c648 --container ddp-openstates-api-1`. Same gates otherwise.
* **Part B2 (`recompute-diff-order nm` dry run):** run it on core `5c1455e1`. The extra commit touches only Utah's action rule, so the expectation (about 129 corrected, 0 nulled) is unchanged.
* If main moves again before the build, use the commit the image records and say so in the `update-` note.

## What v68 does **not** do for Utah
**Stored Utah history is not touched.** The image only changes how new Utah scrapes are written. Two separate requests fix the stored history, each with its own GO, in Utah's silent window:
* `fix-ut-vote-chamber.py` (ddp-open-states #422, not merged yet): 1,172 actions;
* `os-text-extract relabel ut` (about 1,412 actions).

**New loads still use ddp-sync's own older core** (`44c3b8dc`) until SYNC-180's rebuild, so Utah's core rule applies on import only after that. SYNC-180's request will name `5c1455e1` or later.

## Not authorized
* Either Utah stored-data run.
* The broker's Utah switch: ddp-broker-py #767, its own request `5da5c42c` on the broker's notes branch.
* ddp-sync's rebuild.
* Anything not in `05a7643`.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
