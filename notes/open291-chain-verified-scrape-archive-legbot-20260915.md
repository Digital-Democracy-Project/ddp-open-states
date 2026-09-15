# Confirmed, by reading the code end-to-end: scrape -> archive -> LegBot chain is real and wired correctly

Follow-up to `open291-deployed-trigger-reenabled-mac-flag-check-needed-20260915.md`. Ramon asked
me to confirm the full chain rather than just relay the PR description, so I traced it directly
in the deployed source on this host:

1. `openstates_scrape.py::_run_scrape()` -- on a successful scrape, calls
   `maybe_trigger_archive_after_scrape(jurisdiction)` (OPEN-291, new).
2. That function checks the config-driven opt-in (`archive_config.enabled` +
   jurisdiction in `openstates_archive.jurisdictions`), then calls
   `run_single_archive_job(archive_jurisdiction, archive_config)`.
3. `run_single_archive_job()` routes through `_run_archive_with_hook()` -- **the same wrapper**
   every other archive path (the weekly cron, the manual trigger endpoint) already uses. Not a
   separate/bypassing code path.
4. `_run_archive_with_hook()`, on a successful archive, calls `_maybe_trigger_legbot_for_archive()`
   (SYNC-65, pre-existing) -- which is what actually reaches out to the Mac's ddp-sync over
   WireGuard to dispatch LegBot.

So the three-stage chain (scrape -> archive -> LegBot) is real, not just described in the PR
notes -- confirmed by reading steps 1-4 directly, not inferred from the docstring alone. The
existing per-jurisdiction weekly archive cron stays registered as an untouched backstop; the
debounce in `_run_archive_with_hook` (step 3's entry) is what stops it from double-running if it
lands close to a hook-triggered run.

This doesn't change the still-open ask from the previous note: the Mac needs to independently
gate the automated call at the very end of this chain (step 4's WireGuard hop, which sends
`X-DDP-Automated-Trigger: true`) on **its own** copy of `LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED`
-- please confirm/flip that when you get a chance, since EC2's own flag being `true` isn't
sufficient on its own for the chain to complete end-to-end.
