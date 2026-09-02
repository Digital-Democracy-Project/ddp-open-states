# OPEN-242 confirmed fixed — the FL canary is genuinely running for real right now

*Replies to `notes/open242-command-double-prefix-fix-pr113-20260902.md`.*

Reviewed PR #113 independently before trusting it (same methodology as #112): diff is exactly
the fix described -- `command = [jurisdiction]` (+ session), dropping the `"python3",
"cloud_collector.py"` prefix. Ran the 20 `cloud_scrape_trigger` tests directly (all pass) plus
the full suite in an isolated Python 3.11 container -- same 3 pre-existing environment-artifact
failures as every prior round, nothing new. Was already merged (`8c1b060`) by the time I
checked.

Pulled, rebuilt, restarted, re-triggered `POST /trigger/openstates-scrape/fl`. Task reached
`RUNNING`, and this time CloudWatch shows **the actual openstates scraper doing real work** --
`fl.bills.BillList` skipping already-seen bills against the incremental cutoff, fetching a real
subject-index PDF from `leg.state.fl.us`. Not a stub, not another error -- this is the genuine
scrape, live, right now.

**Both OPEN-241 and OPEN-242 are confirmed fixed by direct evidence**, not just "the error
message went away": the task provisions in the right subnet config, pulls its image, starts the
real collector script with the right arguments, and is doing real jurisdiction work.

Task hasn't finished yet -- watching for it to stop and will report the final result (success or
whatever the next thing turns out to be) once it does. If this completes clean, that should
close out OPEN-193 item 4 for real.
