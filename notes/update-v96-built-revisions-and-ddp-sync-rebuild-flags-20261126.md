# UPDATE (no new ask beyond the v96 request): **v96 is built; the numbers and the ddp-sync rebuild flags for Part 1 and Part 2.** 2026-11-26 ~00:30 UTC (Mac side, Onboard New States)

This adds to `request-v96-scrapers-image-release-api-v3-rebuild-iowa-reimport-recompute-dry-run-open892-893-894-20261125.md` (a57c0d9). Nothing in that request's scope changes, and it is still **not a GO**; Ramon gives the go in your session.

## Part 1 is done by Ramon (his build output, relayed by the PM)
* Tag **v96**; task-definition revisions **`ddp-scrapers:98`** and **`ddp-scrapers-db:25`**; core **`4af91c906f09dfbbc17d11f2743bf0ff3fdfb8a5`** (OPEN-893).
* The image was built before openstates-core **#176** (Idaho struck text, merge `647bb399`) merged, so **v96 does not contain #176**. That goes in the next image (v97): see `request-v97-…` (separate note).
* **Please confirm** the recorded scrapers commit and that the new revisions carry the stored database login as `ddp-scrapers-db:23` did (names and lengths only, no values). Tell Ramon in your session.

## Part 2: ddp-sync's rebuild on EC2 needs two build arguments (SYNC-180 / SYNC-188)
`DDP_CORE_SHA=4af91c90` and `DDP_SCRAPERS_SHA=<the scrapers commit the v96 image records>`: so ddp-sync's own copy of the core and scrapers matches the image. Read the scrapers commit from your Part 1 confirmation. api-v3 is rebuilt at core `4af91c90` on both hosts as before.

## Also merged since the request
Wave 1 manifest PR **#498** (Oregon and Wyoming `replica_routing` and `legbot_replica` true; merge `a69063ac`). **Not part of this release: no rollout yet.** A separate rollout request follows after the Wyoming sample re-run; do not act on #498 until then.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
