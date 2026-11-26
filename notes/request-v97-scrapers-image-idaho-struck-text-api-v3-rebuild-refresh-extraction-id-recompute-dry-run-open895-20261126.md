# REQUEST (not a GO): **release v97: a new scrapers image carrying the Idaho struck-text fix, an api-v3 rebuild at the new core, then Idaho's text refresh and checks.** 2026-11-26 ~00:30 UTC (Mac side, Onboard New States)

**Not a GO, and not ready to build yet:** the PM and I are batching anything else that lands before Ramon builds, to avoid a v98 right behind it. I will post an `update-` note with the final contents and commits before he builds. Ramon gives the go in your session naming the final note. **Start only after v96's parts are finished** (the Iowa re-import and its checks), so Idaho's chain does not overlap Iowa's.

## What v97 contains so far
| Change | Repo and merge | What it does |
|---|---|---|
| OPEN-895 | openstates-core #176 (merge `647bb399`, **core `main`**) | Idaho's PDF reader drops struck-out words, using Alabama's strike-line reader (OPEN-530). Measured on the Mac's archive copy: 438 of 924 Idaho 2026 documents (427 versions) lose struck text; none gains a character; 0 errors; the only reader-table entry that differs from clean main across all 131 states is `id`. |
Scrapers `main` now: `248c2571c8cbbf4a6dbe275b19cb68f84a390640` (same as v96). The image takes core's `main` at build: **read the recorded core commit and report it; stop if it is not `647bb399` or newer.**

## What I need from you (after the go)
1. **Part 1: the image.** Ramon builds it (your role cannot launch the build). Report the new task-definition revisions and the recorded scrapers and core commits.
2. **Part 2: api-v3 at the new core on both hosts**, and EC2's ddp-sync rebuilt with `DDP_CORE_SHA` and `DDP_SCRAPERS_SHA` for the new image (as in the v96 update note).
3. **Part 3: `os-text-extract refresh-extraction id`, dry run first.** Expect **438 changed, 486 unchanged, 0 errors**. Report the exact lines; **do not commit**; the commit holds until a go note.
4. **Part 4: `recompute-diff-order id --dry-run`** with the new core (the comparisons change). Report the exact lines; commit holds until a go note.
5. After each: tell me; I verify on the Mac replica: H 561 reads "(b)" where it read "(c) (b)", the struck "(h) Official flags of Idaho colleges, universities, and public schools" is gone, H 570's struck ", or" is gone, no unrelated Idaho text changes, Stage 3 gates. Then the Idaho dev LegBot sample is re-run (my step, through `/onboard-state`).

## Not authorized
Any other state's refresh or recompute; a scrape or re-import; a manifest change; `replica_routing`/`legbot_replica` for Idaho (it stays false until its sample passes); a ddp-sync restart beyond the rebuild; any commit before a go note.

Tickets: OPEN-895; OPEN-664 (Idaho go-live); OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
