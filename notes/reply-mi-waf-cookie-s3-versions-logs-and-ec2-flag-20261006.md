# Reply: Michigan WAF cookie: three identical uploads, versioning is on, the EC2 publisher is off (prod agent, 2026-10-06)

Replies to `question-who-publishes-michigans-waf-cookie-...-20261006.md` and `mi-cookie-s3-object-facts-read-from-the-mac-20261006.md`. **Read-only throughout: I wrote nothing to S3, Redis, compose files or AWS.** No cookie value was printed or saved; the downloaded versions were compared in memory and the temp files were deleted. Times UTC.

## 1. S3 versions of `prod/mi/_cache/mi_waf_cookies.json` (bucket `ddp-openstates-scraper-memory`)
- **Versioning is Enabled** (MFA delete off). This host's role can read it (`get-bucket-versioning`, `list-object-versions`).
- **Three versions exist, all 339 bytes:**
  - 2026-08-30 18:32:38 (`VJ3VDFgM...`), oldest;
  - 2026-09-03 01:09:41 (`DcuBXsJt...`);
  - 2026-09-03 02:08:22 (`z42h6F7n...`), the current one, as you read it.
- **All three have identical content** (same cookie names, same `expires`, same `_meta`; compared whole, in memory). So nothing has ever re-minted the cookie: the same cookie was uploaded three times. There is no 6-hour cadence at all; the three uploads are 08-30 18:32, then 09-03 01:09 and 02:08 (an hour apart, around the SYNC-53 merge and the first Mac and EC2 enablement).
- The prefix `prod/mi/_cache/` holds only two keys: this cookie file and `mi_last_actions_2025-2026.json` (last written 09-27 02:28:01, 219,873 bytes, by the MI collector).
- **Who wrote them: I cannot tell.** S3 versions do not record the writer, and this host's role is denied `cloudtrail:LookupEvents`. Two uploads an hour apart look like manual or one-off runs, but that is a guess.

## 2. File shape
Two cookies, `x-bni-fpc` and `x-bni-rncf`, both `expires` 2027-09-10 15:27 UTC; `_meta` has only `user_agent`; no minted-at. Same in all three versions.

## 3. MI task logs (CloudWatch group `/aws/ecs/ddp-scrapers`, **region us-east-1**; this host's default region is us-east-2, so a bare `aws logs` call there finds nothing)
- **10-04 02:00 task** (stream `scraper/scraper/9320162174a5...`, 02:00:43 to 02:04:07): failed after 205 s: `scrapelib.HTTPError: 502 while retrieving` the bill search page (`docTypesList=HB,SB ... sessions=2025-2026`), raised inside `mi_waf_get` / `fetch_with_retry`. Final line `{"source":"mi","run_id":"mi-14c5348d2c9d","mode":"incremental","status":"failed","duration_s":205}`.
- **09-27 02:00 task** (stream `scraper/scraper/a404d992...`, 02:00:42 to 02:28:01): **succeeded**: `{"source":"mi","run_id":"mi-5ce103cbb832","mode":"incremental","status":"ok","found":242,"duration_s":1633}`, and `MI OPEN-134: last-action baseline now covers 4185 bills (180 updated this run)` at 02:27:52. So the site honoured this same cookie file as late as 09-27.
- **Neither task logs any cookie hydrate or freshness line** (the only cookie-adjacent line is `Created fresh session (user agent rotation disabled for this scraper)`), and neither logs a `VersionId`. I cannot say from the logs which version a task used; since 09-03 02:08 there has only been the one current version.
- So the 10-04 502 is **not** a refused run at the freshness gate (the task got past it, as you said) and the logs do not tell whether the site stopped honouring the cookie or was simply down. The next MI run (Sunday 10-11 02:00) is the next real observation.

## 4. The EC2 side
- `MI_COOKIE_PUBLISH_ENABLED=false` in `/opt/ddp-sync/infrastructure/docker-compose.prod.yml` and in the live container. It has been `false` since the 2026-09-02 OPEN-193 setup (my 09-08 note, `mi-cookie-publish-root-cause-deliberately-disabled-20260908.md`, found the same and asked whether to flip it; I did not).
- The live container's log since its 10-06 02:17 recreate contains exactly one `mi_cookie_publish` line: `mi_cookie_publish: disabled - skipping`. Older log history was lost when the container was recreated; my 09-08 note recorded the same "disabled" lines from the 09-03 19:45 rebuild onward. So EC2 is not a second publisher now. Whether it could have written the 09-03 uploads before that rebuild I cannot prove; the flag was already false.
- **I also correct my own 09-08 note:** it said the object was published "exactly once" right after SYNC-53. The version list shows three identical uploads (08-30 and two on 09-03), not one.

## 5. Anything else that could write that key
Nothing I know of from this host. The collector writes under the same prefix (`mi_last_actions`) so Fargate has write access there; I did not check bucket or IAM policies, and CloudTrail is denied here.

## What this means (my reading, not verified)
The freshness gate cannot protect anything: the only check is `expires` (2027-09-10), and the file has never changed. The cookie worked on 09-27; whether it works now is unknown. I would not set `SCRAPER_MEMORY_PREFIX=prod` on the Mac or flip the EC2 flag before you decide what the publisher should mint: either would replace this object with a new cookie on a live-site path, which is the risk I flagged on 09-08. Nothing here needs a change today; decisions are yours and Ramon's.
