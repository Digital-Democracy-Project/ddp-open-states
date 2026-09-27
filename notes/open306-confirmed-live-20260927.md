# OPEN-306 confirmed live -- HCONRES 89 (the exact record that crashed the scraper twice) now processes cleanly

**Re:** `open306-v29-deployed-20260927.md` (this branch).

Triggered `POST /trigger/openstates-scrape/usa` directly (checked for in-flight jobs first --
clean). Both chambers completed: `openstates_usa_scrapes: completed duration_seconds=197.5
failed=0 total=2` -- no crash, much faster than the last crash-then-continue cycle (~29 min).

**Direct confirmation, not just an absence of failure**: pulled the actual CloudWatch log for the
chamber=lower run (`usa-6e338e0d9c9e`) and confirmed it re-encountered `HCONRES 89` -- the exact
bill/vote that crashed this scraper twice (2026-09-26 03:08 and 22:28) -- and this time completed
cleanly: `{"status": "ok", "found": 540, "duration_s": 509}`. No traceback. `"Concurrent
Resolution Rejected"` is now a normal, direct hit in `senate_statuses` (added as part of the
fix), so this didn't even need to exercise the `safe_lookup` graceful-degradation path -- the
known case is just fixed outright, exactly as the PR described.

**Also incidentally confirmed the overlap-protection discussion from earlier**: the regular
03:00 UTC daily cron fired right on schedule a few minutes after my manual trigger finished --
two more `usa` runs, both clean `EmptyScrape` no-ops (nothing left to find since my manual run
already cleared it). No conflict, no crash, no duplicate work -- `cloud_collector.py`'s
`SourceLock` behaved exactly as OPEN-187's own docs describe.

**OPEN-306: confirmed working live, closing out.**
