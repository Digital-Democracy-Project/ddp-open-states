# Ramon: run the Step 3 archive validation across all jurisdictions in parallel

*Follow-up to `notes/step3-first-clean-pass-20260909.md`.* `ut` alone came back clean but
`archived=0` (nothing pending), so it never literally exercised the `GLACIER_IR` upload path.
Ramon's ask: launch all archive-enabled jurisdictions in parallel against the fixed image/task
definition, both for broader coverage and to get a real archive (not just a clean no-op) from
whichever jurisdiction has something pending.

## Jurisdictions

The real, currently-committed `openstates_archive.jurisdictions` list (`ddp-sync`
`config/sync_schedule.yaml` -- NC is NOT in this list yet, PR #125 adding it is still unmerged,
so leave it out of this run):

```
fl  ut  az  wa  va  mi  ma  al  us
```

## Before launching: two things worth checking first, not skipping

1. **Michigan specifically** -- per the standing WAF-resilience rule, check there's no
   currently-running scheduled MI scrape or archive (`ecs list-tasks` on the `ddp-scrapers`
   cluster, or whatever visibility you have into the live schedule) before adding a manual MI
   launch on top of it. If one's already running, either wait or drop `mi` from this batch and
   note why.
2. This is a real production run, not a dry-run -- any jurisdiction with pending documents will
   genuinely upload to `ddp-bill-archive`. That's the point (literal `GLACIER_IR` proof), just
   flagging it's real writes, not a simulation.

## What to launch, per jurisdiction

Same shape as every `ut` run today: task-definition `ddp-scrapers:20` explicit revision,
`RUNNER_SCRIPT=cloud_archiver.py`, `DATABASE_URL` via the now-fixed live-resolve path (no manual
override needed anymore for anything using OPEN-260's fix -- confirm whichever launch mechanism
you use here actually goes through that, not a hardcoded value left over from earlier debugging).

## Report back

Per-jurisdiction: exit code, the parsed summary line (`fetched`/`archived`/`extract_errors`/
`s3_verified` etc.), and total wall time. Call out specifically:
- Which jurisdiction(s), if any, had `archived > 0` -- that's the one that gives us the literal
  end-to-end `GLACIER_IR` proof the original Step 3 ask wanted.
- Any jurisdiction that fails or behaves differently from `ut`'s clean pattern -- don't average
  it away, each one's result matters on its own.
