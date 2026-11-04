# Reply: api-v3 bill list and search, production baseline (OPEN-484, OPEN-485). Read-only, 2026-11-04 04:01 to 04:06 UTC, at the user's go

Running api: container `ddp-openstates-api-1`, image `5659b12c601a` (api-v3 checkout `72e6d21f71`), started 2026-11-03 20:56:33 UTC. Host load 0.5 to 0.9 on 4 cores. Nothing was started alongside (the Pennsylvania/Louisiana archive trial waits until this was done, by the user's choice). Nothing changed: no `ensure`, no index, no restart, no deploy; PR #47 and #329 not pulled. No secrets printed.

Full printed output of steps 1 and 2: `notes/api-v3-speed-20261104/prod-scripts-output.txt`.

## Step 1: `bills_explain.py` (production database `ddp-openstates`)
- 87,489 bills; `opencivicdata_bill` 51 MB heap, 87 MB with indexes.
- **Owner of the table = the connected role** (`openstates_admin` both), so an `ensure` could create an index there.
- Page 1 (newest action): Execution Time **152, 158, 166 ms (median 157.6)**. Plan: a parallel sequential scan of all bills, a hash join with sessions, jurisdictions and organizations, then a top-N sort, 2 workers; every page read is a buffer hit (6,840 hits, 0 reads).
- Middle page (offset 43,744): **500, 466, 514 ms (median 499.6)**; the sort spills to disk (`external merge`, 31 MB, temp read 1,992 / written 3,897 blocks).
- Count: **77, 83, 80 ms (median 79.9)**, parallel index-only scan.
- Page 1 wall time from the container, 5 runs: **180, 219, 142, 146, 145 ms**.
- Settings: `shared_buffers` 1,950,336 kB (about 1.9 GB), `work_mem` 32 MB, `random_page_cost` 1.1, `effective_cache_size` 3,900,680 kB (about 3.7 GB), `max_parallel_workers_per_gather` 2, PostgreSQL **16.15**. Cache counters: 4,076,131,660 hits to 121,109,060 reads.

## Step 2: `search_legs.py`
- `ddp_bill_search`: 77,719 rows, 10 jurisdictions; **103 MB heap, 738 MB total, 216 MB indexes**.
- "health care" (12,650 candidates): full-text leg **320 ms median** (first 329); fuzzy-title leg 297 ms; people leg 53 ms.
- "tax" (10,562 candidates): full-text leg 152 ms (first run 2,258 ms: a cold first call); fuzzy-title 129 ms; people 38 ms.
- "pelosi" (19 candidates): 2 ms, 5 ms, 74 ms.
- `EXPLAIN (ANALYZE, BUFFERS)` of the "health care" full-text leg, run 1 and run 2: **326 ms and 328 ms**, bitmap heap scan, **67,396 shared buffer hits, no reads in either run** (the Mac copy read about 67,000 pages from outside the cache). So production's cache holds it.

## Step 3: direct HTTP to api-v3 (from the broker web container to `10.0.0.11:8002`, the broker's own key from its settings, never printed; 1.5 s apart)
| call | HTTP | median ms | max ms | runs |
|---|---|---|---|---|
| `/bills?sort=latest_action_desc&per_page=20` page 1 | 200 | **642** | 666 | 666, 648, 626, 642, 637 |
| same, page 500 | 200 | **924** | 1,037 | 978, 924, 889, 1,037, 912 |
| same, `jurisdiction=us` page 1 | 200 | **354** | 798 | 798, 380, 354, 350, 346 |
| `/ddp/search` "health care" (13 jurisdictions, bill+person) | 200 | **700** | 747 | 747, 693, 692, 706; `elapsed_ms` 686.9 |
| "tax" | 200 | **346** | 360 | 350, 340, 342, 360; `elapsed_ms` 342.0 |
| "pelosi" | 200 | **93** | 105 | 96, 90, 90, 105; `elapsed_ms` 96.2 |

The bill list from the endpoint is **about four times the database time** (642 ms against 152 ms): the rest is in api-v3's own work after the query (not separated).

## Corrections and one open difference to know about
- **My first attempt at the HTTP search calls got HTTP 400.** I sent `types=bill,representative`; api-v3 wants `bill,person` (the broker translates). I fixed it and reran; the numbers above are the rerun. No other call was affected.
- **My BROKER-427 reply reported the api-v3 leg of search for "health care" at about 3.5 s (4 runs, 02:25 UTC). I cannot reproduce that.** Now it is 0.69 to 0.75 s through the same broker function (`_openstates_leg`, 4 runs: 753, 692, 690, 694 ms; "pelosi" 90 to 96 ms), through the broker's client (706 ms median, one 1,662 ms), and directly (700 ms). At 02:25 the Nebraska archive task was writing to the same database and the WA scrape was about to start. The database was **not** busy: CPU averaged 5 to 7%, maximum 15% in that window, and the CPU credit balance stayed full at 864. So I do not know why it was slow then. It may have been a one-off or a first-call cost. I would treat 0.7 s as the production figure and the 3.5 s as unexplained.
- The "tax" full-text leg's first call took 2.3 s (cold), then 152 ms.

## Step 4: facts
- Database: RDS instance `ddp-openstates`, class **db.t4g.large** (read from AWS), PostgreSQL 16.15. I did not read its memory or disk type directly; the class is the burstable t4g.large.
- `ddp_bill_search` is 738 MB in all; every page of the "health care" plan was already in `shared_buffers` (1.9 GB), so it fits.
- Host load during the run: 0.5 to 0.9 (4 cores).

## Not run, or run differently
- Step 3 ran from the broker web container, not from the host shell, so the key never passed through me. It used the same address and the same key.
- I did not run anything that creates an index and did not look at PR #47.
