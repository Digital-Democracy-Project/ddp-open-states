# Reply: api-v3 recreated from `main` (`14433582`) and the bill-list index built on production, measured in three stages (OPEN-484, OPEN-489). Done, no check failed. Written 2026-11-04 19:40 UTC.

Run at the user's go in this session ("let's fulfill the remaining dev agent requests while it's still quiet", then "Yes, run it now, all stages" at 19:23 UTC, after I read the request and the two new scripts). Gates at 19:24 UTC: no ECS task, nothing in flight, no ddp-sync job in 10 minutes, host load 0.3; at 19:29 (just before the index) the same.

## The three stages, side by side (production, `GET /bills?sort=latest_action_desc&per_page=20`, from the broker web container to api-v3 `10.0.0.11:8002`, 15 runs 1.5 s apart, median ms)
| stage | page 1 | page 500 | US page 1 | count statement | page statement | whole request (server-side) |
|---|---|---|---|---|---|---|
| **BEFORE** (19:24 UTC, image `5659b12c601a`) | **642** | **906** | **348** | **474 ms** (sort inside: True) | 143 ms | 637 ms |
| **AFTER 1**: recreated, no index (19:27 UTC) | **231** | **511** | **161** | **62 ms** (sort inside: False) | 134 ms | 217 ms |
| **AFTER 2**: recreated + index (19:29 UTC) | **87** | **107** | **55** | **64 ms** | **2 ms** | 86 ms |
- Same first-20 ids fingerprint in every stage: **`e6b714850c66`**; `total_items` **87,489** in every stage (the same fingerprint you measured on the Mac).
- Min/max for page 1: before 593/690; after 1 **217/1,523** (the max is the first calls after the restart); after 2 84/90. (Page 500 after 1 max 1,859, same cause.)
- `bills_explain.py` after the index (saved in `notes/api-v3-speed-20261104/prod-after2-bills-explain-output.txt`): **page 1 Execution Time 0.27 / 0.19 / 0.18 ms (median 0.2 ms)**, plan reads `Index Scan using opencivicdata_bill_latest_action_desc_idx`, **no Sort node**; middle page (offset 43,744) 125 ms (it must skip 43,744 rows); count 76 ms (parallel index-only scan); page 1 wall time from the process **6 to 7 ms**. Before (my baseline `1f82173`): page 1 158 ms, middle page 500 ms, count 80 ms.
- What is left in the endpoint is the count: about 62 to 64 ms of the 86 ms. Not changed by the index.

## The broker's lists, quiet host (same script as before, through the public name; median ms, first call in brackets)
| call | before the recreate (19:17 UTC) | after the recreate and index (19:31 UTC) |
|---|---|---|
| bills list p1 | 1,595 (1,614) | **297** (432) |
| bills list US | 637 (607) | **150** (146) |
| legislators list p1 | 273 (178) | **177** (1,504) |
| legislators list US | 122 (121) | 126 (150) |
| openstates-bills US list | 89 | 79 |
| openstates-bills back to back x4 | [87, 86, 83, 84] | [77, 76, 73, 70] |
Note: the "before" column is the 19:17 run I took right after the broker deploy (`f155c273`); I did not repeat it at 19:24, nothing but my own api tests ran in between. For the bills list through the broker: **api-v3's part now 87 ms of the 297 ms**, so the broker's remaining part is about **210 ms** (BROKER-425). **OPEN-484's acceptance (the unfiltered page well under 300 ms):** api-v3's own answer is 87 ms; the website's path through the broker is **297 ms median, which is under 300 but not "well under"** (first call 432 ms). I leave the call to you.

## What I did (UTC)
1. Gates and saved state, 19:24: running image `5659b12c601a` (kept, also tagged `ddp-openstates-api:pre-open484`), api log saved to `/home/bitnami/ops/log-archive/ddp-openstates-api-pre-recreate-20261104T1924Z.log.gz`.
2. **api-v3 source** (`/opt/ddp-open-states/api-v3`): `git merge --ff-only 144335823c7403369f9f01618160ca769eca9be9` (from `72e6d21f71`; 7 files, +284 / -3; `origin/main` was exactly that commit). `order_by(None).count()` is in `api/pagination.py`.
3. **Image built and `api` recreated only** (`docker compose -p ddp-openstates-rds ... up -d --build --no-deps api`, 19:26:59): compose exit 0 in 4 s (cached layers); **api-v3 was down about 6 seconds** (healthz polled every 0.5 s); `healthz` 200 at 19:27:11; healthy. **New image `5247cecb337c`** (full id `sha256:5247cecb337ce3617d90252a546e1a5cba9f0326dd524280b25f305e863464f1`), container started 2026-11-04 19:27:03. The redis container was not touched (started 2026-10-11 19:49 UTC, unchanged; **this host's api-v3 reads the RDS database directly, so there is no database container to compare**).
4. **Checks after the recreate:** image id is not the saved one: yes; `'order_by(None).count()' in inspect.getsource(api.pagination)` prints **True**; `GET /healthz` **200**; a request without a key (`/bills?jurisdiction=nc&per_page=1`) **403**; with the broker's own key **200**; `/ddp/enrollment` **200, 13 jurisdictions** (keys `manifest_mtime`, `jurisdictions`); person-votes for Jay Adams (`ocd-person/1a75f967-...`, NC House): **200, `total_items` 485, counts yes 462 / no 9 / absent 9 / abstain 0 / not voting 5**, the first call took **633 ms** at 19:27:46 (cold after the restart). That is the same reading I reported on 11-02 (485, not the 481 the request expected); unchanged by this release, not investigated. API log since the restart: **0 tracebacks, 0 errors**.
5. **Index built once**, 19:29:35: `docker exec ddp-openstates-api-1 python -m api.search_projection ensure --bill-list-index` printed `=== BILL SEARCH ENSURE: ddp_bill_search present ===` and then **`=== BILL LIST ENSURE: opencivicdata_bill_latest_action_desc_idx created ===`**. **Real duration of the command: 3.11 s wall time** (this includes starting Python and the `ddp_bill_search` check; I did not time the index creation on its own). No lock timeout. Index size **7,840 kB**.
6. `SELECT indexdef FROM pg_indexes WHERE indexname = 'opencivicdata_bill_latest_action_desc_idx';` → `CREATE INDEX opencivicdata_bill_latest_action_desc_idx ON public.opencivicdata_bill USING btree (latest_action_date DESC NULLS LAST, id)`. As specified.

## Final state
api-v3 on this host: source `14433582` (#47 and #48), image `5247cecb337c`, healthy, 0 errors in the log; index present. Rollback if wanted (not used, nothing failed): re-tag `ddp-openstates-api:pre-open484` (`5659b12c601a`) as `local` and recreate `api` with `--no-deps`; `DROP INDEX opencivicdata_bill_latest_action_desc_idx;` if the index should go (the old code works with it).

## Not run
- No plain `ensure`, no `refresh`, no ddp-sync change, no broker change (the broker release `f155c273` with #660 and #661 was done earlier today under its own request: Checkpoint E `de677d66`).
- The "database container's start time unchanged" check: not applicable on this host (RDS); redis start time shown instead.
- BEFORE for the broker's lists was the 19:17 run, not a new one (above).
