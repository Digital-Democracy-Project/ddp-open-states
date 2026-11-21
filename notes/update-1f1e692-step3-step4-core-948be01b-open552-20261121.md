# UPDATE to `c1d800d` (steps 3 and 4 of `1f1e692`): the image's core is now `948be01b` (adds #127, OPEN-552), not `130c40bd`. 2026-11-21 19:50 UTC (Mac side, State Specific Handling)

**Not a GO.** The image still waits for Ramon's approval of OPEN-642's Florida list (the decision in `c1d800d`).

## What changed
* openstates-core #127 (OPEN-552) is merged as **`948be01bebcc140ff80cb6776fcb22c22305a1f1`**, after Ramon's "Approve and go" on Arizona's list (OPEN-552 comment 22255). Core main is now one merge past `c1d800d`'s pin. The build clones main, so **the step 3 image is built at `948be01b`**, and step 4 uses `DDP_CORE_SHA=948be01bebcc140ff80cb6776fcb22c22305a1f1` (or whatever the build log shows).
* **What #127 adds:** Arizona's `classify_action`. The bare "FAILED" action line no longer carries `failure`. No migration, no other state.

## What it does once the image is live
* **New Arizona imports** apply the rule from then on. Stored Arizona history keeps its old labels until the relabel, which has its own request and runs in the silent window.
* **The mixed labels in between are harmless:**
  * The broker's Arizona reader (`_read_arizona`, removed only later by BROKER-490) still drops the same label when it reads, so bill stages read the same.
  * Arizona's scorecards no longer read action labels (BROKER-491).
  * The OPEN-552 measurement on the dev copy found 0 votes and 0 scorecard files changed with the labels applied.
* **Imported bills' `updated_at` moves as on any import.** No bill events are expected, because the reader gives the same stage. The relabel's own request still checks for 0 bill events in its window.

## Everything else in `c1d800d` stands
* the table of scrapers and ddp-open-states heads (check the build log's clones);
* the Florida decision before building;
* step 2 check 3d;
* the follow-ons waiting on this image.

The relabel request (`os-text-extract relabel az`, fresh dry run first) comes as its own note after the image is registered: the relabel needs code at a core with #127.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
