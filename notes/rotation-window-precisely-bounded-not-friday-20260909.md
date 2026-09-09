# Resolved: the break window is precisely bounded to THIS AFTERNOON, not Friday

*Replies to `notes/rotation-timeline-conflict-check-since-friday-20260909.md`.* Did the re-check
you asked for -- actual outcomes, not just firing timestamps, back through Friday. Short answer:
**every scheduled load since Friday actually succeeded, including as recently as this morning.**
The credential only broke sometime this afternoon.

## Evidence, in order

1. `ddp-sync`'s own logs, `cloud_scrape:` lines, Friday 2026-09-04 through today: every single
   `collection done, loading into RDS` is followed by a clean `done duration_seconds=N` --
   `fl`/`wa`/`va`/`mi`/`usa`/`az` all present, one unrelated MA data-conflict failure on 09-06
   (real bug, nothing to do with credentials). **Most recent confirmed-successful loads: `usa`
   at 03:10 and 03:35 UTC *today*, `wa` at 03:28 UTC today.** So this has NOT been silently
   broken since Friday -- every real production load through this morning actually worked.

2. I initially got confused by an apparent hash mismatch between `/opt/ddp-sync/.env`'s
   on-disk `RDS_DATABASE_URL` and the running container's live env var -- turned out to be my
   own test artifact (a trailing newline from `grep`), not a real difference. Corrected: **the
   file and the running container's in-memory credential are byte-identical**, confirmed by a
   matching hash both ways. So this was never a "stale file vs. fresh render" problem -- it's the
   same one value throughout.

3. That same, single, unchanged value: succeeded for `os-text-extract` (my RDS backfill
   dry-runs, ~00:41-04:05 UTC today) and for `ddp-sync`'s own loads (through 03:35 UTC today) --
   **then started failing** by the time of my first Fargate archive validation (13:37 UTC today),
   and still fails right now on a fresh direct connection test from this bare host.

## Conclusion

The actual RDS password changed sometime in the roughly 10-hour window between **03:35 UTC and
13:37 UTC today (2026-09-09)** -- not Friday. Whatever Ramon remembers rotating on/before Friday
either predates this file's own Sep 3 render (so this file already reflected it correctly, which
is why nothing broke until today) or is a separate event from whatever changed today. Worth
checking whether the RDS-managed master secret has an automatic rotation schedule in Secrets
Manager that could have fired today on its own, independent of anyone manually rotating it.

**No silent multi-day production gap** -- today's early-morning jobs are confirmed good. The
risk is still real but narrower than the last note implied: tonight's ~01:00-03:00 UTC cycle,
and anything triggered between 13:37 UTC and whenever this gets fixed.

## Next step

Once whoever can check Secrets Manager confirms *when* the secret actually changed (ideally
matching this ~03:35-13:37 UTC window) and re-renders `ddp-sync`'s `.env` with the current value,
I'll re-verify with the same direct-connection test before re-running the Fargate validation a
fourth time.
