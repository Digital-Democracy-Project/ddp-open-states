# Please confirm/refute against real logs: cloud_archiver.py looks like it was never wired into ddp-sync at all

Found this from a dev-checkout code read, not from anything observed live on your end — please
verify against actual logs/behavior before we act on it, since it's a bigger claim than the
poppler-utils thing and I'd rather be wrong here than have you chase a phantom.

## What I found, reading code only

- `ddp-sync`'s `scheduler.py._register_openstates_archive_jobs()` schedules
  `run_single_archive_job()` (`openstates_archive.py`).
- That function shells out to **`run-archive.sh`** (`subprocess.run`, via
  `os.path.join(openstates_root, "run-archive.sh")`) — the pre-OPEN-192 wrapper script, not
  `cloud_archiver.py`.
- Grepped the entire `ddp-sync` repo (dev checkout) for `cloud_archiver`: **zero matches**,
  anywhere — not in `scheduler.py`, not in any pipeline file, not in config.
- `openstates_root` defaults to a Mac-shaped path (`/Users/agentsmith/Developer/repos/ddp-open-states`)
  but is overridden per-host via config -- on production this should resolve to wherever this
  host's own toolchain lives, which per earlier findings is the same bare `/opt/ddp-open-states`
  install missing `poppler-utils`.

## If this is right, it would mean

1. OPEN-192/238 (marked Done in Jira) built and tested `cloud_archiver.py`, but it was never
   actually connected to the live scheduler — the archive step still runs the old wrapper script
   this whole migration was supposed to replace.
2. It would fully explain the 2026-09-06 mystery from earlier (~39 US Congress bills landing in
   `DEEP_ARCHIVE` instead of `GLACIER_IR`) — that's `run-archive.sh`'s own default upload
   behavior, not a bug in the new direct-upload path, because the new path was never live.
3. It would mean the missing-`poppler-utils` problem isn't scoped to just the historical backfill
   investigation — every PDF-sourced document archived through the *live* pipeline while that
   binary was missing could have the same bad/empty-extraction problem, not just what's already
   flagged as stale.

## What would settle it either way

- Real archive job logs/output from a recent run (CAMS alert history, whatever `ddp-sync` itself
  logs for `openstates_archive_<jurisdiction>` job runs) -- does the log shape match
  `run-archive.sh`'s own output format, or `cloud_archiver.py`'s (its own completion-record
  shape, per its docstring, is deliberately NOT the same as `run-archive.sh`'s)?
- `ps`/process history during a live archive run, if you can catch one -- is it actually
  `run-archive.sh` (bash) in the process tree, or `python3 cloud_archiver.py`?
- Whatever `openstates_root` actually resolves to in this host's real deployed config (not the
  dev-checkout default) -- confirms whether the wrapper runs on the bare host or somewhere else.

No urgency beyond the poppler-utils/RDS re-run work already in flight -- this is a "confirm
before we treat it as real" check, not a new fire.
