# Reply to 3ac8959f3 (Part B): NM's first scrape succeeded on revision 69; AZ's rerun is running

Written 15:45 UTC 11-18 (date -u at write time). From the production EC2 host. User's words in session: "Yes, NM then AZ" (pop-up), and later "I am Ramon" (the user is Ramon).

## NM (nm-ed99d23b40cb), ECS revision ddp-scrapers:69
- Launched 14:58:15 UTC, one call, no retry, no skip flag; ddp-sync read 112 NM people. Active sessions for both the bills and votes scrapers: **{'2026'}**.
- Scrape done 15:08:49 (631.9 s, past the vote-PDF step that crashed on 68, so the pandas fix works); archive 15:33:54 (1,505 s); **`openstates_pipeline: done archived=True duration_seconds=2202.0 failed=0 status=completed` at 15:34:57.**
- **812 bills and 259 vote events** in RDS. Archive: 812 bills checked, **1,113 documents fetched and archived, s3_verified 1,113, fetch_errors 0, blocked 0, extract_errors 0, persist_errors 0.**
- Hand-back for the Mac-side checks: run id **nm-ed99d23b40cb**. NM is in the Sunday weekly batch (11-22 02:00 UTC).

## AZ (az-c9bd427244f2), ECS revision ddp-scrapers:69
Launched 15:35:08 UTC after NM finished clean, one call. The scraper's active-sessions line names **{'57th-2nd-regular'} only** (as you expected; the 2027 session no longer stops it). It is still running; I will report status, failed, bills, vote events and archive counts when it ends.
