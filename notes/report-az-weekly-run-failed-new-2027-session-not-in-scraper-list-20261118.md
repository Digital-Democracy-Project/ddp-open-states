# Report: Arizona's first weekly run on the new day FAILED: the scraper reports a 2027 session that is not in its session list. Not retried.

Written 12:05 UTC 11-18 (date -u at write time). From the production EC2 host. No retry; nothing else was done.

## What happened
- Run **az-cc40c0a754ce**, started by ddp-sync's schedule at 12:00:00 UTC (AZ and NC's new Wednesday slot after the ddp-sync cb5eade release), on the revision NC's task shows: **ddp-scrapers:68** (v65). Mode incremental (start 2026-11-15T02:22:36).
- It failed after about 3 seconds of scraping (ddp-sync: `cloud_scrape: collection failed ... exit_code=1`, **`openstates_pipeline: done archived=None duration_seconds=91.8 failed=1 status=failed`** at 12:01:31).
- The task log: `openstates.exceptions.CommandError: Session(s) 2027 - Fifty-eighth Legislature - First Regular Session were reported by Arizona.get_session_list() but were not found in Arizona.legislative_sessions or Arizona.i...` raised from `openstates/cli/update.py` check_session_list (line 349, called from do_update line 424), before any bill was scraped; the scraper then logged "az scrape failed, exit 1".
- **Cause (from that message, not from the code):** azleg now lists the 58th Legislature's 2027 first regular session and the scraper's own session list (scrapers/az/__init__.py legislative_sessions) does not carry it. This is the same class of failure as an unlisted upstream session; it needs a scrapers change (add the 2027 session, or ignore it) in a new image, and a matching session row on the RDS/broker side later.

## State
- **Nothing was loaded:** the run failed before saving bills; AZ's stored data is as of its 11-15 run. No archive, no LegBot. The S3 lock for az is released the same way as NM's (the task exits through the scraper's normal path); I did not re-read it.
- **AZ is live.** Until this is fixed, every AZ run (weekly Wednesday 12:00 UTC from now, and any manual one) will fail the same way in the first minute, so AZ's data will not update. **NC's run (nc-b9ac274ee86a, revision 68) started at 12:00 and is still running.**

## Needs from you
A fix in openstates-scrapers (a v66 image), or whatever you decide for the 2027 session. I will not run AZ again, change the manifest or touch the image without a GO note and the user's word.
