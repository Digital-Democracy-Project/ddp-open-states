# Request: release ddp-sync `766ff6c` (a probing state is on no scrape list) on the EC2 broker host, 2026-11-02

Ramon merged ddp-sync **PR #261** at 19:42:52 UTC; merge commit **`766ff6c`**. It is step 1 of pilot #2's rollout (Pennsylvania, Nebraska, Louisiana: OPEN-478, 479, 480). **Nothing else is being asked of you in this note.**

## What it is
Two files, 24 insertions, 3 deletions, against what you run now (`2ea2c06`): `src/ddp_sync/services/jurisdiction_enrollment.py` (the manifest-derived `scrape_primary` and `scrape_secondary` lists now leave out a state whose status is `probing`, as they already did for `paused`) and its test. No config, compose or secret change. **It changes nothing today**: the manifest this host holds (`76c271c`, 10 states) has no `probing` state. It matters only once the Pennsylvania, Nebraska and Louisiana entries arrive, which is why it must be live first.

## What I need
1. **Gates:** nothing in flight (in-flight Fargate record 0, no ddp-sync job running), a quiet moment (not near 02:00, 02:30 or 03:00 UTC). Tag the running image first, as you did before, for rollback.
2. **Pull** `/opt/ddp-sync` fast-forward to `766ff6c` (`git status` should be clean: your compose edit was committed by #260). **Restart** ddp-sync the usual way.
3. **Read-only checks afterwards:** the start-up log line `jurisdiction_manifest_agrees ... mode=authoritative`; the scheduler's job count (it was 19); no `Traceback` or error line; and that the running code has the rule: the module's `_UNSCHEDULED_STATUSES` reads `("paused", "probing")` (ask the loaded code, no job started).
4. **Reply** with: the revision now running and the time (UTC), the job count, and anything unexpected. If any check fails, stop and roll back to the tagged image.

## Not asked
- **Do not pull ddp-open-states** for this: the manifest entries (ddp-open-states PR #321) are not merged. I will post a separate request when they are, and it will say to recreate api-v3.
- **Do not touch** the Stage 2 drafts (ddp-sync #262, ddp-open-states #322): they must not be pulled until Ramon says go.
- The Mac's ddp-sync is Ramon's side; this note is for the EC2 host only.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
