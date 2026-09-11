# Go-ahead: run fl's commit via the new Fargate trigger, not the bare EC2 venv

Ramon's explicit go-ahead: proceed with `fl`'s `recompute-diff-order --commit`, now using
OPEN-268's new Fargate path instead of this host's bare venv -- this is exactly the case that
mechanism exists for. No more waiting on `ddp-broker`'s nightly window; the commit runs
isolated on its own Fargate task, so the resource-contention reason `fl` was held for
no longer applies.

```bash
curl -X POST "http://localhost:8001/ddp-sync/v1/trigger/openstates-backfill/fl?subcommand=recompute-diff-order&mode=commit" \
    -H "Authorization: Bearer $DDP_SYNC_API_KEY"
```

**Before running it**, per the established discipline: a fresh `mode=dry-run` immediately
before the commit is still worth doing, even though `fl`'s dry-run was already confirmed
clean and spot-checked earlier (`7685 bills checked | unchanged=17325 corrected=2712
nulled=1`, 6/6 spot-check match) -- enough time and a `ddp-sync` redeploy have passed since
then that a quick re-confirmation costs little and matches how every other jurisdiction in
this backfill has been handled so far.

Once `fl`'s commit completes, report the result here (the trigger's `output` should show the
real commit summary, same shape as the dry-run but reflecting what was actually written) and
move on to `va` next -- same pattern: dry-run, spot-check sample sent here if needed, go-ahead,
commit, report, next. `wa` and `us` remain after that.
