# Request: build the newest-action bill-list index on the production bill table, with a before and after (OPEN-484), 2026-11-04

**Ramon approved this on 2026-11-04 (/ask-me, his words): "Yes, build it on production and file a ticket to investigate the other 400ms"** (that ticket is OPEN-489; my phase-timing request `b76c23c` is its first step and is still open for you). api-v3 **PR #47** is merged (`16c5168b` on `Digital-Democracy-Project/api-v3` `main`). It adds one index, `opencivicdata_bill_latest_action_desc_idx ON opencivicdata_bill (latest_action_date DESC NULLS LAST, id)`, made only by `python -m api.search_projection ensure --bill-list-index`. Why: your 04:01 UTC baseline showed the endpoint's page query as a sequential scan plus sort (158 ms); on the Mac copy the matching index took it from 39 ms to 0.17 ms. **PR #48 (a count without its sort) is open: do not pull it.** The endpoint code did not change in #47, so **the running api container does not need to be recreated**: the index helps it at once.

## What the index build does to production (please read before running)
* It is **not concurrent**: it blocks writes to `opencivicdata_bill` for the build. About **0.1 s** on the Mac copy (87,489 bills, 7.8 MB, measured twice); production is not measured, expect well under a second. **Please record the real time of the command.**
* Before the build it waits for writers already on the table for at most **5 s** (`lock_timeout`). If one is still writing it stops with `canceling statement due to lock timeout`, **creates nothing**, and can simply be run again. It bounds the wait, not the build.
* Rollback: `DROP INDEX opencivicdata_bill_latest_action_desc_idx;` Nothing else depends on it.
* You already confirmed the connected role owns the bill table (`openstates_admin`).

## Gates
* **No scrape or archive import in flight** (no ECS task, no `run-scrape`), a quiet moment, away from 02:00, 02:30 and 03:00 UTC. Stop and report if a task is writing bills; do not wait it out.
* Nothing else changes: **no recreate, no restart, no refresh, no `ensure` without the flag** (a plain `ensure` is not asked for), no setting, no deploy of anything else.

## Steps
1. **Before (read-only):** from the broker web container (as in your 04:06 reply) time `GET /bills?sort=latest_action_desc&per_page=20` directly on api-v3, page 1 and page 500, five runs each, 1.5 s apart (median and max), and record the first 20 bill ids of page 1. Also run `bills_explain.py` once (`notes/api-v3-speed-20261104/`) for the page-query `Execution Time`.
2. **Bring the host's api-v3 source to `16c5168b` or later on `main`** (it must contain `ensure --bill-list-index`; it need not contain anything else new) and **build the api image**, as you did for earlier api-v3 releases. Do not recreate the running container. Save the running image id first.
3. **Build the index from the new image**, once: `docker compose -f <the host's compose file> run --rm --no-deps api python -m api.search_projection ensure --bill-list-index` (the form you used for `ensure` on 2026-10-30; always `--no-deps`, always the `api` service). Expected output: the usual `=== BILL SEARCH ENSURE: ddp_bill_search present ===` and then `=== BILL LIST ENSURE: opencivicdata_bill_latest_action_desc_idx created ===`. If it prints `canceling statement due to lock timeout`, report it, change nothing, and I will ask for a retry at another time.
4. **After:** `SELECT indexdef FROM pg_indexes WHERE indexname = 'opencivicdata_bill_latest_action_desc_idx';` shows `(latest_action_date DESC NULLS LAST, id)`. Repeat step 1's timings and compare the **first 20 bill ids of page 1 with the before** (they must be identical). Run `bills_explain.py` again: the page plan should now read the index (no `Sort` node).
5. **Reply** `reply-api-v3-build-the-bill-list-index-on-production-open484-20261104.md` with the image ids, the times (UTC), the command's real duration, the before and after tables, the plan nodes, and what you did not run. If any check fails, do not restart anything else: report first.

## Not asked
* No recreate of the api container, no `refresh`, no PR #48, no change to the broker.
* The OPEN-489 phase timing (`b76c23c`) is separate and still wanted.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
