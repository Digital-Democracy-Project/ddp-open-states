# Reply: api-v3 `b3148ac` (OPEN-481, `GET /people/{id}/votes`) is LIVE on the EC2 host (answers `5119954`), 2026-11-02 20:40 UTC. **One check differs from what you expected: Jay Adams's numbers.**

**The operator told me to do the release as written** (report-first on any failure).

- **Gates:** 0 ECS tasks, no real `run-scrape` process (my first count of 3 was my own command line matching itself; re-checked: 0), 20:39 UTC. **Before:** log saved (`api-v3-pre-open481-20261102T2039Z.gz`); the running image was `145414bb6b51`, now tagged **`ddp-openstates-api:pre-open481` (the rollback)**.
- **Source and build:** `/opt/ddp-open-states/api-v3` fast-forwarded from `aed937a` to **`b3148acb20`** (clean; `api/person_votes.py` present, `main.py` includes the router). `docker compose ... build api` finished in 2.5 s (cached layers; the new code layer rebuilt) to **image `31d95356e4ba`**.
- **Recreate:** `up -d --no-deps --no-build --force-recreate api` at 20:39:38 UTC; **healthy at 20:39:55 (about 17 s)**. Only `api` was recreated; Redis, ddp-sync and the broker were not touched.

## Checks, with values
- **Image:** `31d95356e4ba` (not `145414bb6b51`). `import api.person_votes` exit **0**. Healthy.
- **Route registered:** no key: `/people/ocd-person/x/votes` **403**; `/people/ocd-person/x/nothing` **404**.
- **Jay Adams** (`ocd-person/1a75f967-8f35-40aa-8b0a-990a135e70cb`), `?per_page=50`, host's key used inside the ddp-sync container (never printed), via the mesh address `10.0.0.11:8002`, first call 20:40:03 UTC:
  - **DIFFERENT from your expectation. Read: `pagination.total_items` 485 (you expected 481); `summary.counts` yes 462, no 9, absent 9, abstain 0, "not voting" 5 (you expected yes 459, no 9, absent 9, abstain 4).** The counts add up to 485, and 485 matches `total_items`, so the route is consistent with itself. **What I did not check:** why it differs from the Mac (I did not compare any rows). The differences are yes +3, abstain -4, a new "not voting" bucket of 5, total +4. I changed nothing.
  - 10 pages of 50 (`max_page` 10). Result keys: `bill, id, option, vote_event, voter_name`.
  - **Timing (end to end from the ddp-sync container over the mesh, not database time):** first call after the restart **2.163 s**, then 1.395 s, then **0.090 s** and **0.082 s** on repeats. The slow ones are the first hit on each of 4 workers; warm is under 0.1 s.
- **Existing routes:** `GET /bills?jurisdiction=nc&per_page=1` **200** (`total_items` 2,343, 0.027 s). `/ddp/enrollment` **13 jurisdictions**, `manifest_mtime 2026-11-02T20:11:13.237093+00:00` (unchanged; the key is `manifest_mtime`). **Broker routed list unchanged: AZ FL MI NC US UT VA WA** (fresh fetch).
- **Log:** 0 real `Traceback` lines since the restart (one `error` hit was the gunicorn start-up config line containing `errorlog`). 0 nginx 5xx on the broker in 6 minutes.

**Not done, as you said:** no ddp-sync restart, no broker release (BROKER-410 is Ramon's `/broker-deploy`), the Stage 2 drafts untouched.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
