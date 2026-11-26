# Status 11-26 17:35 UTC: Iowa 2026s1 session lines (you asked for these first); run still collecting

* Run `ia-eb086dbc03e2` (`ia?full=true&sessions=2026s1`, v97 task `ddp-scrapers:99`), triggered 16:27:02 UTC, collecting for about 1 hour 8 minutes. Read from the task's own log (CloudWatch), not from ddp-sync.
* **Session lines: the special session is found.** The scraper's arguments read `bills: {'session': '2026s1'}` and `votes: {'session': '2026s1'}`.
* **What it is doing now:** walking Iowa's bill list (General Assembly 91) and logging `Skipping HF 521: it belongs to 2025` for each bill not in the special session; at 17:29 it was around HF 521/522. It is slow because it fetches each bill's history page to decide. Two warnings so far: `Skipping SF 538` (16:47) and `Skipping SF 2320` (17:02): `no session of General Assembly 91 holds its first dated action (None, companion None)`. I have not looked into them.
* No end counts yet. I will post them when the pipeline finishes. After it: the v96 Iowa re-import (`ia?full=true&sessions=2025,2026,2026s1`; I will first check that list against the sessions the manifest and production hold), then the recompute dry run, no commit.
