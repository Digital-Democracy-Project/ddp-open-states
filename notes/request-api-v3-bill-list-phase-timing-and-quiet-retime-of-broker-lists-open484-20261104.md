# Request (read-only): where the other ~400 ms of api-v3's bill list goes, and a quiet-host re-time of the broker's lists (OPEN-484, BROKER-424, BROKER-425), 2026-11-04

Thank you for the 04:06 UTC reply. It showed that api-v3's newest-action bill list answers in **642 ms** on production while its page query takes **158 ms** and its count **80 ms**: about **400 ms is outside both queries**. On the Mac copy the steps outside the queries take about 2 ms in total, so the production gap is not explained yet. **Nothing here changes anything: no `ensure`, no index, no restart, no deploy, no setting.** api-v3 PR #47 (the index) is merged but **not to be run**; PR #48 (a count without its sort) is open and **not to be pulled**.

## Gates and limits
* **Read-only.** Quiet hour; stop and report if a call runs over 30 s. No secrets in your reply: the script prints none.
* Run **inside the api container** on the host that serves production, as before: `docker exec -i <api container> python - < bills_phases.py` (file: `notes/api-v3-speed-20261104/bills_phases.py`; read it first). It repeats what `GET /bills?sort=latest_action_desc&per_page=20` does, step by step, and times each step (build the query, the count round trip, the page query and row load, rows to response objects, JSON), seven runs. It skips the key check on purpose. Tested on the Mac copy: total 118 ms, of which the count 77 ms and the page query 38 ms.

## Steps
1. **`bills_phases.py`**, once, and again after a one-minute pause (a cold and a warm run). Paste the printed table as it came.
2. **Same script, one more number:** from the same container, time `python -c "import time; t=time.time(); from api.db import SessionLocal; db=SessionLocal(); db.execute(__import__('sqlalchemy').text('select 1')).fetchall(); print(round((time.time()-t)*1000), 'ms: first connection plus select 1')"` three times, and then `select 1` again on an already-open session (a loop of 20 on one session, median). This separates a connection cost from query cost. (It reads the API's own connection settings; it prints no credentials.)
3. **Quiet-host re-time of the broker's lists.** The 1.6 s (`/api/bills/?page=1`) and the legislator list numbers from the 02:20 UTC run came from the window in which api-v3 itself behaved abnormally. Please re-run `timing_prod_nosearchdiscovery.py` from your BROKER-427 reply, the same way, now (only the rows for `bills list p1`, `bills list US`, `legislators list p1`, `legislators list US` matter; the rest can run as before).

## Reply
`reply-api-v3-bill-list-phase-timing-20261104.md` on this branch: the outputs as they came, the times (UTC), what you did not run. I will post the split on OPEN-484 and the re-timed broker numbers on BROKER-424 and BROKER-425.

## Not asked
No index, no deploy, no restart. The index step (`ensure --bill-list-index`) still needs Ramon's go and is not part of this.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
