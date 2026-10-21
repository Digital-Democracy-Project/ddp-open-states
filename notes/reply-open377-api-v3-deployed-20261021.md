# REPLY: OPEN-377 Part 2 done: api-v3 `a2f5db8` is live on the EC2-broker host; every check passes (2026-10-21 UTC)

Operator said "Option A, deploy at 05:35 UTC" in this session after Ramon's GO (`76ce302a`). api-v3 only: no other container, no database, no ddp-sync, ddp-api or broker change, no setting change.

## Before
* **05:35 UTC:** the 05:00 VA and WA archives had finished at 05:02 (`fargate task done` 121.4 s and 121.1 s; both `archiver_triggered_legbot_no_sessions_touched`). Next ddp-sync job: 2026-10-22 00:30 UTC; none started in the previous 10 minutes.
* `/opt/ddp-open-states/api-v3`: branch `main`, `HEAD` `ba0b646`, `git status --short` clean, range to `origin/main` exactly the three commits (`a2f5db8`, `d4a1a6c`, `92d107c`). Container `ddp-openstates-api-1`: healthy, restarts 0, image `cc7deeaaa1a9`.
* **One deviation to say plainly:** at 05:35:17 the log showed **one** non-health request in the previous 5 minutes (`GET /jurisdictions/FL?include=legislative_sessions` from 172.26.0.1, the Docker bridge; a metadata read, 200). Your quiet check says only `/healthz`, so I **waited for a clean 5-minute window** (met by 05:36:31) before starting.

## The change (times UTC, 2026-10-21)
| step | time |
|---|---|
| tag `ddp-openstates-api:pre-open377` (= `cc7deeaaa1a9`, the rollback) | 05:36:36 |
| `git pull --ff-only origin main` to **`a2f5db8`** (4 files, +147/-1: `api/bills.py` +23, `api/db/models/votes.py`, two test files) | 05:36:36 |
| `build api` (exit 0, new image **`84f8074fdae3`**) | 05:36:41 to 05:36:43 |
| `up -d --no-deps api` from `/opt/ddp-open-states/deploy` | 05:36:47 |
| healthy | by 05:37:05 (about 18 s) |
`HEAD` before `ba0b646`, after **`a2f5db8`**; image before `cc7deeaaa1a9`, after `84f8074fdae3`.

## Verification (from inside the ddp-sync container, its api-v3 key; `10.0.0.11:8002`): all PASS
* `/healthz` 200; container healthy, **restarts 0**, policy `unless-stopped`; ddp-sync healthy (up 2 days, not touched); **0 `apikey=` lines**, **0 5xx / Traceback / ERROR lines** in api-v3's log since the recreate; the broker's `/api/status/` 200.
* **Equality check** (`GET /bills?jurisdiction=<J>&per_page=1&vote_updated_since=<cutoff>%2B00:00`, `total_items`, expected = your G4 numbers): `2026-06-01` Utah **739** (expected 739), Virginia **2,201** (2,201); `2026-08-01` Utah **0** (0), Virginia **6** (6); `2026-06-20` Utah **5** (5), Virginia **2,201** (2,201). RDS had not changed since Part 1, so I did not re-run the SQL.
* `vote_updated_since=2099-01-01T00:00:00%2B00:00` returns **0**; the `...T00:00:00Z` form returns **400** and `not-a-date` returns **400** (`datetime must be in ISO-8601 format, try YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS`); **no offset gives the same answer as `+00:00`** (739 and 739).
* **Nothing else moved:** Utah unfiltered **1,021** (unchanged); `document_updated_since=2099` **0** (unchanged); `GET /bills/ocd-bill/1ab505cf-f29c-496a-824b-5d6c76e41258?include=versions` returns **14 versions in exactly the order recorded in my 10-14 OPEN-361 reply**: Introduced, Senate Amendment 1 to 4, House Amendment 5 and 6, Amended 1/27, Amended Excerpts 1/27, Amended 2/9, Amended Excerpts 2/9, Amended 3/3, Amended Excerpts 3/3, Enrolled.

## Unexpected
Nothing. I did not measure whether a broker search saw a `partial` result during the 17 s; I saw no error.

## Rollback (only on Ramon's say-so)
`docker tag ddp-openstates-api:pre-open377 ddp-openstates-api:local`, `up -d --no-deps api`, `git checkout ba0b646` in the checkout.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
