# FINDING (2026-11-24 02:49 UTC): the Washington nightly FAILED at 02:31 UTC: the legislature now lists session 2027-28 and the scraper does not know it. Washington is a LIVE state: it will fail every night until fixed.

- **Run `wa-69bec06e89b6`** (the 02:30 UTC nightly, ddp-scrapers rev 86 as the latest task definition; incremental): `collection failed ... exit_code=1`, **91.6 s**, `openstates_pipeline: done ... failed=1 status=failed`. Nothing was loaded, nothing retried.
- **Cause (Fargate log):** `openstates.exceptions.CommandError: Session(s) 2027-28 were reported by Washington.get_session_list() but were not found in Washington.legislative_sessions or Washington.ignored_scraped_sessions.` then `ERROR: wa scrape failed, exit 1` (`"mode": "incremental", "status": "failed", "duration_s": 2`). So `check_session_list` stops the scrape before any page is read: **`2027-28` must be added to Washington's `legislative_sessions` (or `ignored_scraped_sessions`) in the scraper** (the same date-switch kind of change as Georgia 2027-28 OPEN-605 and Arizona 2027 OPEN-632).
- **Not yet seen for other states:** the US (03:00) and Pennsylvania (04:00) nightlies run next; I will report them. Any state whose legislature lists a new session ahead of its start can fail the same way.
- **What I did not do:** no retry (it would fail the same way in 2 s), no change. WA's weekly pipeline and LegBot hand-offs depend on this scrape.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
