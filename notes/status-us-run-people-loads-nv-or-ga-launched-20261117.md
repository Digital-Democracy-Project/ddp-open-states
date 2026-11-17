# Status on 1fc0d674 steps 5 and 7: US run clean, ga/nv/or people loaded, nv/or/ga launched (all on the user's word)

Written 03:35 UTC (date -u at write time). From the production EC2 host. Runs still in flight; results follow.

## Step 5: the 03:00 US run (revision 65)
- Run usa-a59ac5fbc86a (task dd6e8b8f50be..., ddp-scrapers:65, read at 03:00:51) then usa-b59ce583ef84. The second task's revision read was missed (it started 03:02:19; my read ran 03:01:51), so it is NOT verified.
- Pipeline done 03:21:23: status=completed failed=0 sessions=2 archived=True, 1,282.8 s.
- HR 1 (119-21), S 5 (119-1), HR 4 (119-28), HR 1968 (119-4): latest action still "Became Public Law No: ...".
- Warnings: only the launch-time "stall check could not read the task log" (once) and "no usable filing figures" (twice, 03:03:57).

## Step 6: Virginia was run early on the user's word (see 705f13aff): corrected 4,763, second dry run 0. `--expect` is refused without `--baseline-only`; I committed without it.

## Step 7A: people loads, real, 03:28-03:29 UTC (people main f6a7e832be, includes #24 and #25)
- ga: 594 created, 0 updated. The gate said about 236 (220-250); that is the number of files under data/ga/legislature. The loader also takes retired (329) and executive/other (29) files. The safe run showed 594 first; the user approved the real load at 594.
- nv: 226 created (63 current, 154 retired by file count); other names for Moore, O'Neill and the Cruz-Crawford entry present.
- or: 277 created; "Gregory Smith" present under Greg Smith.
- ddp-sync read current people at launch: nv 67, or 93, ga 240.

## Step 7B: manual runs (one POST each, no retry), revision 65 on all three per ECS
- nv-67f700fadc5f launched 03:31:13; scraper line: active sessions {'2025Special36'} (matches).
- or-b23a44862331 launched 03:34:22; session line not yet seen.
- ga-9cc31fc4c24c launched 03:34:24; scraper line: active sessions {'2026_ss'} (matches).
- ddp-sync accepted all three triggers, so it knows ga/nv/or after the rollout; no restart was needed.
- **Deviation from your rule "at most two pipelines at once":** or and ga were launched while nv ran (three at once, and PA is due at 04:00). The user chose this: ga's RDS load comes much later than the others'. Say if you want it recorded differently.

## Also done tonight (see 8946bd9b)
Step 3 rollout with two gates overridden on the user's word; md5 23c165c4fdbb48667844369b54f514db everywhere; /ddp/enrollment shows no newest_first true.

## Still to report
Per-run results for nv, or, ga: status, failed, bills, vote events (or: floor and committee separately), archived documents, ga archive fetched and fetch_errors; PA 04:00 result; the broker's re-read of the list.
