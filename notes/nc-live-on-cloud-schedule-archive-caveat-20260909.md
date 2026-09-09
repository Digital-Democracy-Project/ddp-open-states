# NC is live on this host's cloud scrape schedule -- archive cadence is a separate, unresolved question

*Follows up on `notes/live-sync-schedule-values-and-sync-mechanism-20260909.md`.* PR #125
merged. Pulled `ddp-sync` to `main` (`c1136e7`) -- real merge conflict this time (upstream and
my local drift both touched `cloud_path.jurisdictions`), resolved by keeping upstream's version
(has `nc` added, which is what we want). Restarted.

## Confirmed live

```
openstates_secondary_scrapes: registered jurisdictions=['va', 'mi', 'ma', 'ut', 'az', 'nc']
sync_day=sunday sync_time=02:00
```

`nc` is also in `cloud_path.jurisdictions`/`memory_backend_jurisdictions` now, so its next
Sunday 02:00 UTC secondary scrape should route through Fargate/RDS like the others. NC's
Stage 6 scrape-cadence clock genuinely starts now.

## Caveat: archive cadence is unaffected by this

Same startup log: `openstates_archive: disabled — skipping` -- unchanged, this host's
`OPENSTATES_ARCHIVE_ENABLED=false` (deliberate, its OPEN-193-canary-only scope) means the
recurring *archive* schedule for `nc` (and every other jurisdiction) still doesn't run from
here. Not new or NC-specific -- same gap `notes/cloud-archiver-code-confirmed-logs-inconclusive-
20260909.md` already flagged: whichever host actually runs `openstates_archive` live needs its
own config/restart to pick up `nc`, separately from this scrape-side change.

So: NC's scrape clock starts today. Its archive clock depends on that other host's own config
state, which I have no visibility into from here.
