# Update: facts about Michigan's S3 cookie object, read from the Mac with the scraper IAM user (2026-10-06)

From the Mac Studio session, on Ramon's instruction. Adds to `question-who-publishes-mi-waf-cookie-...-20261006.md`
(this branch). Correction to that note: the Mac **does** have AWS credentials (IAM user `ddp-scraper`, in the dev `.env`), the same
ones that build and push the scraper image. They are narrow: they could read this object but not list its versions.
Read-only; nothing was written or changed. No cookie value was printed or saved anywhere.

## What was read (`s3://ddp-openstates-scraper-memory/prod/mi/_cache/mi_waf_cookies.json`)

- **`head_object`:** `LastModified` **2026-09-03 02:08:22 UTC**, 339 bytes, `VersionId` `z42h6F7n3L3FYoFkiwAVLxskif0BC7n7`.
  So the file the Fargate collector has been accepting is **one object, a month old**.
- **Shape:** two cookies, `x-bni-fpc` and `x-bni-rncf`, each with only an `expires` field (no other metadata). Both expire
  **2027-09-10 15:27 UTC** (about 339 days from now). `_meta` holds only a `user_agent` string; there is **no minted-at time**.
- **Consequence:** `_mi_waf_cookies_are_fresh` checks only `expires` at least 600 s ahead, so this file passes the gate for about
  another year regardless of whether the site still honours the cookie. That matches the second reading in the question (one old
  file passing), not a second live publisher. I cannot tell from here whether the site still accepts it; the 10-04 502 may or may not relate.
- It was written 09-03, after the Mac's `mi_cookie_publish` was enabled (08-31) but when that job was already refusing every tick, so
  I suspect a manual upload. That is a guess; please confirm or refute.

## Denied to this IAM user (still needed from you)

`s3:GetBucketVersioning` and `s3:ListBucketVersions` are both AccessDenied, so I could not see whether versioning is on or any older
version. Of the original questions, these remain open and need you:

1. Versioning on/off and `list_object_versions` for that key (was 09-03 the only upload, or one of a cadence? who wrote it?).
3. The CloudWatch logs of the 10-04 and 09-27 MI tasks (any cookie hydrate/check line; which `VersionId`).
4. The live `MI_COOKIE_PUBLISH_ENABLED` on the EC2 compose, and whether the EC2 `ddp-sync` ever logged a `mi_cookie_publish:` line.
5. Anything else that could write that key (cron, operator upload, CAMS or ScrapeBot).

Item 2 (file shape) is answered above; you can skip it.

Still not done on my side: no change to the Mac's `.env`, no `SCRAPER_MEMORY_PREFIX`, no new IAM permission.

Reply on this branch either way.
