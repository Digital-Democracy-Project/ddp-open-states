# REQUEST (not a GO): **Mississippi: a people load, then a rescrape of four bills, to fix four unmatched roll-call votes (OPEN-899).** 2026-11-27 ~00:45 UTC (Mac side, Onboard New States)

**Not a GO.** Ramon gives each go in your session naming this note. Mississippi is live (since 05:50 UTC 11-26); this request is small and does not block it.

## What I need from you
1. **Part 1: the people load for Mississippi** (people #56, merge `1eea3bce`, adds the roll-call name "Luther-Waldo" to Rep. Beth Waldo). Run `os-people to-database ms`, the command `run-people-refresh.sh` runs per state (no dry run exists; lint passed). Gates: no Mississippi task in flight; record "now" as the restore point. Report the output lines and the Mississippi people count before and after (expect no change in the number of people).
2. **Part 2: rescrape four 2026 bills on the v98 image** (`ddp-scrapers:100`, db `ddp-scrapers-db:27`; scrapers #298, merge `1c02aae8`, is in it): **SB 2838, HB 515, HB 1330 and HB 1924**. Why: a roll-call line like "Rhodes, Simmons D." wrapping to "T. (12th), ..." was read as a stray blank voter; #298 fixes the parser. The first three are Senate roll calls (passage 02-04, passage 02-18, conference report 04-01); HB 1924 is a House veto override (04-15, the "Luther-Waldo" vote).
   * **How:** a rescrape by bill (`bill_no=`, as `cloud_collector.py ms session=2026 bill_no=...` supports). **Please tell me whether a ddp-sync trigger can pass `bill_no` on Fargate.** If not, **do not run a full Mississippi 2026 session** (4,116 bills, hours) without telling me first: say so and I will ask Ramon.
   * **Not additive for votes** (RUNBOOK, OPEN-437): a bill rescrape updates its vote events in place and deletes that bill's other stored vote events the scrape does not write, so each bill must yield **all** its votes. **Preview first** (the cloud-collector's preview/dry mode if it has one; report the vote counts per bill it would write against what is stored), and **do not run for real until a go note.**
3. **Part 3: check:** unmatched Mississippi person votes: 4 in 2026 today (3 for "T. (12th)", 1 for "Luther-Waldo"), expect 0; "Simmons D. T. (12th)" appears once per roll call; the three Senate roll calls' yes counts equal the printed totals (each was one too many). I verify on the Mac replica afterwards.

## Not authorized
A full Mississippi session run; any other bill or state; a manifest change; `replica_routing`/`legbot_replica`; a ddp-sync restart.

Tickets: OPEN-899 (OPEN-669, OPEN-146).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
