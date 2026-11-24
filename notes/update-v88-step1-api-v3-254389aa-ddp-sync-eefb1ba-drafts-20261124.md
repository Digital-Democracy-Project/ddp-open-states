# UPDATE (not a GO) to `e30bb8e` step 1 (the v88 core rollout): build **api-v3 from main `254389aa`** and **ddp-sync from main `eefb1ba`**. They add the Montana drafts follow-ups (OPEN-861). 2026-11-24 ~19:30 UTC (Mac side, Onboard New States)

**Not a GO.** Everything else in `e30bb8e` and `a0e5d64` stands. Core stays `0d373728`.

## Why the commits move
* **api-v3 main `254389aa8dbb754834b5600ad752b514284d7a9f`** (was `903013d`): it adds #79 (OPEN-870), a separate switch `exclude_introduced_drafts` that leaves a draft out of lists, counts, search, hydrate, the sitemap and the embedding ledger once a bill replaces it, and #80 (lint only). `bill_types_only` is unchanged and implies it. **No schema change.** An api-v3 that doesn't know the switch ignores it, so the order of the rebuilds doesn't matter.
* **ddp-sync main `eefb1ba588227bd8ae8a48d67b4d830451caff16`** (was `e7f4b35`): it adds #309 (SYNC-190): the knowledge-base embedding reads send the switch. LegBot's artifact scan is untouched (it already sends `bill_types_only`). #310 (SYNC-191, the cleanup) is **not merged yet**.
    * Since `e7f4b35` that is only #309. No `.env`, yaml or schedule change.
    * Keep `DDP_CORE_SHA=0d373728…` and `DDP_SCRAPERS_SHA` as in `e30bb8e` / `a0e5d64`.

## What changes in the order
* **Step 1 of `e30bb8e`:**
    * EC2 and Mac api-v3: build from api-v3 main **`254389aa`** with core `0d373728`;
    * EC2 ddp-sync: ff `/opt/ddp-sync` to **`eefb1ba`** (not `e7f4b35`).
* **After step 1:** check that Montana's draft **LC 858** (`ocd-bill/4dffc95d-382a-4813-a0f8-247fe430711f`) is left out of a list that asks for the switch, and still opens by its id: `GET /bills/ocd-bill/4dffc95d-…` answers 200, and a list with `exclude_introduced_drafts=true` for Montana 2027 has 1 fewer bill than without it.
* **The draft cleanup** (SYNC-191, ddp-sync #310) is a **separate, later request** once #310 is merged: a dry run first, on Ramon's go. Not part of v88.
* **The broker's sitemap change** (#827) is in the broker request (`e472203f`, D3). It works before api-v3 carries the switch and only takes effect after this rebuild.

## Not authorized
Unchanged.

Tickets: OPEN-861, OPEN-870, SYNC-190 (OPEN-146).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
