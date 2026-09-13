# Correction to my last note: archive DOES write final flow-status, just not in-flight reconciliation

Ramon caught an imprecise claim in `notes/open192-archive-jobs-not-reconciled-on-restart-
20260913.md`. Traced it precisely this time instead of asserting from a partial grep:

- **Final flow-status write (`_write_flow_status`)**: real, confirmed at
  `openstates_archive.py:537` -- same mechanism scrape jobs use. If the watching process is
  still alive when an archive job finishes, its result lands in Redis normally.
- **In-flight reconciliation across a restart (OPEN-251's `record_started`/
  `reconcile_inflight_fargate_jobs`)**: genuinely absent for archive, confirmed by tracing the
  actual call site -- that registration lives inside `run_cloud_scrape()`'s own launch wrapper
  in `cloud_scrape_trigger.py`, not inside the generic `_wait_for_task_stop()` helper both
  scrape and archive share. `openstates_archive.py`'s `_run_archive_fargate()` calls
  `_wait_for_task_stop()` directly, bypassing that wrapper -- so it never registers.

Net effect, precisely: a restart while an archive job is still running doesn't lose the task
itself (still runs fine in AWS) or corrupt anything, but the specific coroutine that would have
written that run's final flow-status is gone -- so that one run's result silently never lands
in Redis, even though a future run's would. That's what just happened to the `us` job I
restarted through today. Same underlying gap as my original note, just more precisely stated.
