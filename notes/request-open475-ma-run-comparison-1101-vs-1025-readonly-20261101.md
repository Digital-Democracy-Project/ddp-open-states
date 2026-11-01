# Request (read-only): why was Massachusetts' 11-01 run slower than 10-25? (OPEN-475), 2026-11-01

Your 18:20 UTC update says MA's run was stopped at the 12-hour wait limit with nothing loaded. Ramon's decision (2026-11-01): **find out why first; no re-run, no limit change, no schedule change.** **Nothing here changes anything: do not stop, restart, re-run, launch, pull or edit anything.** Do not print secrets; redact log lines.

What I already know (from your 10-26 report and ddp-sync's config): the 10-25 run was an "incremental" run that re-walked almost the whole session (`bills: {'start': '2026-10-18T09:01:07'}`, found 12,260, 36,845 s, about 11,747 bills saved, no 429/403/timeout lines). The wait limit is 43,200 s, so there was only about 1.8 h of room. A cold-start run took about 9.5 h in the rehearsal. So a run only about 17% slower than 10-25 would miss the limit; the question is whether 11-01 was slower per request, made more requests, or got stuck.

## What I need, from CloudWatch `/aws/ecs/ddp-scrapers`
Streams: 11-01 `scraper/scraper/a400a49e2c1646e79264fa2047d3c1a6`; 10-25 `scraper/scraper/737b2599f0fd4f56b777d910ab5e5862`.
1. **How each run started:** the first 15 lines of each (redacted), especially the `bills: {'start': ...}` line. Was 11-01 incremental with a start date, or did it walk with no start date?
2. **Requests per hour for each run** (count of `malegislature.gov` requests in each clock hour of the run), split into bill-detail requests (`/Bills/194/...`) and everything else.
3. **Progress at the stop:** how many distinct bill ids the 11-01 run had fetched by 14:00:54, against the 10-25 run's total (about 11,747), and whether any bill id was fetched more than once (count the repeats).
4. **Slowness:** the 20 largest gaps between consecutive log lines in each run (seconds, with the line before and after), and the median gap per hour. Any single request that stalled for more than 60 s.
5. **Block or throttle signs:** any `429`, `403`, `Too Many`, `retry`, `timed out`, `ERROR`, `WARNING`, `Barracuda` or empty-response lines in either stream, verbatim.
6. If you can read it: the **task definition revision** MA's 11-01 task ran on (your Part 3 note said you could not read ECS; skip if still so, and say so).

Put the numbers in a table, 11-01 beside 10-25. If a number cannot be read from the log, say "not readable" rather than estimate. I will write the cause and a recommendation on OPEN-475; Ramon decides what changes. The 11-08 02:00 UTC run is the deadline for that recommendation.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
