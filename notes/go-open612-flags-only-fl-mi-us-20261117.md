# GO: give US Congress, Michigan and Florida's archived documents their missing bill-version flag (OPEN-612), as in request `1255b07`. 2026-11-17 (Mac side)

**Ramon's go:** "2. Go", his reply on Slack to "OPEN-612: go for request 1255b07?" (relayed to this session by the Project Manager session, 2026-11-17). That is the go for exactly the three `--flags-only` runs in `request-open612-flags-only-us-mi-fl-20261117.md`, nothing more.

**The request is the instruction.** Read it in full; this note only adds what changed since it was written.
* **Since the request:** v64 = `ddp-scrapers:67` is live (`1dc37e5`). The command (`recompute-diff-order --flags-only`, OPEN-492 `249ed268`, OPEN-498 `6aed98cc`) is in v64's core as in v62's; nothing about it changed. Use the same host and tool setup as the 11-16 baseline passes (core on `PYTHONPATH` in a throwaway worktree), at the core of the live image.
* **Order:** fl, then mi, then us. One state at a time.
* **Gate per state (from the request):** the dry run's flag summary shows `set` = the state's count of documents with no flag (fl 20,072, mi 14,458, us 92,768 on the Mac replica 11-17; a later archive may have added a few: report the number you see), `changed` = 0, `not a version` = 0, and "diffs untouched (--flags-only)". Then `--commit`, then a second dry run showing `set` = 0.
* **Window:** not while that state is being scraped or archived (us nightly 03:00 UTC; mi and fl Sunday 02:00), and not during the EC2 api-v3 rebuild (`0ee8404`) if it is still in progress.
* **Report** per state: the dry-run summary line, the commit line, the second dry run. The Mac side then re-counts on the replica and re-reads the five spot-check bills in the request.

## Not authorized
Anything but the three `--flags-only` runs: no comparison rebuild, no `--baseline-only`, no other state, no scrape, no broker step (the broker's version-order refresh the request mentions waits for its own go), no api-v3 change.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
