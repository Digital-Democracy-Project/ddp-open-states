# Result 11-26 19:35 UTC: Iowa 2026s1 DONE; the v96 Iowa re-import is started

## Iowa `ia?full=true&sessions=2026s1` (run `ia-eb086dbc03e2`)
* Triggered 16:27:02 UTC; collection done 19:20:41; load into RDS 19:20:48 (cloud_scrape 10,424 s); archive done 19:22:51; pipeline `done`, `failed=0`, `archived=True`, 10,549 s (2 h 56 min). Ran on the v97 collection task (`ddp-scrapers:99`); the load ran on a v97 or v98 db revision with the same core.
* **Special session found and loaded (production, read-only):** `2026s1` "2026 Extraordinary Session": **7 bills, 4 vote events, 12 versions**. Others unchanged by this run: `2025` 2,358 bills, 763 vote events, 3,575 versions; `2026` 1,912 bills, 640 vote events, 3,055 versions; empty sessions `2023s1`, `2024`, `2027`, `2028`.
* My reading of the 11-24 miss, as you asked: the 11-24 trigger carried `sessions=2026,2026s1` without `full`, and the 20:15 restart resumed it; `2026s1` never started (production held no `2026s1` bills before today). This run, started with `full=true` and its own session list, did load it. I did not read the 11-24 run's log to prove it.
* The scraper warnings I mentioned (SF 538, SF 2320: `no session ... holds its first dated action`) are in the task log; I have not looked into them.

## The v96 Iowa re-import: STARTED 19:29:39 UTC
* `ia?full=true&sessions=2025,2026,2026s1` answered 202 with `full: true`. Session-list check you asked for: **production holds data for exactly `2025`, `2026` and `2026s1`** (the four other Iowa sessions are empty); the manifest sets no explicit Iowa session list (`session_arg: null`), so the manifest cannot differ. Runs on the v98 image (`ddp-scrapers:100`); same core as v96, so date-sorted actions and the version-note stages (v96 contents) apply.
* Still to do after it: the recompute dry run (`recompute-diff-order ia --dry-run`), no commit; ddp-sync's rebuild at the v98 scrapers commit (waits for no lock to be held; Hawaii also holds one now).
