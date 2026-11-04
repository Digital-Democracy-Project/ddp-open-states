# Request (read-only): production baseline for api-v3's newest-action bill list and for search (OPEN-484, OPEN-485), 2026-11-04

Your 2026-11-04 reply to BROKER-427 (`ddp-broker-py` `notes/ops-handoff`) showed two slow spots that live in api-v3, not the broker: the website's bill list (`/api/bills/`, 1.6 s unfiltered) and the api-v3 part of search (3.5 to 4 s for "health care"). On the production-copy database on the Mac I found likely causes; this request is to measure the same things on production **before** anything is changed. **Nothing here changes anything: no `ensure`, no index, no restart, no deploy, no setting.**

## What dev showed (Mac, production-copy database: 87,489 bills, 2,637,775 person votes)
* **Bill list:** `GET /bills?sort=latest_action_desc` orders by `latest_action_date DESC NULLS LAST, id`. The table's only date index is ascending with no `id`, so Postgres reads and sorts every bill per page: page query **39 ms**, the page's total `count(*)` another **43 ms**. A matching index on a scratch copy took the page query to **0.17 ms**. Your 2026-10-31 timing of this endpoint on the host was **613 ms** (OPEN-469 report); the Mac's 103 ms is the same endpoint. The broker's call adds the rest of the 1.6 s you saw (not yet separated).
* **Search "health care":** the full-text leg is about **405 of the 540 ms**. The index finds the 12,643 matching bills in 1 ms; fetching them to rank costs the rest (about 67,000 pages read for 12,643 rows: each row's `fts` vector holds title, abstract and capped bill text, average 5 KB, 633 MB of the table's 981 MB). Even on the second run about 28,000 pages come from outside Postgres's 128 MB buffer cache. **My guess (not measured on production):** a smaller or colder cache or slower disks make this about six times slower; your numbers will say.

## Gates and limits (please keep to these)
* **SELECT and `EXPLAIN (ANALYZE, BUFFERS)` only** (it runs the SELECT, writes nothing). Quiet hour of your choosing, away from 02:00, 02:30 and 03:00 UTC and from any refresh or scrape that is importing. Stop and report if a query runs over 30 s or the host looks stressed.
* **No secrets in your reply.** The scripts print none (no keys, no database address). Do not paste `DATABASE_URL`, a key or a token.
* The scripts are in `notes/api-v3-speed-20261104/`. Read each before running. They import api-v3's own modules, so run them **inside the api container** on the host that serves production traffic (your section 4 of the runbook says which), e.g. `docker exec -i <api container> python - < bills_explain.py`. Tested on the Mac's api image and the production-copy database; each ran in under a minute there.

## Steps
1. **`bills_explain.py`:** builds the endpoint's own page and count queries and prints the plan nodes, buffers and Execution Time for page 1, a middle page and the count (3 runs each), plus: the owner of `opencivicdata_bill` against the connected role (**if they differ, say so first**: it decides whether `ensure` could ever create an index there), the table's indexes and sizes, `shared_buffers`, `work_mem`, `random_page_cost`, `effective_cache_size`, `max_parallel_workers_per_gather`, the server version, and the database's cache counters.
2. **`search_legs.py`:** times each search leg for "health care", "tax" and "pelosi", counts the full-text candidates, prints the full-text leg's plan with buffers twice (cold then warm), table sizes and the same settings.
3. **Direct HTTP timing, from the host to api-v3 (not through the broker), with the host's own key:** `GET /bills?sort=latest_action_desc&per_page=20` page 1, page 500, and `&jurisdiction=us` page 1; five runs each, median and max. And `GET /ddp/search?q=health+care&jurisdiction=<the jurisdictions the broker passes>`, `q=tax`, `q=pelosi`: four runs each, the `elapsed_ms` the response carries and the wall time.
4. **Tell me, if you can read it:** the database instance class and memory (if RDS: the class), whether `ddp_bill_search` (981 MB) can fit in the buffer cache or the instance memory, and the host's load during the run.

## Reply
`reply-api-v3-bill-list-and-search-production-baseline-20261104.md` on this branch: the printed outputs as they came, the commit and image id of the running api, the times (UTC), what you did not run and why. I will compare against the Mac copy and post it on OPEN-484 and OPEN-485.

## Not asked (separate, later, needs Ramon's go)
* **No index.** The fix proposed for OPEN-484 is api-v3 PR #47 (open, not merged): `ensure --bill-list-index`, which needs this baseline and Ramon's go first. **Do not pull or run it.** `Digital-Democracy-Project/ddp-open-states` PR #329 is a docs correction, also not to be pulled.
* No change for search yet: the options (a smaller candidate set, a cheaper ranking input, more cache) change what visitors see or what the database needs and are for Ramon to choose from your numbers.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
