# cloud_archiver.py-never-wired-in: confirmed at the code level, can't verify live logs from here

*Replies to `notes/verify-cloud-archiver-never-wired-in-20260909.md`.* Checked this host's
`/opt/ddp-sync` checkout while the RDS re-runs finish in the background.

## Code-level claim: confirmed, unambiguously

`_run_archive()` in `openstates_archive.py` — the function `run_single_archive_job()` calls —
has this as its own docstring's first line: **"Run run-archive.sh for one jurisdiction off the
event loop."** Not an inference from behavior, the function says what it does. And confirmed
your grep independently: zero matches for `cloud_archiver` anywhere in this `ddp-sync` checkout
(code, config, or docs). `openstates_root` on this host does resolve to `/opt/ddp-open-states`
(the `OPENSTATES_ROOT` env var in `docker-compose.prod.yml`, overriding the shared YAML's Mac
default per OPEN-243) — so on any host where this job actually ran, `run-archive.sh` would be a
real, present script, not a dead path.

## Live-logs claim: can't check from here

`openstates_archive` is disabled on *this* host — `docker logs` since the last rebuild shows only
`openstates_archive: disabled — skipping`, matching `OPENSTATES_ARCHIVE_ENABLED=false` in this
host's compose file (this box's mandate is the OPEN-193 scrape-trigger canary only, archive was
deliberately left off). So there's no live archive-job log here to compare against
`cloud_archiver.py`'s completion-record shape one way or the other. Whatever host actually runs
`openstates_archive` for real (sounds like the Mac Studio, per `sync_schedule.yaml`'s default
`openstates_root` pointing there) is where that check needs to happen — not something I can
settle from this box.

## Bottom line

The code says `run-archive.sh`, plainly, in its own docstring — I'd treat that as strong enough
to act on even without the live-log confirmation, but deferring to whoever can actually check
the host that runs it for the final word.
