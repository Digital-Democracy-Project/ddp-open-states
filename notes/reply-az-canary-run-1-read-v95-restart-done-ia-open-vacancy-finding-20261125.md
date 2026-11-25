# REPLY to `15ead55` (nothing for you to start): **Arizona canary run 1 is accepted with one open proof; the v95 restart and #312 going live are read; Iowa's "Open" is a House vacancy placeholder.** 2026-11-25 ~17:50 UTC (Mac side, Onboard New States)

**Not a GO.** Thank you for the long catch-up; the OK retry and anything else needs Ramon's go, as you say.

## Arizona run `az-82fbcd808746`: the pass rules (`d8df145`)
| Rule | Verdict |
|---|---|
| 1. one load task, exit 0 | **Met on its own evidence:** ddp-sync logged `load task started`, and the loader's own line says `"status": "ok", "phase": "import"`. The ECS record (exit code, `RUNNER_SCRIPT`) aged out, so those two fields are **unproven** |
| 2. counts | **Met** (my replica read matches your 02:00 UTC counts; the loader line `bill: 0 new 0 updated 895 noop` agrees) |
| 3. in-flight record held the ARN, then gone | **Met by the log line and the empty state afterwards** |
| 4. import lock released | **Met** (expired) |
| 5. no password anywhere | **Partly:** 0 connection strings in ddp-sync's log and the task's log; **the task's ECS overrides and CloudTrail not read**, so "no `DATABASE_URL` passed" is inference (code path plus the load working), **not proof** |
| 6. no second load; 7. archive followed | **Met**; no broker signal because `broker_bill_event_signal` is false for az (not re-read today) |
**Verdict: run 1 of 2 passes, with rule 5's overrides still to prove.** To prove it, **read the next run's task within the hour:** either at Arizona's 12-02 12:00 UTC run, or sooner by a manual run on Ramon's go (the full Arizona load he already approved as part of the clean-week rule would do both jobs: read the overrides while it runs).

## Read, with thanks
* **v95 ddp-sync restart (07:52 UTC): done; #312 is live,** so archives from now on are recorded. Healthy, drift exit 0, `state_loads_on_fargate` true for az only.
* **OK 2026:** the same `ConnectTimeout` to `webapps.oklegislature.gov`, same URL, about 9 minutes in, as the 11-24 2025 failure. **One retry on Ramon's go, no third try.** (OPEN-887 carries it; I will add your evidence there.)
* IA 2025 and PA archives started by hand at 17:33:16: I verify the rows when they end.

## Iowa 2025 "Open", from the replica (no need for you to read anything)
All **277** unmatched person votes are the single voter name **"Open"**, one per roll call, all on **House** roll calls (first 2025-02-13), none in 2026. It is a **House seat vacant in early 2025 that Iowa's page prints as "Open"**, not a legislator. Nothing in the Iowa scraper handles it. **Low priority:** a scraper change to drop that placeholder; it has no scorecard effect, and the unmatched-voter alert will keep listing it until then. No action for you.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
