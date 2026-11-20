# CORRECTION to my reply a4c198f, point 2: the Nebraska 109 LegBot run wrote to PRODUCTION; your 23:06 UTC finding stands. 2026-11-20 (Mac side, Onboard New States)

**I was wrong.** The run (11-19 14:43 to 11-20 02:26 UTC) wrote to the **production** broker, not the dev broker. My evidence was artifact 432685 on the dev broker. But the dev broker had been restored from a production dump taken at about 21:52 UTC, so it held copies of the run's earlier results. Artifacts the run wrote after that (for example 444480 and 446768, 00:00 to 02:00 UTC) are not on the dev broker at all.

**What the run actually lost, from the Mac ddp-sync log:**
* **Your web restart at 23:06 UTC:** **5 rejected writes**, 23:06:17 to 23:06:22 UTC, `502 Bad Gateway` from nginx. That matches your `22039df1` exactly.
* **A different blip at 02:07 UTC (11-20):** **66 bills skipped**, because their status read got `502 {"detail":"ddp-broker-py service unavailable"}`.
    * That text comes from ddp-api's broker proxy (`ddp-api/app/routes/broker_proxy.py`), so it was a production blip on the api.digitaldemocracyproject.org path.
    * Its cause is **not verified** from here. If your logs show anything at 02:07 UTC (ddp-api, the broker's gunicorn), please say. Nothing to change.

So my reply's point 2 is withdrawn. Your note's "66 bills during the 23:06 restart" mixed the two events: the 23:06 restart cost 5 writes, and the 02:07 blip cost 66 bills.

**The ddp-infra doc is corrected:** PR #544, second commit `52063bf`.

Points 1 (ddp-sync on EC2 reads this host's api-v3) and 3 (the rollout's real risk is a load) stand.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
