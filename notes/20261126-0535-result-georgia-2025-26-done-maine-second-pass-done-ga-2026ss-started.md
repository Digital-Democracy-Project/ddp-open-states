# Result 11-26 05:35 UTC: Georgia 2025_26 DONE; Maine second pass DONE; Georgia 2026_ss started

Ramon approved Georgia 2025_26, then 2026_ss, then Iowa 2026s1 (one at a time) in this session.

## Georgia `ga?full=true&sessions=2025_26`
* Trigger 11-25 23:02:40 UTC (202). Collection done 02:26:06 (3 h 23 min); load into RDS done 02:35:58 (cloud_scrape 12,795 s); archive task 9,205 s, done 05:09:24. Pipeline `done`, `failed=0`, `archived=True`, 22,004 s in all. One try, no retry. The run was never stopped by the 45-minute stall rule and ran well under 12 hours.
* **Counts now on production (read-only), session `2025_26`: bills 5,480; vote events 2,517; person votes 279,904; person votes with no voter id 0.** Your estimate was about 2,500 to 3,000 bills; the run loaded 5,480. Please check that against Georgia's own site.
* `unmatched_voter_check` alerted once (`new_names=1`); the run's own alert, not investigated by me.
* Warning seen: `no usable filing figures ... expected marker missing` for `ga_session_2025_26.imported` (the same Fargate-load marker warning as Arizona).
* ddp-sync's task definition limit: my role cannot read ECS task definitions, so I still cannot tell you the runtime limit there. The run took 6 h 07 min without being stopped.

## Georgia `2026_ss` (started)
* Trigger answered 202 at 05:29:23 UTC (`ga?full=true&sessions=2026_ss`). Before the run production holds 176 bills, 280 vote events, 45,780 person votes, **35 with no voter id** (the Dickerson votes). Pass: those 35 drop to 0.
* Iowa `2026s1` follows after it finishes.

## Maine second pass
* `me?full=true&sessions=132R1,132R2,132S1`: done 04:35:32 UTC, 3 sessions, `failed=0`, `archived=True`, 22,407 s.

## Held
v96 rebuilds (api-v3, ddp-sync) wait for the Georgia 2026_ss and Iowa runs and for no state to hold a lock; api-v3 not before 07:00 UTC (scorecard chain).
