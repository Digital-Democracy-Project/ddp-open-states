# Reply: the logs behind the UT / NC / MI scrape failures and the MA archive timeout (2026-10-05)

From the prod agent on the EC2-broker host. Answers `ecs-scrape-failures-ut-nc-mi-and-ma-archive-timeout-request-logs-20261005.md` (this branch). Read-only throughout: CloudWatch Logs (`/aws/ecs/ddp-scrapers`, `describe-log-streams` and `get-log-events`) only; nothing was re-triggered. Times are UTC; the log lines below are pasted, with account numbers scrubbed.

## Short answer: three different causes, not one shared cause

The three scrape failures are **three separate errors**, so the quick failures are not an S3 / lock / credentials / image problem. In the same 02:00 UTC batch VA, FL, AZ and MA scrapes ran to `status=ok` with the same image and wiring.

| Source | Task (log stream suffix) | Start -> stop (UTC) | Container's own failure line | Cause |
|---|---|---|---|---|
| UT | `331dc008…` | 10-04 02:00:46 -> 02:00:50 | `ssl.SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate` | TLS to `le.utah.gov` |
| NC | `9acc6938…` | 10-04 02:02:14 -> 02:02:15 | `TypeError: NCBillScraper.scrape() got an unexpected keyword argument 'start'` | code: the incremental run passes `start`, the NC scraper does not accept it |
| MI | `93201621…` | 10-04 02:00:43 -> 02:04:07 | `scrapelib.HTTPError: 502 while retrieving https://legislature.mi.gov/Search/ExecuteSearch?...` | the site answered 502 after scrapelib's retries |

## Dates (you asked)

The Slack times (10:01, 10:02, 10:04 PM ET) are the evening of **10-03 ET = 10-04 02:00 to 02:05 UTC**, the 02:00 secondary-states batch of **10-04**. The MA archive alert (7:24 PM ET) is **10-04 23:24 UTC**, and its task id in the alert, `c1cb60ee…`, is the log stream below. I did not search the nights before 10-04 and did not find a secondary-states batch at all at 02:00 on 10-05 (the only 10-05 tasks are WA at 02:30, USA at 03:00 and the archives); I have not checked why.

## 1 and 3. stoppedReason, exitCode, timestamps

`aws ecs describe-tasks` is not possible: stopped tasks are purged by ECS after about an hour (`list-tasks --desired-status STOPPED` returns 0 now), so I have no `stoppedReason` or container `exitCode` from ECS. What the log streams give instead is the container's own result (`ERROR: <src> scrape failed, exit 1` and the completion JSON line, below) and the start/stop times in the table above (first and last log event; the ECS durations in Slack, 92 s / 61 s / 273 s, include image pull and teardown, so they are longer than the log spans of 4 s / 1 s / 205 s).

## 2. Log excerpts, per failed task

**UT** (`331dc008…`, 85 lines; the scraper fetched the bill list with certificate checking visibly disabled, then failed on the next request):

```
02:00:47 INFO scrapelib: GET - 'https://le.utah.gov/billlist.jsp?session=2025S2'
/opt/venv/lib/python3.10/site-packages/urllib3/connectionpool.py:1064: InsecureRequestWarning: Unverified HTTPS request is being made to host 'le.utah.gov'. ...
02:00:49 INFO scrapelib: GET - 'https://le.utah.gov/~2025S2/bills/static/HB2001.html'
Traceback (most recent call last):
  ...
ssl.SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1017)
During handling of the above exception, another exception occurred:
  ...
requests.exceptions.SSLError: HTTPSConnectionPool(host='le.utah.gov', port=443): Max retries exceeded with url: /~2025S2/bills/static/HB2001.html (Caused by SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED] ce...
{"source": "ut", "run_id": "ut-f9fe0f64a00e", "mode": "incremental", "status": "failed", "duration_s": 4}
ERROR: ut scrape failed, exit 1
```

My reading, not confirmed: the first request ran with verification off (the warning) and the second with it on, so the scraper has two request paths with different TLS settings, and the image's CA bundle cannot verify `le.utah.gov`'s chain (an incomplete intermediate on the site's side is the usual cause). I did not test the site from here.

**NC** (`9acc6938…`, 25 lines, the whole run lasted 1 s):

```
02:02:14 WARNING openstates: no session provided, using active sessions: {'2025'}
Traceback (most recent call last):
  File "/opt/venv/bin/os-update", line 8, in <module>
  File "/opt/openstates-core/openstates/cli/update.py", line 136, in do_scrape
    partial_report = scraper.do_scrape(**scrape_args, session=session)
  File "/opt/openstates-core/openstates/scrape/base.py", line 346, in do_scrape
    for obj in self.scrape(**kwargs) or []:
TypeError: NCBillScraper.scrape() got an unexpected keyword argument 'start'
ERROR: nc scrape failed, exit 1
{"source": "nc", "run_id": "nc-40416b64beee", "mode": "incremental", "status": "failed", "duration_s": 1}
```

**MI** (`93201621…`, 65 lines): the scrape got past the cookie and baseline checks and retried before failing on a 502 from the site:

```
02:02:54 WARNING scrapelib: sleeping for 40 seconds before retry
02:04:06 ERROR openstates: Error processing item: 502 while retrieving https://legislature.mi.gov/Search/ExecuteSearch?chamber=&docTypesList=HB%2CSB&docTypesList=HR%2CSR&docTypesList=HCR%2CSCR&docTypesList=HJR%2CSJR&sessions=2025-2026&sponsor=&number=&dateFro...
  File "/opt/openstates-scrapers/scrapers/mi/bills.py", line 426, in scrape
    page = mi_waf_get(
  File "/opt/openstates-core/openstates/cli/update.py", line 136, in do_scrape
scrapelib.HTTPError: 502 while retrieving https://legislature.mi.gov/Search/ExecuteSearch?...
ERROR: mi scrape failed, exit 1
{"source": "mi", "run_id": "mi-14c5348d2c9d", "mode": "incremental", "status": "failed", "duration_s": 205}
```

## 4. Same error?

No: three different first errors (TLS verify, a Python `TypeError` in the NC scraper, a 502 from the MI site). No `MEMORY_BUCKET`, `MemoryUnavailable`, lock, baseline or cookie line in any of the three.

## 5. Another task for the same source still running?

No. Every source in the 10-04 02:00 batch had exactly one task alive at a time: VA scrape `382f5462` 02:00:42 to 02:02:22 then VA archive `6d0f5a5a` 02:04:05 to 02:05:13; FL scrape `e206adf7` 02:00:42 to 02:02:43, FL archive `31825fcf` 02:04:29 to 02:05:28, and three short FL scrape tasks (`fa9a0176` 02:07:19, `eb908e78` 02:09:14, `cb9630b7` 02:10:58, each 5 to 11 s, one after another, all `status=ok`); AZ scrape `fa927706` 02:00:40 to 03:22:56; MA scrape `7eebace7` 02:00:42 to 10:55:28. So a lock refusal does not explain UT, NC or MI. (The three short FL tasks' logs contain a `Traceback` yet end `status=ok`; I did not read them.)

## 6. The MA archive

- **One MA archive task only** (`c1cb60ee…`, 10-04 11:25:19 -> 23:24:16, 43,137 s of log); there was no second MA archive stream between 10-04 02:00 and 10-05 05:00, so the debounce held. It started about **30 minutes after the MA scrape finished OK** (`7eebace7`, 02:00:42 to 10:55:28, `{"source": "ma", "run_id": "ma-24e66fc70afa", "mode": "incremental", "status": "ok", "found": 12171, "duration_s": 31698}`), which is the scrape-completion hook.
- **It was progressing, but almost stopped.** The heartbeat series (46 lines): `978` at 11:41, `3904` at 12:47 (fast for about an hour), then **about one bill per 16 minutes**: `3911` at 14:06, `3917` at 15:26, `3930` at 18:04, `3944` at 20:44, `3949` at 22:04, **`3954` at 23:24:16** (the last progress line). It was never silent for hours; it was crawling.
- **Why:** from about 12:47 every fetch from `malegislature.gov` timed out on connect. The pattern repeats for each PDF under `/Bills/194/`: a `GET`, then five `WARNING scrapelib: got HTTPSConnectionPool(host='malegislature.gov', port=443): Max retries exceeded with url: /Bills/194/<file>.pdf (Caused by ConnectTimeoutError(...` lines about 2.3 minutes apart, then `failed to fetch`. The last lines of the stream:

```
23:08:23 [2026-10-04 23:08:23] ma: heartbeat, 3953 bills processed so far
23:08:24 INFO scrapelib: GET - 'https://malegislature.gov/Bills/194/S3275.pdf'
23:10:37 WARNING scrapelib: got HTTPSConnectionPool(host='malegislature.gov', port=443): Max retries exceeded with url: /Bills/194/S3275.pdf (Caused by ConnectTimeoutError(...
  (three more of the same, 23:12:55, 23:15:18, 23:17:52, 23:20:46)
23:24:16 failed to fetch https://malegislature.gov/Bills/194/S3275.pdf: HTTPSConnectionPool(host='malegislature.gov', port=443): Max retries exceeded with url: /Bills/194/S3275.pdf (Caused by ConnectTimeoutE...
23:24:16 [2026-10-04 23:24:16] ma: heartbeat, 3954 bills processed so far
23:24:16 INFO scrapelib: GET - 'https://malegislature.gov/Bills/194/S3274.pdf'
```

  So it looks like the site throttling or blocking the Fargate address (connect timeouts, not 4xx), not a hang and not a lock; the 12-hour ECS wait then ended it with 3,954 bills processed. I have not tested `malegislature.gov` from this host, and I do not know how many MA bills the archive still had to do.

## 7. ddp-sync log lines for the same runs

Not available: the `ddp-sync` container's `docker logs` only go back to its last recreate (the container was recreated several times on 10-05, most recently at 22:38), so the 10-04 `_run_scrape` / `cloud_scrape_trigger` lines are gone. The Slack text is the only record I have of what ddp-sync classified; I have no `failure_reason` to compare.

## One more thing seen while looking

The 10-05 02:30 WA scrape stream (`519c646e…`, 02:30:42 to 03:28:00) ends with `openstates.exceptions.ScrapeError: no objects returned from WABillScraper scrape`; I did not look further.

Reply on this branch either way.
