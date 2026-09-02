# OPEN-248 fixed and pm-reviewed — the openstates toolchain is now bundled into ddp-sync's image

*Replies to `notes/open248-os-update-container-gap-filed-20260902.md`.*

Went with Option A, per Ramon's call. Built the openstates toolchain (Python 3.9 +
Django 3.2/pydantic 1.x + openstates-core/openstates-scrapers) INTO `ddp-sync`'s own image, in
its own builder stage, mirroring the same pattern the root `ddp-open-states` Dockerfile
already uses for the Fargate scraper image. `requirements-openstates.txt` is reached via a
BuildKit additional build context pointed at `/opt/ddp-open-states` (same path
`OPENSTATES_ROOT` already uses), not duplicated into `ddp-sync`'s own repo.

Confirmed **Django itself isn't the constraint** here (ddp-broker-py runs Django 5.0.3 on
Python 3.12 fine) -- it's specifically openstates-core's own frozen `Django==3.2.14` pin,
which predates Python 3.11's release. Upgrading that whole frozen dependency closure is a real,
separate migration project, explicitly out of scope for this fix.

Verified this thoroughly with actual local build+run testing (against this Mac's own sibling
`ddp-open-states-dev` checkout, standing in for `/opt/ddp-open-states`) rather than just
reasoning about it, and found + fixed two non-obvious bugs along the way:
- A venv's own convenience symlink (`bin/python3 -> /usr/local/bin/python3`) silently resolved
  through the FINAL image's own python3.11 install once copied cross-stage, since that generic
  name is already claimed there -- worse than a clean crash, it partially started under the
  wrong interpreter. Repointed at the unambiguous, version-specific binary.
- `libgdal` was missing -- Django eagerly loads it via ctypes for GIS-capable models,
  invisible to any Python-level dependency pin.

Sent through `/pm-review` per the standing practice now. Found two more real gaps, both fixed
and verified live:
- `docker-compose.prod.yml`'s `additional_contexts` alone doesn't supply the Dockerfile's
  BuildKit secret -- a real `docker compose build` would have failed at the git-clone step.
  Added compose-level `secrets.github_token` wiring; verified an actual `docker compose build
  ddp-sync` now succeeds end to end.
- `PYTHONPATH` was leaking into `ddp-sync`'s own app process, not just the `os-update`
  subprocess. Scoped it via a thin wrapper script instead.

Verified end to end: `os-update --help` runs cleanly from the final stage, and a real
`os-update ut --import` invocation gets all the way to attempting a real database connection
(correctly refused -- no local Postgres in this test environment) rather than failing anywhere
in the toolchain itself. `ddp-sync`'s own test suite: 1069 passed throughout.

**PR:** https://github.com/Digital-Democracy-Project/ddp-sync/pull/118 -- not merged yet.

Once it merges: pull, rebuild (this one needs a real image rebuild, not just a `git pull` --
the toolchain is baked in), restart, and re-attempt the FL canary. Every known blocker from
this entire thread (OPEN-241 through OPEN-248, plus the import-lock IAM grant) should finally
all be in place at the same time.
