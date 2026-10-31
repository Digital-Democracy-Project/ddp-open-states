# Report: api-v3 `aed937a` (OPEN-469, newest-action order across all jurisdictions) is LIVE on the EC2 host, 2026-10-31 23:31 UTC

Operator said go in this session ("Option A, run the api-v3 deploy now"). No rollback, no `ensure`, no `refresh`, no database change, `/opt/ddp-open-states` itself not touched.

## Before and after
| | before | after |
|---|---|---|
| api-v3 checkout HEAD | `dac69bc75ea039ebc52f73c779a4baf1172342a7` (clean) | `aed937a69e03628707ce3e0b37bce7446ee628db` (clean; `git merge --ff-only`; `dac69bc` is an ancestor, checked; only `api/bills.py` and `api/tests/test_bills_newest_action.py` differ) |
| `api` container started | 2026-10-31 20:43:36 UTC | 2026-10-31 23:30:59 UTC |
| `api` image ID | `c54094c0ed8c` | `145414bb6b51` |
| `ddp-openstates-redis-1` started | 2026-10-11 19:49:12 UTC | **unchanged** |
- **Rollback tag:** `ddp-openstates-api:pre-open469` = `c54094c0ed8c`. Not used.
- **Quiet window:** 0 non-health api requests and 0 ddp-sync non-health lines in the 10 minutes before; no new notes since your request. Command: `docker compose -p ddp-openstates-rds -f /opt/ddp-open-states/deploy/docker-compose.rds.yml up -d --build --no-deps api`, exit 0, 4 s. `/healthz` was not 200 for **about 6 s**, then 200.

## Smoke tests (read key, not printed)
- `GET /bills?sort=latest_action_desc&per_page=20`: **200** (was 400). `total_items` **77,688**, `max_page` 3,885. The 20 dates run newest to oldest (first three `2026-10-29T04:00:00+00:00`).
- `GET /bills?jurisdiction=ut&sort=latest_action_desc&per_page=20`: **200**, newest first (first `2026-03-26T21:24:57+00:00`).
- **Still 400, as required:** `/bills`, `/bills?sort=updated_desc`, `/bills?sort=latest_action_asc`, `/bills?sort=latest_action_desc&session=2025`.
- `/bills?jurisdiction=ut&sort=updated_desc&per_page=3`: 200, 3 results.
- `/jurisdictions/va?include=legislative_sessions`: 200, 33 sessions, all with `is_current` and `is_previous`.

## Undated bills last (step 4)
Last 6 pages read in order (108 bills): **73 have a blank `latest_action_date`, all at the end; no dated bill comes after a blank one.** The 73 and the 77,688 total are **the same as on the Mac**. Last dated date seen: `2023-01-03T05:00:00+00:00`.

## Timing (step 5; five runs each; from the host, through localhost)
- `page 1`: **median 613 ms, max 649 ms.** (The very first call right after the restart took 1.9 s and the first UT call 1.4 s; those were cold calls.)
- `page 500`: **median 825 ms, max 888 ms.**
- `jurisdiction=ut` page 1: **median 74 ms, max 81 ms.**
These are slower than your Mac numbers (about 103, 124 and 27 ms) by roughly six times, but page 1 is well under your 2-second line, so I did not treat it as a stop. I did not check why the host is slower (the database here is a different server from the Mac's).

Nothing else changed. Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
