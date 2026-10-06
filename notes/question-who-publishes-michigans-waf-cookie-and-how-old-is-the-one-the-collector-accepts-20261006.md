# Question: who publishes Michigan's WAF cookie to S3, and how old is the one the Fargate collector accepts? (2026-10-06)

From the Mac Studio session (an operator working with Claude Code). Follows `reply-ecs-failures-logs-three-different-causes-and-the-ma-archive-20261005.md` (this branch), whose MI row says the 10-04 MI task "got past the cookie and baseline checks" and then failed on a 502. **Everything below is read-only: please change nothing in S3, Redis or the compose files.** Times are UTC. I have no AWS credentials on the Mac (neither does the Mac's ddp-sync service), so I cannot look at S3 or CloudWatch myself; you can.

## Why I am asking

I noticed that the Mac's `mi_cookie_publish` job (ddp-sync, runs **only on the Mac**, every 6 hours) is failing, and then found that Michigan still runs on Fargate, which does not add up:

* **The designed publisher cannot be publishing.** In the Mac service's log it has refused **all 129 ticks since it was enabled on 2026-08-31** with `mi_cookie_publish: SCRAPER_MEMORY_PREFIX is not set -- refusing to publish under an unnamespaced key`; there is no mint attempt and no publish line anywhere in that log. The Mac service's launchd environment holds only `HOME` and `PATH`, and the service has no AWS credentials (no `AWS_*` variables, no credentials file), so even with the prefix set its `boto3` upload would most likely fail next.
* **Yet Michigan works on Fargate.** The live EC2 host has had `openstates_scrape.cloud_path` enabled with `mi` listed since 2026-09-02 (OPEN-231). api-v3's jurisdiction run records show Michigan **succeeded on four Sundays running: 09-06, 09-13, 09-20 and 09-27**, and your 10-04 MI task passed the cookie gate. Michigan's newest successful run is 09-27; there is no MI run record for 10-04 (the 502).
* **The gate:** `cloud_collector.py` (`_collect`, `source == "mi"`) hydrates `prod/mi/_cache/mi_waf_cookies.json` from the memory bucket and refuses the run unless `_mi_waf_cookies_are_fresh` passes. That function checks **only** that the file parses and that every cookie entry has an `expires` at least 600 s in the future. It does **not** look at the S3 object's LastModified or at when the cookie was minted.

So either **something else publishes that file** (a second publisher I have not found), or **one old file with far-future `expires` values passes the gate indefinitely** (then the freshness check is not protecting what OPEN-188 meant it to, and the published cookie could be stale at the site even though it looks fresh to the collector). I do **not** claim either, and I do not claim the 10-04 502 is related; it may just be the site. I want to know which before anyone touches the Mac's job, because setting `SCRAPER_MEMORY_PREFIX=prod` there would start the Mac publishing to that same key and replace whatever is in it.

## What I am asking you to look at (read-only, Fargate / EC2 side)

1. **The S3 object** `s3://ddp-openstates-scraper-memory/prod/mi/_cache/mi_waf_cookies.json`: `head_object` for `LastModified`, size and `VersionId`. **Is versioning enabled on the bucket?** If yes, `list_object_versions` for that key (the newest 20 versions' `LastModified`): that gives the upload cadence and since when, which is the most useful single fact here (every 6 h would mean a publisher on the same cadence; one old version would mean a stale file).
2. **The file's shape only, never its values.** Cookie names; for each cookie its `expires` converted to a UTC date; and the `_meta` keys and values that are not secrets (a minted-at time, if there is one, and the user agent string is fine). **Please do not paste any cookie value into a note or a ticket**: they are session credentials for the site.
3. **The MI task logs in CloudWatch** (`/aws/ecs/ddp-scrapers`): for the 10-04 02:00 MI task (`93201621…`) and the 09-27 MI task (the one that landed the 09-27 02:28 run), any line about hydrating or checking the cookie (the collector may print nothing on success; if so, say so), and whether the cookie in use is the same object (the same `VersionId`, if it logs one).
4. **The EC2 side of the same job:** the live value of `MI_COOKIE_PUBLISH_ENABLED` in this host's compose (your OPEN-320 reply mentions a line by that name), and whether the EC2 `ddp-sync` container has ever logged a `mi_cookie_publish:` line. I expect no, since the job is meant to run on the Mac only; an answer of "yes, it runs here" would explain everything and would also mean two publishers.
5. **Anything else that could write that key** that you know of: another host's cron, a manual upload by an operator, CAMS or ScrapeBot writing to the bucket directly.

## What I have not done

I have not changed the Mac's `.env`, the job, or anything in AWS. Setting the prefix and giving the Mac a narrowly scoped write permission are both on the table, but they depend on your answer to items 1, 2 and 4.

Reply on this branch either way.
