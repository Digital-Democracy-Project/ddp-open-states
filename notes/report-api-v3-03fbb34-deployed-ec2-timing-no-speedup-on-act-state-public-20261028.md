# Report: api-v3 03fbb34 (OPEN-398) deployed on the EC2 host. Little or no speedup for the common words; results of the common words change a lot

Prod agent, Wed 2026-10-28 00:50 UTC. The operator said "Option A, do both now". Output in `/home/bitnami/ops/open398-20261028T0046Z/` and the id lists in `/home/bitnami/ops/open398-ids-{before,after}-20261028.json`.

## What ran
* Gates before the rebuild: no non-health, non-search api-v3 request in 5 min, VoteBot no query, in-flight 0, WA at 02:30. api-v3 `d5b37dc` to **`03fbb3443a76dfe211c0c6b7c2d0eedee3a636f5`** (fast-forward, clean tree). Old log saved.
* `docker compose -p ddp-openstates-rds -f deploy/docker-compose.rds.yml up -d --build --no-deps api`: **4 s**, healthy; new container created 00:46:08, image `7bfeb59cbff7`. **Redis start time unchanged** (2026-10-11T19:49:12Z).
* Verified: `grep -c FTS_RANK_POOL /app/api/ddp_search.py` = **5**; `GET /ddp/enrollment` 200 with `manifest_mtime` unchanged (00:13:35.470006); `/bills` 200, embedding ledger 200, `/healthz` 200, broker search through Django 200; no error or traceback in the log.

## Timings: `GET /ddp/search`, all nine jurisdictions, 5 runs each, median of the response's `elapsed_ms` (production api, warm)
| word | before | after | first-20 ids same as before | same position |
|---|---|---|---|---|
| act | 1023.2 | 1039.9 | 1 | 0 |
| state | 994.9 | 1017.1 | 2 | 0 |
| school | 333.1 | 270.3 | 10 | 3 |
| health | 510.5 | 394.3 | 9 | 0 |
| public | 611.6 | 638.1 | 4 | 0 |
| hemp | 75.8 | 76.7 | 20 | 20 |
Each query returned 20 results (the "text" list; the number is capped at 20, so it is not a total count).

## What this says
* **No speedup for act, state and public** (within run-to-run noise: act runs 1008 to 1139 ms after against 984 to 1051 before), and about a 19 to 23% speedup for school and health. The Mac's dev numbers (act 620 to 495) are not reproduced on production; production is about twice as slow as the Mac to begin with, so the 5,000-bill pool does not look like the dominant cost for the all-state "act" and "state" queries here. I have not profiled it.
* **The top 20 changes a lot for the common words** (act 1 of 20, state 2, public 4 unchanged), as you expected; `hemp` is identical.
* I did not roll back (not asked to; rollback is `git checkout d5b37dc` plus the same rebuild). Whether to keep it is for Ramon.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
