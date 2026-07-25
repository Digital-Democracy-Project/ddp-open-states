# openstates-api Docker image still resolves unpatched OpenStates from PyPI (2026-07-21)

Found during a macOS Tahoe 26.5.2 / Xcode CLT 26.6 upgrade-safety audit (unrelated task) —
flagging because it's the same class of bug as the 2026-07-13 `os-people` pydantic break and
the local-patches gap already fixed for the host scraper toolchain venv (see
`notes/scraper-status-and-pydantic-break-20260713.md` and commit `214f97a`).

## Finding

The production `ddp-openstates-api-1` container (port 8002) is **not** built from this repo's
`openstates-core` fork. `deploy/docker-compose.ddp.yml:31` builds it from a sibling `../api-v3`
checkout instead (`dockerfile: ../deploy/Dockerfile.ddp`). `api-v3/pyproject.toml:10` declares
`openstates = "^6.7.0"`, and `api-v3/poetry.lock:1082` resolves that to **openstates 6.17.3
from PyPI** — a hashed wheel, not a path/git dependency on this fork.

Meanwhile the local fork (`openstates-core/pyproject.toml:3`) is at version **6.25.3** with
cherry-picked patches tracked in `apply-local-patches.sh`.

Net effect: the running API container has never executed any of the local-patches commits.
It's the same "silently running unpatched upstream" pattern as the pydantic/os-people
incident — just in the Docker API image instead of the host venv — and it was never touched
by the `214f97a` fix (that commit only edited `requirements-openstates.txt`, the host
toolchain venv's dependency file, not `api-v3`).

## Why this matters

Per the bill-provenance plan, VoteBot/DDP-API are meant to eventually cut over from the
upstream `v3.openstates.org` API to this local `openstates-api` container (`10.0.0.8:8002`).
Whenever that cutover happens, whatever's "fixed" in the local fork needs to actually be
running in the container it points to — right now it wouldn't be.

**Re-checked 2026-07-24/25, and this is less urgent than "Net effect" above makes it sound.**
`api-v3` only imports two things from the `openstates` package: `openstates.metadata.lookup`
(`api-v3/api/utils.py:3`) and `openstates.utils.transformers.fix_bill_id`
(`api-v3/api/bills.py:8`) — nothing else. None of DDP's current cherry-picked patches (motion
classification, the FL/VA/AZ scraper fixes, the `CACHE_DIR` env fix) touch either of those two
functions. So today, nothing is actually being silently missed — the drift is real but inert
against `api-v3`'s current, narrow usage surface. It becomes a live problem only if/when either
(a) a future patch actually touches `metadata.lookup` or `fix_bill_id` themselves, or (b)
`api-v3` starts importing more of the package (e.g. as part of the VoteBot/DDP-API cutover this
note already flags). Don't read "Net effect" above as "something is broken right now" — it
isn't; treat this as a drift risk to close before that cutover, not an active incident.

## Suggested fix (not yet applied)

Point `api-v3`'s dependency at the local fork instead of PyPI — e.g. a path or git dependency
in `api-v3/pyproject.toml`/`poetry.lock` targeting `openstates-core`, or have
`deploy/Dockerfile.ddp` install `openstates-core` via `pip install -e` from a mounted/copied
checkout — then rebuild `ddp-openstates-api-1` and confirm the patched commits are present
inside the running container (e.g. `docker exec ddp-openstates-api-1 pip show openstates`
should show the fork's version/patches, not `6.17.3` from PyPI).

**Open gap in this fix, not addressed above: how does `api-v3` stay current afterward?**
Pointing at the fork only fixes the version installed *at image-build time* — the host
toolchain venv had this exact same problem and it took an editable install (`pip install -e`)
plus a manually-maintained cherry-pick list to actually stay current, not just a one-time
version bump (see `notes/scraper-status-and-pydantic-break-20260713.md`). If `api-v3`'s image
does a one-shot `pip install` from a git ref, it drifts stale again the moment the fork moves,
with nothing forcing a rebuild — same failure mode as this note describes, one layer up. Needs
either a rebuild trigger tied to whatever refreshes the fork (see
`PLAN-fork-management.md`'s `apply-local-patches.sh` cadence), or an explicit decision that
`api-v3` gets manually rebuilt on its own schedule and that's an accepted tradeoff. Also worth
deciding, if this fix goes forward: point `api-v3` at `cherry-pick-line` (see
`PLAN-fork-management.md` recommendation H, added 2026-07-25) rather than a fixed commit/tag, for
the same "don't hand-list versions to track" reasoning that motivated that branch in the first
place.

## Evidence pointers

- `deploy/docker-compose.ddp.yml:30-34` — build context for `ddp-openstates-api-1` points at
  `../api-v3`, not `openstates-core`.
- `api-v3/pyproject.toml:10` — `openstates = "^6.7.0"`.
- `api-v3/poetry.lock:1082` — locked to `openstates 6.17.3`, PyPI source.
- `openstates-core/pyproject.toml:3` — local fork at `6.25.3`.
- `apply-local-patches.sh` — cherry-pick list for the local fork; none of this reaches `api-v3`.
