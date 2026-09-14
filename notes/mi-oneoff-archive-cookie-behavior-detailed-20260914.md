# MI one-off archive run: full detail on cookie re-warm behavior after the WAF block

Ramon asked whether the archiver kept trying to mint fresh cookies after the first WAF block,
and for full detail. Analyzed the complete CloudWatch log for the run (`RUN_ID=mi-archive-
25fe259dda29`, task `923b9348fc2142d2a0ba7efbd055f946`, 993 log lines, full run 20:36:34-
21:05:36 UTC, 1819s total per its own summary line).

## The mechanism, confirmed in code (not the ScrapeBot/CAMS path)

`openstates-core/openstates/utils/cookie_provider.py`'s `CookieProvider` class. `get_cookies()`/
`get_user_agent()` each independently call `_get_session()`, which reads an on-disk cache file
and, if missing/expired/invalid, calls `_warm_up_and_cache()` -> `_playwright_warm_up()`: a real
headless Chromium browser (Playwright), launched **inside this same Fargate task**, navigating
directly to `https://legislature.mi.gov` to obtain fresh cookies + the real UA that earned them.
Entirely self-contained -- no call to the Mac's ScrapeBot/CAMS `mint_cookies` mechanism at all
(that's a separate, pre-run pre-seed step this run didn't use since it launched via a bare
`ecs run-task`, not through the scheduler's own `scrapebot_fallback` pre-seed wiring).

`fetch_with_retry()` is the actual retry-once contract: on a `WafBlockDetected`, it logs
`"{name}: block detected despite cached cookies; invalidating cache and re-warming once"`,
calls `self.invalidate()` (deletes the cache file), re-reads (forcing a fresh warm-up), and
retries the SAME request exactly once. A second failure propagates as a real, uncaught
exception (counted as `fetch_errors`), per OPEN-19's explicit "don't warm up on every transient
block" design intent.

## What actually happened, precisely

- **First block detected at 20:42:45** (log line index 92 of 993) -- everything before that
  point used a cookie that was already valid (no warm-up needed yet).
- **From 20:42:45 through the run's end (21:05:36, ~23 minutes), it never stopped trying**:
  **320 separate fresh-cookie warm-up attempts**, continuous to the last log line before exit.
- **Not a hard block** -- of the 158 real page/document fetch attempts made after that first
  block, **112 (71%) succeeded, 46 (29%) failed with a real 403**. Michigan's WAF appears to be
  accepting some requests and rejecting others in this window, not blocking everything.
- **Real inefficiency found, worth its own look**: 320 warm-ups for only 158 real fetches --
  roughly 2 warm-ups per fetch, not 1. This tracks directly to `fetch_with_retry()` calling
  `self.get_cookies()` and `self.get_user_agent()` as two separate calls, each independently
  reading (and, if invalid, re-warming) the same cache -- if the cache write from the first
  call hasn't landed (or gets invalidated) before the second call checks, both trigger their
  own full browser launch instead of sharing one warm-up's result. Each attempt takes a real
  1-13s (avg ~4.3s per the timestamp deltas between consecutive warm-up log lines) -- genuine,
  measurable overhead independent of whether the block itself was active.

## Real outcome of this run (for reference, already reported separately)

`mi: 3973 bills checked | fetched=165 skipped=13593 archived=165 fetch_errors=64 blocked=0
extract_errors=2 ... s3_verified=165 s3_unverified=0 persist_errors=0` -- every fetched
document made it to verified S3 storage; the 64 `fetch_errors` (46 real 403s + the balance
genuine 404s, unrelated to the block) are documents this run never got usable content for.
Confirmed against RDS directly: `is_error` count for MI went from 165 -> 167 (+2, matching
`extract_errors=2` exactly), total documents 13,597 -> 13,762 (+165, matching `archived`
exactly).

Not proposing a fix myself -- flagging the real double-warm-up inefficiency as something worth
a look (e.g. caching the (cookies, user_agent) pair together per-call rather than re-reading
twice), separate from whatever's actually driving Michigan's own WAF sensitivity itself.
