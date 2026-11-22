# Reply: OPEN-642 Florida full re-import ended with 3 of 9 sessions FAILED (2024, 2025, 2026). Six loaded with links.

From DDP Prod Agent, 2026-11-22 23:50 UTC. Started 02:09:34 UTC 11-22 (202, full true, nine sessions). Pipeline `openstates_pipeline: done archived=True failed=3 sessions=9 status=failed duration 77,087.7 s` at 23:34:22 UTC. Not retried.

## Per session (run ids in the order the pipeline ran them; the session-to-run mapping is my reading of that order, matched against what is in RDS)
| Session | Run id | Result |
|---|---|---|
| 2023 | fl-5ce75d1af523 | loaded 16:34:46 UTC (collection 14 h 19 min). **3,228 links** |
| 2023B | fl-767a288d0e16 | loaded. 12 links |
| 2023C | fl-0911765b66d9 | loaded. 20 links |
| 2024 | fl-9cd93ad10324 | **FAILED** at 23:01:41 UTC after about 6 h 6 min |
| 2025 | fl-db15e4b6700f | **FAILED** after 2 min 33 s (23:04:14) |
| 2026 | fl-bbe69b7fc382 | **FAILED** after 3 min 39 s (23:07:53) |
| 2026D | fl-368f94d39489 | loaded 23:11:32. 5 links |
| 2026E | fl-af368d335c21 | loaded 23:26:25. 146 links |
| 2026F | fl-2801d407f0fb | loaded 23:31:06. 12 links |

## The failure (Fargate log, CloudWatch; the same error on all three runs I read)
`playwright._impl._errors.Error: Page.goto: net::ERR_TOO_MANY_REDIRECTS at https://flhouse.gov/Sections/Bills/bills.aspx` then `ERROR: fl scrape failed, exit 1` (ddp-sync: `collection failed ... Essential container in task exited exit_code=1`). I read the error for the 2025 and 2026 runs and for the one that ended at 23:01:41 (the 2024 run); the site looks like it started refusing the scraper after the long 2024 run. I have not tested this.

## What that leaves in RDS (read only)
- **2024, 2025, 2026: bills 1,902 / 1,959 / 1,897 with their last update 07-24, 07-18 and 08-29, and 0 links.** Nothing from this re-import reached them. Your expectation for 2026 (about 203 links on 80 bills) is **not met**.
- **Loaded:** 2023 (1,828 bills, updated today, 3,228 links: companion 1,292 "companion bill(s) passed"/"Identical", related 1,936 "Compare"/"Linked"/"Similar"), 2023B, 2023C, 2026D (6 bills, 5 links), 2026E (22, 146), 2026F (5, 12).
- The knowledge-base run after the pipeline: bills 0, failed 0.
- I did not run the FL scorecard validators (the broker's next FL sync has not been read) nor count FL BillRelation.

## State
No retry, nothing forced. The FL lock is released. FL is a weekly Sunday 02:00 UTC state; the next scheduled run is 11-29. A re-run of 2024, 2025 and 2026 needs your direction and Ramon's go in my session.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
