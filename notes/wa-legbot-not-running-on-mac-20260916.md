# Checked: no WA LegBot run has reached the Mac -- only MI is active

Ramon asked me to check whether a Washington LegBot pipeline is running, since you're expecting
one. Checked both logs directly on the Mac:

- **`ddp-sync.log`**: every `scraper_triggered_legbot_start`/`session_pipeline_run_start` line
  ever logged here is FL or MI -- no WA entry at all, ever, in this log's history. The only
  active run right now is still MI's (`run_id=cce7bb54-8ded-449d-9e9d-f6990fef0d2d`, started
  2026-09-14 21:16:11, still going).
- **`cams-server.log`**: only one active worker (`w1136/pid...`) and one dispatch caller
  (`caller=ddp_sync`) in the recent window -- consistent with just the MI run, nothing else in
  flight.

**This doesn't necessarily mean WA's own pipeline hasn't run on your side** -- it means no WA
archive->LegBot trigger has reached this Mac's ddp-sync/CAMS to dispatch a `session_pipeline_run`
here. Two possibilities, from what's visible on this side:

1. WA's archive step hasn't completed/dispatched yet tonight, or
2. It ran and hit the same silent-no-op bug as tonight's `us` archive
   (`legbot-trigger-false-negative-on-transient-network-blip-20260916.md` above, now tracked as
   **SYNC-66**) -- `resolve_touched_sessions()` treating a transient api-v3 connection failure
   identically to "genuinely nothing touched." Worth checking WA's own archive log for the same
   `Local api-v3 unreachable` / `archiver_triggered_legbot_no_sessions_touched` pair around
   whenever its archive finished tonight -- I can't see that from the Mac side, only whether a
   dispatch actually arrived here (it didn't).