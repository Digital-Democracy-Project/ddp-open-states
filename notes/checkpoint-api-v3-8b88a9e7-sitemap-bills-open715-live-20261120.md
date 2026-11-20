# CHECKPOINT (done): api-v3 `8b88a9e7` live on EC2 (OPEN-715, the sitemap's bill list). 2026-11-20 19:07 UTC (EC2 prod agent)

Reply to `2ed36c98a`. Ramon approved in session (pop-up: "api-v3 8b88a9e7 now"; the broker `a430881d` part: "after the fill").

**Release:** rollback tag `ddp-openstates-api:pre-open715` = 9bd654db9902 (the previous image). Checkout `/opt/ddp-open-states/api-v3` fast-forwarded `3a8d165e` -> `8b88a9e74ad05fcadba4381fa114e4be819b4c16` (origin main; one merge #75, 3 files `api/ddp_sitemap.py`, `api/main.py`, test; HEAD clean). Rebuilt with `DDP_CORE_SHA=10f32ce08088e544e88d54ec64aa325aea80756f`, `up -d --no-deps api` 19:05:43 to 19:05:55; compose 10 s; **API down about 6 s**; healthz 200 before and after.

**Checks:**
- core-pin drift check (`--image-core 10f32ce0…`): **exit 0**, "the scrapers image and 1 api-v3 container(s) all run core 10f32ce0…".
- **New route through the broker's own client** (`openstates_search._get('/ddp/sitemap/bills', {'jurisdiction':'us','limit':1000,...})`, 40 pages): **39,432 rows, 40 pages, 1,050 with a vote**, fields `['has_votes', 'identifier', 'latest_action_date', 'latest_vote_date', 'ocd_bill_id', 'session', 'title']` (as you listed), **10.5 s** in all (while the broker's first legislator fill was reading api-v3 at the same time).
- `{'jurisdiction': 'zz'}` raised `OpenStatesSearchUnavailable` ("API response unsuccessful").
- **Not run:** the session-table spot check (`us` current 119 / previous 118): I do not have the exact call from `a907d4f` at hand; tell me the call and I run it.

**Effect on the broker's fill:** the legislator fill was running (it started 18:35 UTC); at 19:05:42-43 its api-v3 reads hit `ConnectionResetError` and retried (two retry warnings); the process kept running. I will report its summary line (the `failed:` count) when it ends.

**Nothing else changed.** Next on my side: the broker `a430881d` (BROKER-558) release after the fill ends (a web recreate would kill the running fill), then your Mac half.
