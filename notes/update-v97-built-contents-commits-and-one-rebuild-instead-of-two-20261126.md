# UPDATE (one suggestion, Ramon's call): **v97 is built; its real contents and commits; do the api-v3 and ddp-sync rebuild once, at v97's commits, instead of v96's then v97's.** 2026-11-26 ~05:15 UTC (Mac side, Onboard New States)

Follows `request-v97-scrapers-image-idaho-struck-text-…` (b8210af). Still **not a GO** for Idaho's steps; Ramon gives each go in your session.

## What I read (local `ddp-scrapers:v97` image on the Mac, built 00:59 EST = 05:59... (see image time below), read-only, nothing printed from the environment)
* **Core commit recorded: exactly `647bb3994ed819ba4194820b379147f525219479`**: the openstates-core #176 merge (OPEN-895, Idaho struck text). It includes #175 (OPEN-893) and #173 (OPEN-871). Idaho's reader in the image wraps the strike-line reader (checked in the image's `ddp_states/id.py`).
* **Scrapers commit: the image records none**, but `scrapers/ok/bills.py`, `ia/bills.py`, `hi/bills.py` and `ms/bills.py` are **byte-identical (same md5) to scrapers `main` `d0bd1826f8990f738ee626a7fe7ec01823a37264`**, which is what the build's clone reported. That main contains everything v96 had (#293, #294, #295, #296) plus OPEN-900 (Hawaii label fix, #297).
* **Not in this image:** scrapers **#298** (OPEN-899, Mississippi's wrapped-initial parser fix, not merged yet) and people #56 (a people-repo change, loaded separately). The Mississippi parser fix therefore needs a later image (v98).
* **Task-definition revisions:** I cannot read them; Ramon's script output has them (the PM relays); please take them from there.

## The suggestion (Ramon decides in your session)
v96's rebuild parts (api-v3 on both hosts, ddp-sync on EC2) have not started: they wait for Georgia and Maine. **Since v97 contains everything in v96 plus Idaho's and Hawaii's fixes, rebuild once with `DDP_CORE_SHA=647bb3994ed819ba4194820b379147f525219479` and `DDP_SCRAPERS_SHA=d0bd1826f8990f738ee626a7fe7ec01823a37264`** (api-v3 at that core on both hosts, ddp-sync on EC2), instead of v96's values and then again. Then, in order, as already approved or requested:
1. The Georgia `2026_ss` run and the Iowa `2026s1` run, with the v97 image (date-sorted actions apply to new Iowa data).
2. The Iowa re-import and the recompute dry run (v96 request, parts 3 and 4): **v97's core also carries the Idaho reader, which does not change Iowa.**
3. Idaho: `os-text-extract refresh-extraction id` dry run (expect 438 changed, 486 unchanged, 0 errors), then `recompute-diff-order id --dry-run`; commits hold for go notes (the v97 request).
4. Hawaii's label fix (OPEN-900, State Specific Handling's ticket) has its own steps; not part of this request.

## Not authorized
Any commit before a go note; scrapers #298 or any Mississippi rescrape (a later request, after v98); any other state's refresh or recompute; a manifest change; a ddp-sync restart beyond the rebuild.

Tickets: OPEN-895, OPEN-893, OPEN-894, OPEN-892, OPEN-900, OPEN-899; OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
