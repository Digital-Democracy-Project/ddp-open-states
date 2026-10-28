# Report: api-v3 on the EC2 host reloaded from the reverted main (`f9dde91`). Verified; timings back to baseline; all top-20 ids identical to the pre-#36 lists

Prod agent, Wed 2026-10-28 02:07 UTC. The operator said "Option A, go now" in my session. Output in `/home/bitnami/ops/open398-revert-20261028T0159Z/`; ids in `/home/bitnami/ops/open398-ids-{before,after,reverted}-20261028.json`.

## What ran
* **Before:** re-read all four branches (nothing new). api-v3 checkout HEAD `03fbb3443a76dfe211c0c6b7c2d0eedee3a636f5`, clean; container started 00:46:09; Redis started 2026-10-11T19:49:12Z. **`ddp_bill_search_recency_idx` does not exist in the production database (count 0)**, as you expected.
* **Quiet window:** at 02:00 api-v3 was busy (about 60 `GET /bills` a minute from the VPN hub), so I **waited** for the note's quiet condition: my watcher saw **0 non-health api-v3 requests in 3 minutes at 02:03:47**; I re-checked at 02:04:33 (0 in 1 and 3 minutes, in-flight 0, next launch WA 02:30). Old log saved.
* **02:04:50** fast-forward to **`f9dde9192784f6ac78d599161e8d9d318968caa5`** (HEAD confirmed; 3 files, 11 insertions, 128 deletions). Then `docker compose -p ddp-openstates-rds -f deploy/docker-compose.rds.yml up -d --build --no-deps api`: **3 s**, healthy; new container created 02:04:52, started 02:04:53, image `6e3a0d7e0e10` (the same image ID as the 00:13 deploy: same tree as `d5b37dc`). **Redis start time unchanged.**

## Verification
* `FTS_RANK_POOL` count **0**; `recency` count in `search_projection.py` **0**.
* `jurisdictions.yaml` mount present: mtime identical inside and on the host. `GET /ddp/enrollment` **200**, `manifest_mtime` **2026-10-28T00:13:35.470006+00:00** (unchanged).
* `/bills` 200, embedding ledger 200, `/healthz` 200, broker search through Django 200. The new log's only "error" match is uvicorn's own start-up config line (the key `errorlog`), no traceback.

## Timings, median of `elapsed_ms` (all nine jurisdictions, 5 runs, warm)
| word | pre-#36 (00:46 before) | with #36 (00:46 after) | reverted (02:05) | first-20 ids same as the pre-#36 list |
|---|---|---|---|---|
| act | 1023.2 | 1039.9 | 1004.6 | **20/20** (same position 18) |
| state | 994.9 | 1017.1 | 1003.7 | **20/20** (same position 13) |
| school | 333.1 | 270.3 | 303.7 | **20/20** (20) |
| health | 510.5 | 394.3 | 492.0 | **20/20** (20) |
| public | 611.6 | 638.1 | 607.7 | **20/20** (20) |
| hemp | 75.8 | 76.7 | 85.5 | **20/20** (20) |
Back near the first set, as you expected. The ranking is the same set per word as before; for `act` and `state` a few results sit at slightly different positions (ties, I assume, not checked).

Nothing else changed. api-v3 on this host is now at `f9dde91` with the enrollment endpoint.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
