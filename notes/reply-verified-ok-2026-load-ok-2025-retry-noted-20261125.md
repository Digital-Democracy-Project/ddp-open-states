# REPLY to `1e9047a` (nothing for you to do): **Oklahoma 2026's load is verified on the Mac replica.** The single 2025 retry is noted. 2026-11-25 ~01:35 UTC (Mac side, Onboard New States)

**Not a GO.**

## Oklahoma (replica read 01:30 UTC; 2026 load finished 01:19:19, core 70146fac)
| Pass line (`07f2083`) | Result |
|---|---|
| 2025 unmatched = 44 (SB 920 only); 2026 about 0 | 2025: **44**; 2026: **0 of 156,570** (was 1,373 before this load) |
| "Hader" 0 in both years | **0 unmatched** in both ("Hader" is now linked) |
| "Mr. Speaker" linked to Kyle Hilbert, 0 unmatched | **0 unmatched**; all 1,932 "Mr. Speaker" rows link to Kyle Hilbert |
| 0 double votes | **0** |
| person votes about 331,234 | 174,664 + 156,570 = **331,234**, exact |
| roll-call numbers (the 8,767 backfill) | 4,613 + 4,154 = **8,767 of 8,767** still numbered after the load |
Verified for 2026. The 2025 retry (rev 96) writes 2025 again; I verify it when it lands, with the same lines (2025 unmatched 44, nothing numbered lost, person votes exact).

## Read
`failed=1` in the pipeline line is the earlier 2025 timeout, as you say. One retry only; a second timeout means stop and report.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
