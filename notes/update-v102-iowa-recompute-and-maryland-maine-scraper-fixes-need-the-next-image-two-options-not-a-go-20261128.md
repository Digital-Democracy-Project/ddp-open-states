# UPDATE (adds to `a4ed7d5`; still NOT a GO): **core #197 (Iowa) and scrapers #328 (Maryland) and #329 (Maine) are merged AFTER v101: they need the NEXT image (v102). Two options for Ramon.** 2026-11-28 (Mac side, Onboard New States)

## Facts (read with git today)
* v101 (built; task definitions `ddp-scrapers:103` and `ddp-scrapers-db:30`) carries **core `1f6b4ca86e0ad780e259bc6495f2a77549d59eae`** and **scrapers `cb8aef70d291fa24d622fca42b597cdeac001fd5`**.
* Merged since: **openstates-core #197 (OPEN-962, Iowa)**: core `main` is now **`1ffc3f5402dfed161e27bdd013ba37939a93b658`**; **scrapers #328 (OPEN-954, Maryland) `8d233f1b5b1245cbfacf080eaaefd9acd1722523`** and **#329 (OPEN-850, Maine) `d695c16a4fcea7c0e8ff4696bf0273c82244922b`**; scrapers `main` is now `d695c16a4fcea7c0e8ff4696bf0273c82244922b`. **None of these is in v101.**

## What I need from you
1. **The v101 plan stands for Georgia, Kentucky and Mississippi** (`a4ed7d5`, `dd2da9c`, `6d6928d`, `73ae55f`): none of them needs #197, #328 or #329. If Ramon wants to start with v101, those dry runs and steps are unchanged.
2. **Iowa needs v102 (core `1ffc3f54` or newer, scrapers `d695c16a` or newer):** `recompute-diff-order ia --dry-run` should then read **`is_bill_version` changed = 1,003** (all true to false; the Iowa amendment papers that are line edits; the 271 whole-text "strikers" stay versions), **1,608 comparison changes against today's stored rows** (1,003 removed, 394 documents re-based onto a real version, and 211 that depend on the pending Iowa text refresh of OPEN-913), **about 1,004 non-empty Iowa comparisons afterwards**, no non-Iowa change; commit only on Ramon's go. The Maryland (OPEN-954) and Maine (OPEN-850) scraper fixes also reach the data only with v102 and a rescrape. Iowa's dev LegBot sample waits for **v102 + this recompute + the Iowa text refresh commit (OPEN-913)**.
3. **Two options (Ramon's choice; I recommend A):**
   * **A: build v102 first, then do ONE rebuild of api-v3 (both hosts) and ddp-sync (EC2) on the final core `1ffc3f54...` and scrapers `d695c16a...`**; one pin check. v101's task definitions are already registered; a new build registers new revisions. Unblocks: everything in `a4ed7d5` plus Iowa's recompute, Maryland's and Maine's scraper fixes, in one pass; the Georgia, Kentucky and Mississippi dry runs then run on v102 (the same core plus #197). Cost: waiting for another image build before the rebuild.
   * **B: rebuild now on v101's core `1f6b4ca8...` and scrapers `cb8aef70...` (as in `a4ed7d5`), then build v102 later and rebuild api-v3 and ddp-sync a second time on `1ffc3f54...`.** Unblocks Georgia, Kentucky, Mississippi dry runs and the api-v3 vote key (`dedupe_key`, #81) and the Maine go-live path today. Cost: two rebuilds and two pin checks; Iowa, Maryland and Maine data fixes still wait for v102.
   Either way the order of `a4ed7d5` holds for the manifest: image live first, then ddp-open-states #520 is merged (I tell you), then the manifest rollout (it also turns Maine live: see `6d6928d`), then the Mississippi recompute.

## Not authorized
As in `a4ed7d5`: any commit; any scrape or re-import; any manifest rollout before the image and rebuild steps; any other state; `legbot_replica`; VoteBot's state list.

Tickets: OPEN-962, OPEN-954, OPEN-850, OPEN-673, OPEN-672, OPEN-674, OPEN-913; OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
