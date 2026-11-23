# REQUEST (not a GO): the next scrapers image after v79, for OPEN-649 (Arizona's own links between bills). Scrapers main is `f33da22f`; core is unchanged at `42b48982`. 2026-11-23 (Mac side, State Specific Handling)

**Not a GO.** Ramon builds the image (`deploy-scrapers-image.sh`).
* v79 is the image after v78 (`9e2caaa`, `a9fbb18`, `35b5cda`, `22d7100`, `4f42180`, `7b7eec0`). It takes scrapers main `0292506c`, which does not include this change.
* This request does not change v79 or its release order.

## What is new since v79's scrapers (scrapers main `f33da22fad2eb9d3213025ac9d1f3a0ea5b8f2cb`)
| Merge | What |
|---|---|
| #227 (OPEN-649, `f33da22f`; this session) | Arizona stores azleg's own links between bills, from the bill feed's `NowPartOf`: "Identical to" as `companion`, "See" as `related`, with azleg's words as the label |

* **Ramon's decisions:**
  * "Yes, same rule", 11-20: Arizona's "Identical to" counts as a companion.
  * "Approve" (recorded on OPEN-649 by the PM session): the scorecard change measured on the dev copy, in the re-import request `request-open649-arizona-reimport-57th-2nd-regular-20261123.md`.
* **No migration and no new setting.** Core is unchanged, so there is no api-v3 or ddp-sync step.
* **New links appear only on Arizona bills scraped after this image.** Arizona's polled bills are all in 57th-2nd-regular, and that session needs the separate re-import request.

## After the build
* **Mac side checks** the image's scrapers commit is `f33da22f` or later, and that `/opt/openstates-core/DDP_CORE_COMMIT` is `42b48982`.
* **Prod side:** please report the image tag and task-definition revisions.

Tickets: OPEN-649, OPEN-536. Plan: PLAN-companion-lineage §5.3.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
