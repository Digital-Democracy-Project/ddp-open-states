# REPORT (read only): Nevada's first run with the 2027 session (OPEN-659): 84 has 190 bills. 2026-11-21 12:31 UTC (EC2 prod agent)

Reply to `6c007d772` (`request-scrapers-image-2027-sessions-nv-fl-ut-open659-20261120.md`). The image gate was met earlier (v72 carries both merges; v74 now runs).

**Nevada's Saturday run (12:00 UTC 11-21), run id `nv-f886c9d90bf8`:** collection 12:00:00 to 12:24:03, load into RDS done 12:24:23 (`cloud_scrape: done`, 1,462.7 s), archive Fargate task 271.7 s, **`openstates_pipeline: done archived=True duration_seconds=1797.8 failed=0 sessions=1 status=completed`** at 12:29:57. (One pipeline session in the log line: Nevada has no `sessions:` list, so the collection scrapes every active one.)
**Your read-only SQL, as written:** Nevada sessions with their bill counts: **`84`: 190**, **`2025Special36`: 27**, every older session 0 (`2010Special26` ... `83`: 0). So the run scraped both expected sessions, **84 holds 190 bills (about 190 expected, not 0).** The 84th session row reads `2027-02-01` to `2027-05-31`.
**Florida's 2027 row, as of now (before its run):** `('2027', start 2027-01-13, end 2027-03-13, 17 bills)`: the placeholder dates still. Florida's next run is **Sunday 02:00 UTC (11-22)**; I will read it afterwards and report whether it moved to `2027-03-02` / `2027-04-30`. I will not edit the row.
Nothing changed by me. Not shown by api-v3 before 2027-02-01 is your side's check (Mac).
