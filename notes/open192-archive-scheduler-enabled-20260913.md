# OPEN-192: OPENSTATES_ARCHIVE_ENABLED flipped to true -- real scheduled archiving now live

With Ramon's explicit go-ahead. Checked for a quiet window first (one long-running Fargate
collection task in flight, safe to restart through per OPEN-251's proven reconciliation; no
other imminent scheduled job) before restarting.

Flipped `OPENSTATES_ARCHIVE_ENABLED=false` -> `true` in this host's
`infrastructure/docker-compose.prod.yml`, restarted `ddp-sync`. Confirmed clean:

- `OPENSTATES_ARCHIVE_ENABLED=true` live in the running container.
- All 10 jurisdictions now genuinely registered on their own weekly schedule (not just present
  in config): fl/ut Monday 05:00, az Tuesday, wa/va Wednesday, mi/nc Thursday, ma Friday, al
  Saturday, us Sunday -- all at 05:00 UTC.
- The one in-flight Fargate job (ma) was resumed cleanly across the restart, zero orphaning --
  same OPEN-251 mechanism already proven working twice today.

**Today is Sunday, so `us`'s archive job is scheduled for real, automatically, at 05:00 UTC
today** -- under an hour from this post. This will be the very first genuinely-scheduled
archive run this host has ever had (every prior "success" was a manual validation trigger,
never the scheduler itself). Watching for it and will report the real result either way.
