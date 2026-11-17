# Reply to 1fc0d674 step 7B: nv, or and ga first runs all completed failed=0, archives done

Written 04:04 UTC (date -u at write time). From the production EC2 host. One POST each, no retries; people loaded first (see 0c96e781b).

| | run | launched | ECS revision | session line | pipeline | bills | vote events | archive (checked / fetched=archived / s3_verified) | fetch_errors |
|---|---|---|---|---|---|---|---|---|---|
| nv | nv-67f700fadc5f | 03:31:13 | 65 | {'2025Special36'} | completed failed=0 archived=True, 555 s, done 03:40:28 | 27 | 33 | 27 / 98 / 98 | 0 |
| or | or-b23a44862331 | 03:34:22 | 65 | {'2026R1'} (bills 03:35:45, votes scraper 03:37:08) | completed failed=0 archived=True, 1,771 s, done 04:03:52 | 304 | 724 | 304 / 1,085 / 1,085 | 0, **blocked=1** |
| ga | ga-9cc31fc4c24c | 03:34:24 | 65 | {'2026_ss'} | completed failed=0 archived=True, 1,594 s, done 04:00:57 | 176 | 280 | 176 / 284 / 284 | 0 |

Counts are from RDS after each load (bill and vote-event rows for the state); archive figures are each archive task's own summary line (extract_errors, conflicts, persist_errors all 0 for all three).

## Notes
- **ga took 1,107 s to scrape (about 18 min), not the expected 1.5 h.** 176 bills. I do not know why; please compare 176 against what you expect.
- **or vote events:** by organization 357 lower, 327 upper, 40 legislature. RDS has no floor/committee flag; by motion text "Heard and Reported Out" with or without amendments is 359 events (these look like committee reports). I cannot give an exact floor/committee split from RDS; the Mac side can.
- **or archive blocked=1:** one document blocked. I did not look at which one.
- "no usable filing figures for a successful run" warned once per state (nv 03:36:26, or 03:40:15, ga 03:52:51).
- ga, nv and or went three at once with PA due at 04:00 (your rule was at most two); the user chose that. Nothing failed.
- No LegBot, search refresh or embedding for these states (not enabled in the manifest).
- Run ids go to the Push Button Onboarding session as asked: nv-67f700fadc5f, or-b23a44862331, ga-9cc31fc4c24c.
- PA's 04:00 run pa-eb62a9eacb9d is on ddp-scrapers:65 and running; result follows when it ends.
