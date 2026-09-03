# Correction to my last note — the cookie publish actually went to the wrong bucket

*Replies to `notes/open193-mi-fresh-cookies-published-20260902.md`.*

My last note reported success based on the mint job's own return value alone
(`{'success': True, 'key': 'prod/mi/_cache/mi_waf_cookies.json'}`) without checking the object
actually landed where `cloud_collector.py` reads from. It didn't -- Ramon caught this. Found a
real bug: `mi_cookie_publish.py`'s S3 write path (`SCRAPER_MEMORY_S3_CMD`'s default wrapper,
`ddp-prod-s3-openstates-backups`) still targets the **old**, deprecated `ddp-openstates-backups`
bucket, not `ddp-openstates-scraper-memory` (created 2026-08-29, specifically to get scraper
memory/cache data OFF that bucket's 30-day auto-delete rule). Confirmed directly: the "published"
object's own metadata showed `ddp-openstates-backups`' expiration rule attached, and
`ddp-openstates-scraper-memory`'s copy was still last-modified 2026-08-30 -- meaning **every
scheduled `mi_cookie_publish` tick since the migration has silently written to the wrong place**,
~4 days of "successful" publishes that never actually reached the bucket the cloud path reads.

Filed **SYNC-53** to track the real fix. Immediate unblock for tonight (not the fix): re-minted
fresh cookies directly via `scrapebot_client.dispatch_mint_cookies()`, then
`aws s3api put-object`'d the result straight into `ddp-openstates-scraper-memory` at the correct
key using the `ddp-scraper` credential. Verified the cookie content itself is genuinely valid --
real Barracuda `x-bni-fpc`/`x-bni-rncf` values, ~1 year real expiry, easily passes
`cloud_collector.py`'s freshness check.

MI's canary leg should have a genuinely fresh, correctly-placed cookie to read now. Sorry for
the false confirmation in my last note -- lesson taken to verify the actual landing spot next
time, not just the job's own reported success.
