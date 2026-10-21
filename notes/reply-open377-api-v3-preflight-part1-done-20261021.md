# REPLY: OPEN-377 Part 1 (read-only) done on the EC2-broker host. Every gate passes; nothing changed. Waiting for GO on Part 2 (2026-10-21 UTC)

Run 04:52 to 04:54 UTC, 2026-10-21, after the operator's go in this session. Nothing was pulled, built, recreated or restarted. The only secret touched was the current RDS credential, read from Secrets Manager (the same secret ddp-sync's own `resolve_rds_database_url()` uses) for one read-only query; it was not printed or written anywhere. Reason: this host's saved `RDS_DATABASE_URL` stopped authenticating at about 03:10 UTC today (rotated credential).

## G1 (starting state): PASS
`/opt/ddp-open-states/api-v3`: branch `main`, `HEAD` `ba0b646`, `git status --short` clean. After `git fetch`, `git log --first-parent HEAD..origin/main` = exactly **`a2f5db8` (PR #32)**; the full range is three commits: `a2f5db8`, `d4a1a6c`, **`92d107c`** (your note lists the feature commit as `92dd0e7`; the real one is `92d107c`, a typo in the note). `origin/main` = `a2f5db8`.

## G2 (rollback point and quiet): PASS
* Running container `ddp-openstates-api-1`: image **`cc7deeaaa1a9`** (tag `ddp-openstates-api:local`), up 5 days, healthy, **restarts 0**, policy `unless-stopped`. Existing rollback tags on the host: `pre-open381` `8b7df04cc29f`, `pre-open352`, `pre-open361`, and older.
* api-v3 quiet: the last 5 minutes of its log contain only `/healthz`.
* **Next ddp-sync jobs (this host):** today **05:00 UTC bill-document archives for VA and WA**; then 2026-10-22 00:30 scrape cadence review, 02:30 WA scrape, 03:00 people pull and USA scrape, 05:00 MI and NC archives. So Part 2 should not land between about 04:55 and 05:30 UTC today (archives read api-v3); after that the next gap is the whole day. The recreate is about 17 s; the broker's search also reads this api-v3 (`/ddp/search`), so a topic or keyword search during those seconds can return `partial` (not an error).

## G3 (baseline, before): as expected
From inside the ddp-sync container with its api-v3 key (this host's api-v3, `10.0.0.11:8002`), Utah:
| query | result |
|---|---|
| `GET /bills?jurisdiction=Utah&per_page=1` | 200, `total_items` **1,021** |
| `...&vote_updated_since=2099-01-01T00:00:00%2B00:00` | 200, **1,021** (the parameter is ignored today) |
| `...&document_updated_since=2099-01-01T00:00:00%2B00:00` (control) | 200, **0** |
| `...&vote_updated_since=2026-10-01T00:00:00Z` | **200**, 1,021 (ignored today; after the deploy it must be 400) |
Also, for reference: `document_updated_since=2026-10-01T00:00:00Z` already returns **400** `datetime must be in ISO-8601 format, try YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS` today, which is the behaviour the new parameter must copy.

## G4 (RDS, read-only; the numbers the API must match after the deploy)
Query as written, run 2026-10-21 04:53 UTC:
* Cutoff `2026-06-01T00:00:00+00:00`: **Utah 739 bills / 1,917 votes (newest vote update 2026-06-22); Virginia 2,201 bills / 11,553 votes (newest 2026-08-25)**. Identical to the Mac replica's 739 and 2,201.
* **Cutoff 7 days back (`2026-10-14T04:53:19+00:00`): no rows**: neither Utah nor Virginia has any vote updated in the last 7 days (newest are 06-22 and 08-25). So a 7-day post-deploy check would only prove 0 equals 0. More useful fresh cutoffs, with their expected answers: **`2026-08-01T00:00:00+00:00`: Utah none, Virginia 6 bills / 35 votes; `2026-06-20T00:00:00+00:00`: Utah 5 bills / 10 votes, Virginia 2,201 / 11,553.** (An empty result for Utah at the first cutoff means the API should return `total_items` 0.)

## G5 (which instance the broker uses)
The broker's `DDP_OPENSTATES_API_ROOT` is `http://10.0.0.11:8002`: **this host's own api-v3 container, directly, not the ddp-api proxy**. `OPENSTATES_SERVICE_URL` on the ddp-api host is not visible from here (I cannot see that host), so I cannot say which instance sits behind the proxy.

## Not done / not checked
Part 2 (not authorized); `OPENSTATES_SERVICE_URL`; I did not test `vote_updated_since` against any other state. Waiting for Ramon's GO for Part 2.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
