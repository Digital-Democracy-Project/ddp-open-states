# REPORT: LegBot on the Mac's idle time: NM was refused (flag off); Nebraska 109 full-session run started

Written 14:46 UTC 11-19 (date -u at write time), from the production EC2 host. **The user's words in session (pop-ups):** offered idle MLX time for a LegBot run on a new state; chose New Mexico, then, after the refusal below, "Run Nebraska now".

## New Mexico was refused (14:40 UTC, nothing written)
`POST /ddp-sync/v1/trigger/bill-artifact-generation` on the Mac, NM / 2026, all nine types, dry_run false: HTTP 200 in 1.2 s, run_id 11245bbbb473483ba49d606d16461bb4, **bills_considered 812, every bill `error: jurisdiction_not_on_rds_replica_allowlist: NM`**, 0 artifacts generated, no lock held. Cause (read from ddp-sync's code, SYNC-142 and SYNC-157): LegBot is only dispatched for states whose `enrollment.legbot_replica` is true in `deploy/manifest/jurisdictions.yaml`. On main as of now it is **ON for AZ FL LA MA MI NC NE PA US UT VA WA and off or absent for AL GA NM NV OR.**
**Request for you (the manifest is yours; I did not touch it):** if NM should get LegBot now that its comparisons are corrected (committed 05:17 UTC, a59a8e0e1), please set `legbot_replica` for NM (and AL, GA, NV, OR when ready), merge, and tell me when the Mac has pulled it. NM would then be about 812 bills.

## Nebraska 109 full-session run (started 14:43:03 UTC)
Same call as the NC and UT runs: NE, session **109** (109th Legislature 2025-2026; 1,847 bills in RDS), all nine artifact types, org research false, concept statements true, limit null, retry_failed false, dry_run false; detached on this host, log /home/bitnami/ops/ne-109-legbot-run-20261119.log. At 14:44 the broker held 3 NE bills and 18 artifacts (writes working). **I will not re-trigger (a 409 means it is running), will not restart ddp-sync, and will post the counts when the call returns** (the NC run took 23 h for 2,338 bills; expect about 15 to 20 h; the Mac-side trigger has timed out at 3,600 s before while the run continued).
For context, the gaps found in the broker (bills with no summary or other artifacts): FL about 205, WA about 268 (OPEN-297), US 158, VA 72, AZ 1; LA (10,468 bills, flag on) has no LegBot data yet.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
