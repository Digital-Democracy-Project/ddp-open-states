# ddp-open-states

Digital Democracy Project's local [OpenStates](https://openstates.org/) pipeline: runs the
OpenStates scraper toolchain against DDP's tracked jurisdictions, stores the results in a local
Postgres database, and serves them through a locally-run `api-v3` mirroring the public
`v3.openstates.org` API. DDP's production services still read from the public API — this
pipeline exists for validation against it and as a path toward eventual operational
independence.

## Layout

- **Repo root** — DDP-owned tooling: scrape/import orchestration, historical backfills, data
  quality checks against the public API, motion-classification tooling, and deploy assets for
  the local `api-v3` stack.
- Everything else (`openstates-scrapers/`, `openstates-core/`, `api-v3/`, `people/`, and a
  handful of other directories) is gitignored — upstream or DDP-fork checkouts, not tracked in
  this repo. See [`PRIMITIVES.md`](PRIMITIVES.md) for which is a DDP fork vs. a vendored
  upstream checkout, and how each receives patches.

## Quick start

```bash
source activate.sh                  # env vars + the dedicated OpenStates toolchain venv
./run-scrape.sh fl "session=2026"   # scrape + import one jurisdiction/session
```

> **This is the production checkout** — every scheduled scrape reads code directly from here,
> with no per-jurisdiction isolation. **Never edit files or switch branches here while a scrape
> is running** (`ps aux | grep run-scrape` first). For any code change or manual test, use the
> separate dev environment below instead.

## Development / testing

A fully isolated second checkout lives at `~/Developer/repos/ddp-open-states-dev` — its own
venv, its own Postgres database, safe to edit or run scrapes in regardless of what's running
here. See `RUNBOOK.md` → "Development / testing environment" for setup and usage; quick start:

```bash
cd ~/Developer/repos/ddp-open-states-dev
source activate-dev.sh              # NOT activate.sh — isolated paths, see RUNBOOK.md
os-update fl --scrape bills session=2026 --cachedir "$CACHE_DIR" --datadir "$SCRAPED_DATA_DIR"
```

## More detail

- [`PRIMITIVES.md`](PRIMITIVES.md) — catalog of this repo's scripts and conventions
  (resumability, logging, alerting, environment isolation). Read this before adding a new
  script — most needs already have an existing pattern to reuse.
- `RUNBOOK.md` — full operational reference (day-to-day commands, service topology, known
  gotchas). Not tracked in this repo; ask a DDP maintainer for access.
