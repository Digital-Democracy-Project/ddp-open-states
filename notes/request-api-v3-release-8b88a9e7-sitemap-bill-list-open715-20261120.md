# REQUEST (not a GO): api-v3 release at main `8b88a9e7` (OPEN-715, the sitemap's bill list). EC2, then the Mac; core unchanged at `10f32ce0`. 2026-11-20 (Mac side, SEO Upgrades)

**Not a GO.** It waits for Ramon's go in your session.

**Order.** This is the first of two releases. The broker's `a430881d` (BROKER-558, request on ddp-broker-py `notes/ops-handoff`) reads this route, so **api-v3 goes first**. The website's sitemaps (NEXT-283, ddp-next `eb6ca162`) need both.

## What it does
A new read-only route, **`GET /ddp/sitemap/bills?jurisdiction=<code>&after=<cursor>&limit=<1..1000>`**. It requires the API key, like `/ddp/embedding/ledger`. It lists every bill of a jurisdiction:
* fields: the bare OCD id, session, number, title, last action date, newest vote date, and whether the bill has a vote;
* 1,000 bills a page, keyset-paged by bill id;
* two queries a page.

The broker builds the website's sitemap lists from it, at most once an hour per state.

**Nothing else changes:** no existing route, no database change, no setting.

**Measured on the Mac's copy:**
* US: 39,382 bills in 40 pages, 4.0 to 4.4 s, slowest page about 220 ms, 1,050 with a vote (the same as a direct count);
* MA: 11,932 bills, 1.1 s.

## Exact code
- **api-v3 main `8b88a9e74ad05fcadba4381fa114e4be819b4c16`** (merge of #75). It is the **only** change since your deployed `3a8d165e` (your checkpoint `a907d4f`). `git log --first-parent 3a8d165e..8b88a9e7` shows one merge, 3 files: `api/ddp_sitemap.py`, `api/main.py` (2 lines, the router) and its test.
- **Core unchanged:** `DDP_CORE_SHA=10f32ce08088e544e88d54ec64aa325aea80756f`.
- No migration, no setting, no `.env` change, no new package.

## When
**Any quiet minute.** Only the broker reads EC2's api-v3 (your `a907d4f`, Ramon's reminder). A 6 to 8 s restart can at most make one broker call fail and retry. Avoid the 05:00 to 07:00 UTC scorecard chain.

## EC2 steps, after the go
1. **Rollback point:** tag the running api-v3 image `:pre-open715`.
2. **Release** by the api-v3 release procedure, as for `3a8d165e`:
   - fast-forward the checkout to `8b88a9e7` (HEAD confirmed, clean);
   - rebuild with `DDP_CORE_SHA=10f32ce0…`;
   - `up -d --no-deps api`.
3. **Checks:**
   - the core-pin drift check exits 0;
   - healthz answers 200;
   - the session table from `a907d4f` is unchanged (spot-check `us` current `119`, previous `118`);
   - **the new route, through the broker's own client** (no key is printed). On the host:
     ```
     docker exec <broker web> python manage.py shell -c "
     from ddpbroker.search import openstates_search as s
     rows, after, pages = [], None, 0
     while True:
         b = s._get('/ddp/sitemap/bills', {'jurisdiction': 'us', 'limit': 1000, **({'after': after} if after else {})}, timeout=60)
         rows += b['results']; pages += 1; after = b['next_after']
         if after is None: break
     print(len(rows), pages, sum(r['has_votes'] for r in rows), sorted(rows[0]))"
     ```
     **Expect** about 39,400 rows in about 40 pages and about 1,050 with a vote. Your replica's numbers may differ a little from the Mac's; report them. The fields must be `['has_votes', 'identifier', 'latest_action_date', 'latest_vote_date', 'ocd_bill_id', 'session', 'title']`.
   - **Also** `{'jurisdiction': 'zz'}` must raise the client's unavailable error (api-v3 answers 400).
4. **Report** the numbers, the time it took, and the release time (UTC).

**Rollback:** retag `:pre-open715` as the running tag, then `up -d --no-deps api`. Nothing reads the new route until the broker release.

## The Mac half (mine, after your checkpoint)
`refresh-api-v3.sh` at the same core, pulled to `8b88a9e7`, with its own rollback tag; then the drift check and the same route answer from `:8002`.

## Not authorized
Any core change; any ddp-sync, broker or scrapers change; any data edit; any other host or service.

Tickets: OPEN-715 (for NEXT-283 and BROKER-558, epic NEXT-278).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
