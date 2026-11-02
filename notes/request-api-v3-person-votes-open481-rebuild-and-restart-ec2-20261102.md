# Request: rebuild and restart api-v3 on the EC2 host so it serves `GET /people/{id}/votes` (OPEN-481), 2026-11-02

Ramon merged api-v3 **PR #44** at 20:02 UTC (merge commit **`b3148ac`** on `Digital-Democracy-Project/api-v3` `main`): a new read-only route, **`GET /people/{person_id}/votes`**, the votes one person cast, newest first. The Mac's api-v3 (:8002) was rebuilt and restarted at 20:05 UTC by Ramon's own session; **the EC2 instance has not been**. Your reply `b0763ab` (20:11 UTC) recreated api-v3 there with `--no-build` on the same image `145414bb6b51`, so it still holds the old code (that recreate was for the manifest; nothing is wrong with it). This request is the code release, and it is what the broker's new votes endpoint (BROKER-410, ddp-broker-py #651, merged, not released) waits on.

## What the release is
One new module (`api/person_votes.py`) and two lines in `api/main.py`. **No migration, no new table or index, no setting, no `.env` change.** The route reads `opencivicdata_personvote` through the existing `voter_id` index. **Do not** run `ensure` or the bill-search refresh (nothing touched `ddp_bill_search`). It needs a **new api image** (the code is baked in), the same kind of release as OPEN-469 (api-v3 #43), which you did on this host on 2026-10-31 (report `2a588e6`); use the same procedure.

## What I need
1. **Gates:** nothing in flight (no ECS task, no `run-scrape`), a quiet moment, away from 02:00, 02:30 and 03:00 UTC. Save the api log and note the running image id (`145414bb6b51`) first, for recovery.
2. **Bring the host's api-v3 source to `b3148ac`** (it must contain `api/person_votes.py`), **rebuild the api image, recreate only the `api` service** (`--no-deps`, so the database container is never considered). Do not touch ddp-sync or the broker.
3. **Read-only checks afterwards**, each with the value read:
   - The running image id is **not** `145414bb6b51`; `docker exec <api container> python -c "import api.person_votes"` exits 0; the container is healthy.
   - The route exists: without a key `GET /people/ocd-person/x/votes` answers **403** (the key check), and a path that does not exist, `/people/ocd-person/x/nothing`, answers **404**. That pair proves the route is registered.
   - With the host's own key, for Jay Adams (`ocd-person/1a75f967-8f35-40aa-8b0a-990a135e70cb`, NC House): `GET /people/<id>/votes?per_page=50` should give `pagination.total_items` **481** and `summary.counts` **yes 459, no 9, absent 9, abstain 4**, **if the database this api reads holds his votes** (the Mac replica does). If the numbers differ, report what you read and do not change anything. Please also note the time of that one call (a page of 50 took about 6 ms in the database on the Mac).
   - The existing routes still answer: `GET /bills?jurisdiction=nc&per_page=1` is 200; `/ddp/enrollment` still shows 13 jurisdictions; the broker's routed list is unchanged (`AZ FL MI NC US UT VA WA`).
   - The api log shows no traceback since the restart.
4. **Reply** with the image id now running, the time (UTC), the checks above with their values, and the rollback you hold. If a check fails, do not restart anything else; report first.

## Not asked
- **No ddp-sync restart, no broker release.** The broker release for BROKER-410 is `/broker-deploy`, Ramon's step, after your reply. Until then the broker's new endpoint would answer 503 on every call, which is harmless today (no website page calls it yet).
- Nothing about the Stage 2 drafts (ddp-sync #262, ddp-open-states #322): still not to be pulled.
- The Mac is Ramon's side and is done.

No deadline beyond "before the broker release"; BROKER-410 and NEXT-123 (the website's Votes tab) wait on it.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
