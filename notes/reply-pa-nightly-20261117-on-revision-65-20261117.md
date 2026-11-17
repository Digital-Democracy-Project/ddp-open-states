# Reply (read only): PA's 04:00 UTC nightly on revision 65 completed clean

Written 14:19 UTC (date -u at write time). From the production EC2 host.

- Run pa-eb62a9eacb9d, ECS revision ddp-scrapers:65 (read at 04:00:50). Collection and RDS load done 11:09:30 UTC (25,768 s of scrape); archive task done 11:11:32 (121 s); pipeline done 12:23:36: **status=completed failed=0 sessions=1 archived=True, 30,217 s (8 h 24 min)**.
- It finished inside ddp-sync's 12 h limit, unlike 11-15. It was not touched by the api-v3 rebuilds at 03:50 and 05:17 or by the manifest rollouts.
- Not read: PA's bill counts, vote events and archive totals (I did not pull them); say if you want them.
