# Request: deploy api-v3 `aed937a` (OPEN-469, bill list ordered by newest action across all jurisdictions) on the EC2 host: build and recreate `api` only, no table change

Written by the Mac session at Ramon's instruction, 2026-10-31 about 23:25 UTC. **Nothing here has been run on production.** Ramon decides the time; please pick a quiet window and say when. The Mac (:8002) is already on `aed937a` and verified (refreshed 23:20 UTC, checks below).

## Why
api-v3 PR #43 (merged 2026-10-31 21:36 UTC) lets `GET /bills?sort=latest_action_desc` work **without a jurisdiction** (newest action first, bills with no action date last), and gives bills that share a day a fixed order (by bill id), so a browse list can be paged through. It is two small edits in `api/bills.py` and a new test file. The broker will send this sort for its bill list in a later ticket; nothing reads it yet, so this deploy changes nothing a visitor sees by itself.

## What is different from the 10-31 OPEN-467 deploy
**Same shape: no schema change, no `ensure`, no `refresh`, no `ddp_bill_search` change.** The sort reads `opencivicdata_bill.latest_action_date`, which already has an index (`opencivicdata_bill_latest_action_idx`). Do **not** run any bill-search steps.

## Steps
0. **Before:** record the api-v3 checkout HEAD (expected **`dac69bc`**, from your 20:44 UTC report), the `api` container's start time, `ddp-openstates-redis-1`'s start time and the `api` image ID. Tag the current image **`pre-open469`** (the rollback).
1. **Fast-forward only** `/opt/ddp-open-states/api-v3` to **`aed937a`**. It is a straight fast-forward from `dac69bc` (two commits: `227804c` the change, `aed937a` the merge; only `api/bills.py` and `api/tests/test_bills_newest_action.py` differ). Stop and report if it will not fast-forward. **Leave `/opt/ddp-open-states` itself alone.**
2. **Recreate only `api`:** the same command as 10-31: `docker compose -p ddp-openstates-rds -f /opt/ddp-open-states/deploy/docker-compose.rds.yml up -d --build --no-deps api` (always `--no-deps`, always the `api` service). Quiet window as before. Check `GET /healthz` and that `ddp-openstates-redis-1`'s start time is unchanged.
3. **Smoke test (read key; do not paste it).** Each should answer as written:
   * `GET /bills?sort=latest_action_desc&per_page=20` answers **200** (before this deploy it was 400, "either 'jurisdiction' or 'q' required"); record `total_items`, and check the 20 `latest_action_date` values run newest to oldest;
   * `GET /bills?jurisdiction=ut&sort=latest_action_desc&per_page=20` answers 200, newest first;
   * **unchanged, must still be 400:** `GET /bills`, `GET /bills?sort=updated_desc`, `GET /bills?sort=latest_action_asc`, and `GET /bills?sort=latest_action_desc&session=2025` (a session still needs a jurisdiction);
   * `GET /bills?jurisdiction=ut&sort=updated_desc&per_page=3` answers 200 (another order, unchanged);
   * `GET /jurisdictions/va?include=legislative_sessions` still answers 200 with `is_current` / `is_previous` on every session (the 10-31 flags, untouched).
4. **Undated bills last:** read the **last page** of `GET /bills?sort=latest_action_desc&per_page=20` (`max_page` from page 1). Report how many bills on it and the pages before it have a blank `latest_action_date` and confirm that **no dated bill comes after a blank one** (read the last 6 pages in order). On the Mac: 77,688 bills, 73 with no action date, all 73 at the very end. A different count on production is not a failure; report it.
5. **Timing:** `GET /bills?sort=latest_action_desc&per_page=20` for page 1, page 500 (or the middle page if there are fewer) and `jurisdiction=ut` page 1, five runs each, median and max. Mac, with no network hop: page 1 about 103 ms, page 500 about 124 ms, deepest page about 168 ms, UT about 27 ms. **Report only; do not treat a slower number as a failure unless page 1 is over about 2 seconds**, which would mean the index is not being used (then stop and report).

## Rollback
Re-tag `pre-open469` and recreate `api`. Nothing in the database changed, so there is nothing else to undo.

## Stop conditions
Anything that is not as written (a checkout that will not fast-forward, a 500, a smoke test that fails, page 1 over about 2 seconds): stop, change nothing further, report. No retry and no rollback beyond the image re-tag above without authorization.

## Not authorized
`ensure`, `refresh` (full or per jurisdiction) or any other change to `ddp_bill_search`; any database change; fast-forwarding `/opt/ddp-open-states` itself; any change to the broker, ddp-sync, VoteBot or LegBot, a flag or schedule change, a scrape, archive or embedding run, anything in the Fargate task definition.

## Order against other releases
Independent of the broker release (BROKER-369) and of the ddp-sync release (SYNC-139). The broker's use of this sort is a separate, not yet filed ticket; it waits for this to be live and is not part of this request.

## Reply
A `report-api-v3-open-469-...` note: the before and after checkout HEADs, image IDs and times, the status codes from step 3, the blank-date result from step 4, the timings from step 5, whether the Redis start time was unchanged, and the `pre-open469` tag.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
