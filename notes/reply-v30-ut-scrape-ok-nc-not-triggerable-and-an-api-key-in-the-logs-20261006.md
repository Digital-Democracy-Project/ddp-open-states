# Reply: v30 confirmed for UT (status ok, no certificate errors); NC cannot be triggered alone here; and an API key is written to the ddp-sync log (please add redaction) (2026-10-06)

From the prod agent on the EC2-broker host. Answers `new-scraper-image-v30-rev35-fixes-for-ut-nc-ma-archive-please-confirm-20261005.md` (this branch). Times are UTC. Triggered with the operator's go-ahead, through the normal route, with nothing else changed. I could not read the live task definition myself (this host's role is denied `ecs:DescribeTaskDefinition`), so "v30 / revision 35" is taken from your note, not verified from here.

## 1. UT scrape: ok

`POST /ddp-sync/v1/trigger/openstates-scrape/ut` at **00:43:27**, run id `ut-be99ba7e819c`, Fargate task log stream `scraper/scraper/…6c9d6021`. Completion record, exactly:

```
{"source": "ut", "run_id": "ut-be99ba7e819c", "mode": "incremental", "status": "ok", "found": 4, "duration_s": 2049}
```

- ddp-sync logged `cloud_scrape: done duration_seconds=2127.3` at 01:18:56; the container's log runs 00:44:06 to 01:13:03, and the scraper's own summary says `bills scrape duration 0:34:05`, `bills: {'start': '2026-09-27T01:34:50'}`.
- **First `ERROR:` line: none.** Across the whole stream (6,162 lines): 0 `ERROR` lines, 0 tracebacks, **0 `CERTIFICATE_VERIFY_FAILED` / `SSLError` lines**. The `InsecureRequestWarning` for `le.utah.gov` appears on the bill fetches (verification is off, as OPEN-322 intends), and the scraper fetched bill pages and their `/data/2026GS/…json` files to the end.
- One warning near the end, which I did not investigate: `01:18:13 WARNING openstates: UTBillScraper raised EmptyScrape, continuing without any results` (the run still ended `ok`).
- **Why a quiet UT still took 35 minutes** (the operator asked): the log says `no session provided, using active sessions: {'2025S2', '2026'}`; the scraper fetched **522+ House bills then the Senate bills and resolutions, about 1,020 bills of 2026 plus the 2025S2 special session, at about 2 seconds each (the HTML page plus the JSON file)**, whether or not anything changed; `mode: incremental` and the `start` watermark do not shorten the walk. The 2027 General Session has no bills yet, so it is not active.

## 2. What fired after it (all normal)

At 01:20:28 the UT archive task finished (`openstates_archive: fargate task done duration_seconds=91.7`); `archiver_triggered_legbot_no_sessions_touched` (nothing for LegBot); `bill_search_refresh_run calls=1 drained=True refreshed=0`; then the SYNC-95 embedding hook's first real ledger pass for UT, 01:20:45 to 01:27:17: `mode=ledger bills=1021 documents=0 chunks=0 complete=True failed_bills=0`, ledger `listed 1021, missing_documents 0, changed_documents 5146 (the restamping), orphaned_documents 0, failed 0`. No vectors were written (the index total was unchanged).

## 3. NC: cannot be triggered alone on this host

`POST /ddp-sync/v1/trigger/openstates-scrape/{target}` accepts `patches`, `fl`, `wa`, `usa`, `secondary`, `people`, and the single-jurisdiction codes **`va`, `mi`, `ma`, `ut`, `az`** only (`_OPENSTATES_SINGLE_JURISDICTION` in `triggers.py`); `nc` is not one, and `nc` runs only inside the weekly `secondary` batch (`openstates_scrape.secondary`: Sundays 02:00 UTC, jurisdictions `va, mi, ma, ut, az, nc`). I did **not** trigger `secondary`: it would also launch MI (your instruction) and MA (an 8.8-hour scrape). Options: (a) a small ddp-sync PR adding `nc` to the single-jurisdiction set, after which I trigger one NC run; or (b) wait for **Sunday 10-11 02:00 UTC**, which also covers MI, MA and the rest on v30 and gives you NC's first incremental run. Which do you want? MI and the MA archive: untouched, as asked.

## 4. Please add redaction to the ddp-sync logging (a secret is in the log)

Every api-v3 request from ddp-sync is logged by `httpx` at INFO with the **full URL, including the API key in the query string** (`...&apikey=<the key>&...`). Today I printed an archive-hook request line (`GET http://10.0.0.11:8002/bills?jurisdiction=UT&document_updated_since=…&apikey=ddp-ro-…&per_page=20&page=1`) and the whole `ddp-ro-` read key showed up in my terminal output and so in this session; I am not putting the value anywhere in these notes. This is the same leak I reported on 2026-09-16 (the `RDS_OPENSTATES_API_KEY` and the local one go into the plaintext Docker log on every api-v3 call, not fixed since). **Request: please add redaction**, in ddp-sync's logging setup: raise the `httpx`/`httpcore` loggers to WARNING, or add a logging filter that masks `apikey=`, `api_key=` and `token=` values in any logged URL, and add a test that pins it. Until it ships, treat the `ddp-ro-` key and the RDS api-v3 key as exposed; the operator may want to rotate them after the fix, since the Docker json-file logs on this host (10 MB x 5 files, rotated) hold older lines too.

Reply on this branch either way.
