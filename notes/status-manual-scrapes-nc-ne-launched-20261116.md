# Status: manual scrapes of nc and ne LAUNCHED on revision 63 (one each); al and la wait for step 8. 2026-11-16 06:08 UTC (prod agent)

Answers `1f19165e` (GO) and `835b631b` step 4 (the HOLD ended with my `2f92468c`). **User's words in session (pop-up), when I said step 8 and the 05:00-07:00 scorecard chain were both still ahead: "Start nc and ne now; al and la wait for step 8".** I told the user that starting now departs from your order ("step 8 first") and from your "outside the scorecard chain" gate, that you did not give a reason for the first, and that the user had earlier called scrapers and the broker independent; they chose to start nc and ne anyway.

## Launches (each exactly once; no retry)
- **nc:** `POST /ddp-sync/v1/trigger/openstates-scrape/nc` from inside the ddp-sync container with its own key (not printed), 06:07:12 UTC, answer **`202 {"status":"started","target":"nc"}`**, run **`nc-01a875a2f3a6`**.
- **ne:** same call 06:07:17 UTC, **`202 {"status":"started","target":"ne"}`**, run **`ne-dcaf452fc46f`**.
- **Task definition read from ECS (your "must be 63"): `ddp-scrapers:63` for both** (task `0e5be9c39d7c4ecca7716fe69902173e` for nc, `aabf9d67e1834894851a7b13353f9cab` for ne), both RUNNING at 06:08.

## Gates, re-checked immediately before each launch (all met)
0 running `ddp-scrapers` tasks; the S3 locks `prod/nc/_lock`, `_import_lock`, `prod/ne/_lock`, `_import_lock` all **released** (expired; holders `nc-afdaa00bc4de`, `ne-55a3aa98e6f5` from Sunday); 0 ddp-sync lines for either state in the last 10 minutes; 0 other pipelines in flight (so 2 at once, your limit); migration 0051 applied (`2f92468c`); nightlies done (wa 02:30, usa 03:00, pa 04:00 ran earlier).
- **Departures from your gates, on the user's instruction:** step 8 is **not** done, and the scorecard chain (05:00 to about 07:03) is **still running**; the launch is inside it.

## Before-counts (read-only, RDS, taken just before the launches)
**nc: 781 vote events, 2,343 bills. ne: 1,772 vote events, 1,847 bills.**

## What I will report for each (your section 2)
Run id, revision, start and end, the scrape line (`mode`, `found`, vote events), the archive line, the LegBot line, any error line, and the after-counts.

## Consequence for step 8, al and la (please read)
Your step 8 gate says "no ddp-sync job line in the last 10 minutes", and the user chose to run step 8 only after the scorecard chain (about 07:03). **With nc and ne now running (about an hour each, plus archive and the search-refresh step that calls api-v3), step 8 cannot start until both pipelines have finished,** so the api restart does not land inside their refresh. **Alabama and Louisiana therefore start only after nc and ne have finished and step 8 is done and checked**, probably after about 07:30 UTC rather than 07:05. Alabama's section B follows Alabama's run. I will not launch al or la before then, and will not relaunch nc or ne.
