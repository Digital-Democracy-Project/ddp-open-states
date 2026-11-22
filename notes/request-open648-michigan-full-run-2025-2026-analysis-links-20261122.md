# REQUEST (not a GO): Michigan full run of 2025-2026, so every bill carries the bills its fiscal analyses name, as related links (OPEN-648), once the image holds scrapers #209. 2026-11-22 (Mac side, State Specific Handling)

**Not a GO.** Ramon's go comes in your session. **#209 is not merged yet;** gate 1 stays unmet until it is merged and built into an image. The Mac side will post the image note.

## Why
* Michigan publishes no companion list. Ramon decided on 2026-11-22 ("Store as related") that the bills a fiscal agency analyses together are stored as `related` links. The page says "This document analyzes HB5152, HB5153".
  * The label is the agency's own heading, "House Fiscal Agency Analysis" or "Senate Fiscal Agency Analysis".
  * They are never companions.
* **Measured** on the 4,013 cached Michigan pages: about **2,270 links on 765 bills**, all in 2025-2026.
* **Michigan's incremental runs re-scrape only bills whose last action changed**, so most bills would never get the links. Hence one full run of 2025-2026, the only session with polled bills (65 on the dev copy).
* **No scorecard changes:** the broker follows only `companion` links. The site's bill pages will list these as related items.

## Gates (stop and report if one fails)
1. **The running scrapers image contains #209's merge commit.** If it does not, this waits.
2. **Step 4 of `1f1e692` is done** (checkpoint `7310af7`): ddp-sync at core `7f531958`. Already met.
3. **Nothing Michigan is running:** no `mi` task in ECS, and `GET ddp:pipeline_lock:mi` is empty.
   * Michigan's site is firewall-protected; the run goes the scheduled way and nothing is retried by hand.

## The run (SYNC-181's trigger)
```
POST /ddp-sync/v1/trigger/openstates-scrape/mi?full=true&sessions=2025-2026
```
* **Answer:** 202, with `"full": true` and the session echoed. A 409 means wait, do not force.
* **How long:** about 6 hours. A full walk is about 3,750 bill pages at Michigan's 10 requests a minute (manifest `waf.requests_per_minute`).
* **Report:**
  * the run id and the image revision;
  * the collection's record, with `"mode": "full"`;
  * any firewall-block lines;
  * the load's final status, with bill and vote counts.

## Go/no-go after (read only, on RDS and through EC2 api-v3)
* **Michigan 2025-2026 related-bill links by type and by label.**
  * Before: **0**.
  * After: about 2,270 `related` links, and **no `companion`**.
  * Labels: only "House Fiscal Agency Analysis", "Senate Fiscal Agency Analysis", or the two joined with "; ".
  * Spot check: HB 5807 → HB 5805, HB 5806, SB 966.
* **Broker (no action asked):** Michigan's `BillRelation` count is unchanged.

## Not authorized
Any other state or session; any recompute; any broker change.

Tickets: OPEN-648, OPEN-634. Plan: PLAN-companion-lineage §5.3 (ddp-infra #561).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
