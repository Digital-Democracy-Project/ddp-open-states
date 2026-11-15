# GO: search rebuild on EC2 (part 3 of `a55a798`), including Pennsylvania (OPEN-533)

**Ramon, 2026-11-15 ~23:50 UTC (/ask-me), asked when to rebuild search: "Now, including Pennsylvania (Recommended)".** That is the go for part 3 of `request-go-manifest-7149b40-la-ne-labels-api-v3-8214db7-search-20261115.md` (your `cb5b25b` held it), with **`pa` added**.

## What I need from you
1. **Gate:** finish before **02:15 UTC Monday**, or start after Pennsylvania's 04:00 nightly has loaded; avoid wa 02:30 and usa 03:00. api-v3 is at `8214db7` (your `cb5b25b`).
2. For each of **pa, us, ut, va, az, mi**, one at a time:
   `docker exec ddp-openstates-api-1 python -m api.search_projection refresh --full --jurisdiction <x>`
   Report each run's summary line and time.
3. **Checks (use the search route, not `/bills?q=`):** `GET /ddp/search?q=precondition&jurisdiction=pa`. HB 2625 must **not** be among the results (the struck §9301 wording is only in the old PDF text). `GET /ddp/search?q=education&jurisdiction=pa&per_page=2` must return results (Pennsylvania was not in search before). Report one result count for us and ut too.

## Not authorized
Any other state; a manifest or `search_refresh` change; ddp-sync, the broker, any scrape, archive or recompute.

## Mac side
I run the same six rebuilds on the Mac's api-v3 and the same checks.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
