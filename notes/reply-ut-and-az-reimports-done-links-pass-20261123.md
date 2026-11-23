# Reply: Utah 2026 (`d7ce0d8`, OPEN-775) and Arizona 57th-2nd-regular (`753a793`, OPEN-649) full re-imports DONE. Links as expected

From DDP Prod Agent, 2026-11-23 19:49 UTC. Both started 14:16 UTC on Ramon's overnight pre-approval (rev 83). Both ran through the **18:19 ddp-sync restart** (`4d6e8dc1`) and resumed from Redis.

## Utah: ut-1777beb302dc
Collection done 19:38:37, **load done 19:41:56 UTC** (duration_seconds 4,928 after the resume). Because it resumed, its archive did not run: I triggered it by hand at **19:49:22** (202; the archive is running). **Counts (RDS, read only):** UT 2026 **1,016 bills**; related-bill links **related, "coordination clause": 41; companion: 0**; before: 0 links. **Spot checks:** HB 223 lists HB 32, SB 153 lists HB 209 and HB 361, each `related`, "coordination clause". **Pass.** Not read: "mode full" line, fetch errors, api-v3 call (needs the API key). Broker: its next Utah sync should leave Utah `BillRelation` unchanged and the Utah scorecard checks clean; I will run them after tomorrow's chain (no companion links, no scorecard change expected).

## Arizona: az-183293f2bebd
Collection done 17:45:03, **load done 17:50:17 UTC** (12,803 s); archive done in Fargate (`az-archive-92350bb4bc22 ok, archived=251`, 17:5x); ddp-sync never logged it because of the restart, and I triggered the archive again at 18:21:34 for the LegBot hand-off (archive task done 18:23:07). **Counts (RDS):** AZ 57th-2nd-regular **2,190 bills**; **companion, "Identical to": 336 links on 324 bills; related, "See": 7,769 links on 1,167 bills**; before: 0. (Your dev-copy measure was 148 links on the 50 polled bills: companion 8, related 140; I have the whole-session numbers you asked for.) **Spot checks, all as you wrote:** HB 2042 lists SB 1278 `companion` "Identical to" and HB 2125, HB 2141, SB 1098, SB 1279 `related` "See"; HB 2689 lists SB 1051 as `companion`. **Pass.**
- **Broker, after its next Arizona sync:** I will report Arizona `BillRelation` rows (dev copy: 0 before, 8 after the polled bills), the scorecards of HB 2689, HCR 2004 and SB 1200 against your numbers, and `validate_scorecards --jurisdiction AZ --all`, `validate_scorecards --bills --all` and `reconcile_scorecards --jurisdiction AZ`. The broker syncs bills at 05:00 UTC; this will be in my Stage 5 note after tomorrow's chain.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
