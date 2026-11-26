# UPDATE (no new ask beyond the v97 update `00eafbf`): **v97's revisions, and what is merged but not in v97.** 2026-11-26 ~05:40 UTC (Mac side, Onboard New States)

Numbers from Ramon's script output (relayed by the PM; I cannot read task definitions): **tag v97, `ddp-scrapers:99` and `ddp-scrapers-db:26`, core `647bb3994ed819ba4194820b379147f525219479`.** New tasks now launch v97 (previous v96 = `ddp-scrapers:98` / `ddp-scrapers-db:25`). Rollback per the script: deregister `ddp-scrapers:99` and `ddp-scrapers-db:26`. Image checks passed (Python 3.13.18, imports OK, Utah smoke exit 0).

* The script's reminders: **api-v3 must be rebuilt at core `647bb399` on both hosts** (the core-pin drift check fails until then), and **EC2's ddp-sync rebuilt with `DDP_CORE_SHA=647bb3994ed819ba4194820b379147f525219479` and `DDP_SCRAPERS_SHA=d0bd1826f8990f738ee626a7fe7ec01823a37264`** (the commit I matched by files; my 05:15 note has the evidence).
* **Merged but NOT in v97:** scrapers **#298** (OPEN-899, Mississippi's wrapped-initial parser fix; merge `1c02aae8`) and people **#56** (Beth Waldo's "Luther-Waldo" alias; merge `1eea3bce`). They are for a later request (the people load, then v98, then four targeted Mississippi rescrapes); **not authorized now.**

Everything else in `update-v97-built-…` (00eafbf) and the v96/v97 requests stands.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
