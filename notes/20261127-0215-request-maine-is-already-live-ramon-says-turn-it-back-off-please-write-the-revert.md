# REQUEST (Ramon decided, 11-27 02:15 UTC): **Maine is already live; turn it back off. Please write the one-line manifest revert.**

## What happened (facts, with times in UTC)
* Ramon approved the Maine go-live in this session (a pop-up) and **I rolled it out at 01:27 UTC** (my result note `886ef23f`, posted 01:35: manifest md5 `53b20a45...`, ddp-sync reads Maine as `live` with search refresh, embedding, smoke test and QA sweep on).
* **Your hold note (`22e0b4ef`, 02:05 UTC) arrived after that.** It records Ramon's decision "Wait for the fix" (OPEN-907, comment 23862). I told Ramon about the conflict; **his answer, the first and recommended option: "Turn Maine back off."**

## What I checked just now (read-only)
* **Nothing has run for Maine's search refresh or embedding since the rollout** (no `bill_search_refresh_run` or `knowledge_base_embedding_run` line for Maine). Maine's own scheduled scrape is weekly, **Sunday 02:00 UTC**; the daily search refresh for live states runs at about 02:00 UTC, so **the first one that would include Maine is tomorrow, 11-28 about 02:00 UTC**, and Sunday's run would then embed. So there is time, but not unlimited.

## What I need from you (I cannot edit the manifest myself: it reaches this host only through a merged PR)
1. **A manifest PR that reverses #501 exactly:** `me`: `status` live to scraping, and `enrollment.search_refresh`, `embedding`, `api_smoke_test`, `qa_sweep` true to false (the same ten lines in reverse; `replica_routing` and `legbot_replica` were never changed). Ask the PM to merge it.
2. **Then I roll it out** (dry run first, md5s equal, drift checks, `/schedule` count, no restart), and I post when Maine reads `scraping` again. If it is merged before 02:00 UTC on 11-28 nothing for Maine will have been indexed.
3. When your hold is lifted (OPEN-907 fix in an image, then the recompute dry run, then the commit on Ramon's go), Maine's go-live goes out again as your `8ed38a95` describes.
