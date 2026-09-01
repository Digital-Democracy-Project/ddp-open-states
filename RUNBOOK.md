# DDP Local OpenStates Runbook

Operational notes for running the local OpenStates scraper pipeline on the Mac Studio.
Architecture and planning decisions live in `PLAN-open-states.md` (this repo).

---

## What this is

A shadow pipeline that runs OpenStates scrapers locally and stores the results in a
local PostgreSQL database, served by the real OpenStates `api-v3` on port 8002.
Production services (ddp-broker-py, ddp-sync, votebot) still point at `v3.openstates.org`.
The local data is for validation and eventual cutover independence.

---

## Quick reference

```bash
# Set up environment
source activate.sh

# Run a scrape + import for one state
./run-scrape.sh fl "session=2026"
./run-scrape.sh mi                       # session auto-detected
./run-scrape.sh ut "session=2026"
./run-scrape.sh wa "session=2025-2026"
./run-scrape.sh usa "session=119 chamber=lower"   # US House
./run-scrape.sh usa "session=119 chamber=upper"   # US Senate
# Note: AL not tracked by DDP — omitted from nightly runs

# Run data quality check against live v3.openstates.org
OPENSTATES_API_KEY=<key> python3 quality_check.py
OPENSTATES_API_KEY=<key> python3 quality_check.py --jurisdiction ut --bills 10
OPENSTATES_API_KEY=<key> python3 quality_check.py --no-people

# Check api-v3 is up
curl -s "http://localhost:8002/jurisdictions/ocd-jurisdiction/country:us/state:fl/government?apikey=00000000-0000-0000-0000-000000000001" | python3 -m json.tool | head -5

# Check what's in the local DB (dedicated container; CAMS DB is ddp-agents-postgres-1 on :5432)
docker exec ddp-openstates-postgres-1 psql -U openstates -d openstates -c "
SELECT j.name, COUNT(DISTINCT b.id) AS bills, COUNT(DISTINCT ve.id) AS vote_events
FROM opencivicdata_jurisdiction j
JOIN opencivicdata_legislativesession ls ON ls.jurisdiction_id = j.id
JOIN opencivicdata_bill b ON b.legislative_session_id = ls.id
LEFT JOIN opencivicdata_voteevent ve ON ve.bill_id = b.id
GROUP BY j.name ORDER BY j.name;"
```

---

## Services

| Service | Port | Managed by | Startup |
|---|---|---|---|
| api-v3 | 8002 | container `restart:unless-stopped` + **system LaunchDaemon** one-shot `com.ddp.openstates-api` | `start-os-api.sh` → `docker-compose -f deploy/docker-compose.ddp.yml up -d` |
| openstates-postgres | 5433 | container `restart:unless-stopped` (same compose) | dedicated DB (volume `os_pg_data`) |
| db backup | — | **system LaunchDaemon** `com.ddp.openstates-db-backup` (07:00 local) | `backup-openstates-db.sh` (nightly pg_dump, keep-7) |
| Scraper | 8001 | ddp-sync APScheduler — **system LaunchDaemon** `com.ddp.ddp-sync` (not a GUI agent) | `run-scrape.sh` (per jurisdiction) |
| Staleness watchdog | — | **system LaunchDaemon** `com.ddp.health-monitor` (ddp-agents, every 5 min) — **live, see below** | `check-scrape-staleness.sh` via one-line hook in `ddp-agents/deployment/scripts/health-check-slack.sh` |

**api-v3 deployment (containerized 2026-06-24, per `PLAN-production-hardening.md`):** api-v3
runs as the `ddp-openstates` Docker compose project — container `ddp-openstates-api-1` on
:8002 against its own dedicated Postgres `ddp-openstates-postgres-1` on :5433 (Redis still
shared via `ddp-agents-redis-1`). **Deploy files live in `deploy/`** (DDP-owned), not in the
public `api-v3/` checkout: `deploy/docker-compose.ddp.yml` (build context → `../api-v3`),
`deploy/Dockerfile.ddp` (upstream Dockerfile + `psycopg2-binary==2.9.9` for Postgres-16 SCRAM
on arm64), `deploy/docker-compose.stopgap.yml` (rollback). Pinned pydantic 1.10.2. Use the
`docker-compose` (hyphen) binary — this host has no `docker compose` plugin.

> **Rebuild note:** build context (`../api-v3`) is now ~0.5 MB after removing the stray
> `_cache`/`_data` from that checkout, so rebuilds are fast. Caveat: this host's classic
> builder reads `.dockerignore` only from the context root, so `deploy/Dockerfile.ddp.dockerignore`
> isn't honored — if `_cache`/`_data` ever reaccumulate in `api-v3/` (they shouldn't:
> `activate.sh` points the scrapers at `openstates-scrapers/`), the context will bloat again.
> Fix then = `brew install docker-buildx` (honors the `deploy/` ignore) or just delete the stray dirs.

**`com.ddp.openstates-api` and `com.ddp.openstates-db-backup` are system LaunchDaemons**
(`/Library/LaunchDaemons/`), migrated 2026-07-17 from GUI LaunchAgents as Phase 2 of
`PLAN-cams-hardening-isolation.md` (`ddp-agents` repo, PR #20 + hotfix #21 + follow-up #22) —
same rationale as the `ddp-sync` migration below (GUI agents don't reload over SSH). Installed
via `sudo cams install-daemons` (the `ddp-agents` `cams` CLI), not a bare `launchctl
bootstrap`. As part of the same change, `start-os-api.sh` was hardened for the boot-order race
this creates: as a system daemon, it can start **before** CAMS creates `ddp-agents_default` /
`ddp-agents-redis-1`, so it reaches Docker via the Colima socket directly (`DOCKER_HOST`) and
bounded-waits (5s × 60 = 300s) for the network and Redis instead of fail-fast-exiting;
`KeepAlive={SuccessfulExit:false}` + `ThrottleInterval=30` relaunches it until CAMS is up.

Scrape scheduling moved to ddp-sync on 2026-06-22. The old `com.ddp.openstates-scraper`
launchd job has been removed (plist deleted 2026-06-24). Jobs are now independent per jurisdiction — FL, WA, and USA run
in parallel; secondary states fan out concurrently on Sundays. See `ddp-sync/config/sync_schedule.yaml`
under the `openstates_scrape` block for the full schedule.

**Schedule times are UTC** (`sync_time_utc`): FL 02:00, WA 02:30, USA 03:00, patch refresh 01:00.
WA/USA/patch run daily; **FL is weekly (Sundays only) while out of session** — `primary.fl.sync_day: sunday`,
added 2026-07-16 (`aae1ff4`) since FL has no new draft bills until the 2027 session (remove `sync_day`
to restore daily). So FL fires Sunday 02:00 UTC = **Sat 22:00 EDT**. Secondary states + people refresh Sundays.
Fixed 2026-06-24 — APScheduler had been
interpreting the times as local EDT (firing ~4h late); the openstates triggers now pin UTC.
Verify the live schedule: `curl -s http://localhost:8001/ddp-sync/v1/schedule` (times show `+00:00`).

**The local ddp-sync is a system LaunchDaemon** (`/Library/LaunchDaemons/com.ddp.ddp-sync.plist`,
source in `ddp-sync/infrastructure/com.ddp.ddp-sync.plist`), migrated 2026-07-08 from the old GUI
LaunchAgent. This Mac is administered SSH-only with no reliable Aqua session, so `gui/$(id -u)`
agents can't be reloaded remotely — `bootstrap gui/502` fails `125` even as root once the domain
wedges (that's what took scrapes down 2026-07-04→08 after a `:8001` port-conflict boot-out).
Restart/inspect from an **admin account**: `sudo launchctl kickstart -k system/com.ddp.ddp-sync`;
full recovery + reinstall steps in `ddp-infra/README.md` → "Restart Procedures". See also the
GUI-agent migration note: `project_gui_agent_migration.md`.

```bash
# Restart api-v3 (container)
docker restart ddp-openstates-api-1
# Full stack up/down (api + dedicated postgres)
cd deploy && docker-compose -f docker-compose.ddp.yml up -d
cd deploy && docker-compose -f docker-compose.ddp.yml restart api

# Rollback to the pinned stopgap container (points at the old CAMS DB on :5432)
cd deploy && docker-compose -f docker-compose.ddp.yml down
cd deploy && docker-compose -f docker-compose.stopgap.yml up -d

# Manually trigger a scrape for any jurisdiction via ddp-sync HTTP API
curl -X POST http://localhost:8001/ddp-sync/v1/trigger/openstates-scrape/wa \
  -H "X-API-Key: <ddp-sync-api-key>"

# Trigger targets: patches | fl | wa | usa | secondary | people | va | mi | ma | ut | az

# Run a scrape directly (bypasses ddp-sync scheduling, patches applied normally)
./run-scrape.sh wa
./run-scrape.sh fl "session=2026"

# Refresh people data manually
./run-people-refresh.sh

# Tail scraper log
tail -f logs/scraper.log

# Tail api-v3 log
tail -f logs/os-api.log
```

---

## Scraper staleness watchdog (`check-scrape-staleness.sh`, OPEN-40)

Detects jurisdictions that **silently stop scraping** — the failure mode every in-run alert
path (`run-scrape.sh`'s `ERR` trap / `on_failure`) can't see, and how MA ran wrong for six
weeks unnoticed. It compares the age of each watched `logs/last-run/<key>.ts` marker against
that job's cadence, alerts with the evidence needed to act on it, and escalates at 2× and 4×
threshold rather than going silent (OPEN-130).

**Status: live.** The companion hook in `ddp-agents/deployment/scripts/health-check-slack.sh`
merged and reached production the same day (2026-08-08), and this script itself landed in the
production checkout shortly after ([ddp-open-states#98](https://github.com/Digital-Democracy-Project/ddp-open-states/pull/98)).
Confirmed actually running, not just deployed: `logs/staleness-check.log` shows a real first-run
alert (`STALE: mi last-run age 333h exceeds 228h threshold — alerting`, 2026-08-08 19:57:29 —
the expected MI true-positive called out when this was built), and the matching
`logs/last-run/mi.stale-alerted` sentinel exists, root-owned (written by the LaunchDaemon).

**How it runs:** the existing `com.ddp.health-monitor` system LaunchDaemon
(ddp-agents) calls it every 5 minutes via a one-line `bash …/check-scrape-staleness.sh || true`
hook in `ddp-agents/deployment/scripts/health-check-slack.sh`. That placement is deliberate — the
watchdog lives **outside** ddp-sync and the scrape scripts, so it still fires when the
scheduler daemon itself is dead (which happened 2026-07-04→08 with zero alerts). The `|| true`
means a watchdog bug can never break CAMS/os-api monitoring. Note: the §11.3 design originally
said to append this to `run-all-scrapes.sh` under `com.ddp.openstates-scraper` — that launchd
job was deleted 2026-06-24, and a watchdog inside the pipeline can't see "the pipeline never
started" anyway; the canonical `ddp-infra/PLAN-open-states.md` §11.3 records the correction.

**Watched keys and thresholds** (hardcoded allowlist in the script — backfill markers like
`fl_session_2023`…`2025C` / `usa_session_118_*` must never be watched, so no globbing):

| Threshold | Keys | Basis |
|---|---|---|
| 48h | `wa`, `usa_session_119_chamber_lower`, `usa_session_119_chamber_upper` | daily jobs |
| 228h | `fl_session_2026`, `fl_session_2026D`, `fl_session_2026E`, `fl_session_2026F` | **weekly while `primary.fl.sync_day: sunday`** (out-of-session since 2026-07-16) — move to 48h when FL reverts to daily for the 2027 session |
| 228h | `va`, `mi`, `ut`, `az`, `ma` | Sunday secondaries. Bare `ma`, not `ma_session_194th` — ddp-sync passes no session arg (OPEN-24), so the live marker is `ma.ts` |

A **missing** `.ts` marker is treated as maximally stale (alerts, never skips). This map is
the thing to update when the ddp-sync schedule changes — keep it in sync with
`ddp-sync/config/sync_schedule.yaml`.

**Alert lifecycle:** first detection posts to Slack `#automation-errors` **and** CAMS
`/api/v1/failures` (`error_type=ScrapeStalenessDetected`, so it reaches Agent Smith triage),
then writes a `logs/last-run/<key>.stale-alerted` sentinel recording the escalation tier —
subsequent 5-minute runs at the same tier stay silent. When the marker freshens, the sentinel
is removed and a recovery message posts. Sentinels are written by the root-owned daemon so they
land root-owned; `logs/last-run/` is agentsmith-owned, so `rm` still works without sudo.

**Escalation tiers (OPEN-130).** The one-alert-per-episode version fired at the moment the
condition looked *least* serious — `az last run 229h, threshold 228h` reads as a rounding
error — and then went correctly silent while az grew to 14 days. All three staleness alerts
ever sent were declined by CodeBot triage as "not a code bug", the designed response to a
one-line signal indistinguishable from a scraper legitimately quiet out of session. So now:

* Each alert **carries its own evidence**: staleness in days, the absolute last-success
  timestamp, the count of **missed scheduled runs** (derived from the key's threshold — 48h ⇒
  daily, 228h ⇒ weekly), and the multiple of threshold. The CAMS payload puts that block in
  `stacktrace` (previously `(none provided)` in triage) plus `severity_hint` and
  `escalation_tier`/`scheduled_runs_missed` metadata. No ddp-agents change was needed — those
  fields were always accepted.
* It **re-alerts at 2× and 4× threshold** with wording that says it is the same episode
  growing, not a new outage. Between tiers, and above 4×, it stays silent. The wording (not
  just the numbers) differs per tier on purpose: CAMS fingerprints failures with digits
  normalized to `<n>`, so tiers differing only numerically would de-dupe into one signal.
* The missed-run count is the load-bearing fact for triage, because `run-scrape.sh`'s
  `finish_no_op()` stamps `<key>.ts` even on a zero-bill run — an out-of-session jurisdiction
  still refreshes its marker, so a stale marker means the scheduled job is not completing.
* A **missing** marker is recorded at the top tier: "never" cannot grow, so it fires once.
* A **malformed** `tier=` value (typo in the hand-silence recipe below, truncated write) logs a
  warning and is treated as un-alerted, so the run alerts and rewrites the sentinel — silence
  is never the failure mode.

**Know the remaining gap.** On a weekly job the threshold is 228h, so 2× is ~19 days: the
az incident that motivated this (14 days stale) would *still* have received only one alert.
What changed is that the one alert now reads "no successful scrape in 9 days … 1 scheduled
weekly run missed", not "229h vs 228h". Moving that second signal earlier means moving the
threshold, which is a separate decision — file it against the watchlist, not the tiers.

```bash
# See current staleness state (who has alerted, when, and at which tier)
ls -la logs/last-run/*.stale-alerted 2>/dev/null; cat logs/last-run/*.stale-alerted 2>/dev/null

# Watchdog's own activity log (quiet runs log nothing)
tail logs/staleness-check.log

# Silence a known/expected staleness episode without fixing it yet.
# tier=4 is the top tier, so this suppresses escalations too; a bare-timestamp
# sentinel (the pre-OPEN-130 recipe) only suppresses up to 2x. Remove it to re-arm.
printf 'tier=4\n' > logs/last-run/<key>.stale-alerted

# Run the fixture tests (no network, no production paths)
bash test-check-scrape-staleness.sh
```

Alert copies the `run-scrape.sh` Slack/CAMS pattern (fifth copy in this repo — extraction
tracked as OPEN-43; this script may deliberately stay a copy since monitoring shouldn't share
code with what it monitors).

---

## Database

**Host:** `localhost:5433` — **dedicated** container `ddp-openstates-postgres-1` (postgres:16-alpine, volume `os_pg_data`), as of 2026-06-24.
**Database:** `openstates`
**User/password:** `openstates` / `openstates_dev`
**API key for local api-v3:** `00000000-0000-0000-0000-000000000001` (UUID format, stored in `profiles_profile` table)
**Backups:** nightly `pg_dump` to `logs/db-backups/` (keep-7) via `backup-openstates-db.sh`. Off-host S3 copy is wired-but-disabled in that script, pending AWS creds (WS9). Restore: `docker exec -i ddp-openstates-postgres-1 pg_restore -U openstates -d openstates --clean --no-owner < <dump>`.

> **Migration note:** the openstates DB used to live inside CAMS's `ddp-agents-postgres-1`
> (:5432). It was dump/restored into the dedicated container above. **The old copy is
> intentionally retained on :5432 as a rollback target** until a soak period passes — do not
> drop it until a repo-wide `grep -rn "5432/openstates" ~/Developer/repos` is clean. This is
> also gated on the FL historical backfill (2023/2024 regular sessions still landing as of
> 2026-07-21) finishing first, since those scrapes still write through the same
> `activate.sh`/`quality_check.py` pointers the consumer check inspects.

The real OpenStates API key (for `v3.openstates.org`) is in `ddp-broker-py/.env`.

---

## Environment

Always `source activate.sh` before running scrapers or CLI commands manually. It sets:

- `DATABASE_URL` — local openstates DB (now `localhost:5433`, the dedicated container)
- `OS_PEOPLE_DIRECTORY` — path to people YAML repo
- `PYTHONPATH` — scrapers directory (required for `os-update` module resolution)
- `SCRAPED_DATA_DIR` — where scraped JSON lands before import
- `PATH` — prepends the toolchain venv `.venv/bin` (see below)
- `OS_UPDATE`, `OS_PEOPLE`, `OS_INITDB` — CLI paths (now `.venv/bin/`, the dedicated toolchain venv)

### OpenStates toolchain venv (isolated 2026-07-15)

The `os-*` CLIs run from a **dedicated virtualenv** at `.venv/` (Python 3.9.6), not the shared
user site-packages. This isolates `openstates-core`'s hard `pydantic<2` pin from other services:
the toolchain previously shared `~/Library/Python/3.9`, and a FastAPI install for another service
(Jun 2026) pulled pydantic 2.x, which crashed `os-people`/`os-update` at import time
(`@root_validator ... must specify skip_on_failure=True`). Full writeup:
`notes/scraper-status-and-pydantic-break-20260713.md`.

`activate.sh` prepends `.venv/bin` to `PATH` and points `OS_UPDATE`/`OS_PEOPLE`/`OS_INITDB` at it;
`run-scrape.sh` and `run-people-refresh.sh` (both driven by ddp-sync's scheduler) inherit it. The
old `~/Library/Python/3.9/bin/os-*` copy still runs as a fallback, but nothing scheduled uses it.

> **Corrected 2026-07-19 — `openstates` had drifted to a pinned PyPI release, not the local
> checkout.** From venv creation (2026-07-15) until this was caught, `requirements-openstates.txt`
> pinned `openstates==6.25.2` directly, so the venv installed upstream's unpatched release —
> **every commit on `local-patches` since then (and further back — this had likely regressed
> earlier too) had zero effect on the running scrapers.** `open-states-scrapers` was unaffected —
> it's loaded via `PYTHONPATH` straight from its checkout, no install step involved, confirmed
> still working correctly. Fixed below: `openstates` now installs in **editable** mode from the
> local `openstates-core` checkout, matching how `apply-local-patches.sh` was already written to
> assume this worked (its "installed as a pip editable package" comment was accurate in intent,
> just not in fact, until now).

**Rebuild** (e.g. after a wipe) from the pinned dependency closure in `requirements-openstates.txt`,
then install `openstates` itself in editable mode from the local checkout:

```bash
/usr/bin/python3 -m venv .venv                       # Xcode Python 3.9.6
.venv/bin/pip install 'pip<24.1'                     # newer pip rejects textract 1.6.5's metadata
.venv/bin/pip install --no-deps -r requirements-openstates.txt
.venv/bin/pip install --no-deps -e openstates-core   # editable — local-patches takes effect immediately,
                                                      # no reinstall needed after future patch changes
# verify:
.venv/bin/python -c "import openstates; print(openstates.__file__)"   # must point at openstates-core/, not site-packages
.venv/bin/python -c "import openstates.models"        # must not raise
source activate.sh && $OS_PEOPLE to-database az       # end-to-end
```

- **`pip<24.1` is required** — pip ≥24.1 refuses `textract==1.6.5` ("invalid metadata").
- `--no-deps` (both installs) installs exactly the pinned closure plus `openstates` itself, nothing
  more — `requirements-openstates.txt` is the frozen working set **minus the pydantic-v2 forcers**
  (`fastapi`, `pydantic-core`, `prometheus-fastapi-instrumentator`) **and minus `openstates` itself**
  (installed separately, editable, so it stays live).
- Because it's editable, `apply-local-patches.sh` pulling a fresh `main` (git-only, no pip step)
  is sufficient going forward — no need to re-run `pip install` after every patch change.

> **Do NOT `pip install` FastAPI or any pydantic-v2 package into this venv** — that reintroduces the
> exact conflict the venv exists to prevent. api-v3 (the only FastAPI service here) runs in Docker and
> does not use this venv.

**Playwright browser binaries (added 2026-08-01, OPEN-19)** — MI's WAF-cookie warm-up
(`openstates.utils.mi_cookies.MI_COOKIE_PROVIDER`, wired into `scrapers/mi/*.py` and
`os-text-extract archive mi`) launches a real Chromium via Playwright the first time it needs to
warm up a cookie jar (cache miss, expiry, or a detected block). `pip install`ing the `playwright`
package from `requirements-openstates.txt` only installs the Python bindings — the actual browser
binary is a separate one-time step, required once per venv:

```bash
.venv/bin/playwright install chromium
```

Skipping this doesn't break anything until the cache is actually empty/expired/invalidated — a
scrape can look fine for weeks (reusing the cached `x-bni-fpc`/`x-bni-rncf` cookies) and then fail
the moment a re-warm is actually needed, so run this as part of every venv rebuild above, not just
if/when MI scraping breaks.

---

## Development / testing environment (`ddp-open-states-dev`)

**Never edit code or switch branches directly in this checkout while a scrape is running anywhere**
(`ps aux | grep run-scrape`, or check `/tmp/ddp-openstates-scrapes/` for live PID markers). There's
exactly one production checkout of `openstates-core`/`openstates-scrapers`, shared by every
jurisdiction's scrape — no per-jurisdiction isolation, and `apply-local-patches.sh`'s worktree lock
only guards against a full patch *rebuild*, not a direct file edit. Found the hard way 2026-07-24:
editing `run-scrape.sh` while an 11+ hour FL backfill was actively executing that exact file risked
corrupting it (bash reads running scripts incrementally from disk — caught and reverted in time, no
actual damage, but it was a close call, not a safe-by-design system).

**The fix: a fully separate checkout at `~/Developer/repos/ddp-open-states-dev`.** Same repo,
same nested `openstates-core`/`openstates-scrapers`/`people` structure, but its own venv and its
own Postgres database — completely isolated from production, safe to edit/test at any time
regardless of what's running in this repo.

```bash
cd ~/Developer/repos/ddp-open-states-dev
source activate-dev.sh          # NOT activate.sh — sets isolated paths, see below
os-update fl --scrape bills session=2026F --cachedir "$CACHE_DIR" --datadir "$SCRAPED_DATA_DIR"
os-update fl --import --cachedir "$CACHE_DIR" --datadir "$SCRAPED_DATA_DIR"
os-text-extract archive fl      # Phase 1 bill-document archiving, PLAN-bill-document-provenance.md
```

What `activate-dev.sh` isolates, all under the dev checkout, never touching production paths or
`/Volumes/DDP-HOT`:

| Var | Dev value |
|---|---|
| `DATABASE_URL` | `openstates_dev` database — **same Postgres container** as production (`:5433`), different DB name, so no second container is needed for full data isolation |
| `CACHE_DIR` / `SCRAPED_DATA_DIR` | `ddp-open-states-dev/openstates-scrapers/_cache` / `_data` |
| `ARCHIVE_ROOT_DIR` | `ddp-open-states-dev/_archive_scratch` — a scratch dir, not the real archive |
| `OS_VENV` / `PATH` / `OS_*` | the dev checkout's own `.venv` |

**Not wired into any scheduler** — no launchd plist, no `ddp-sync` job. Purely for manual/
interactive use. **Corrected 2026-07-29 — stale since 2026-07-25:** this used to say `openstates-core`
in this checkout "currently sits on the `phase1-bill-provenance` branch." That branch was deleted
everywhere the same day the archive feature (Phase 1/2 of `ddp-infra/PLAN-bill-document-provenance.md`)
merged to production `main` via `cherry-pick-line` — the feature no longer needs a dedicated branch
to test, since it's live on `main` like everything else. This checkout has since become the general
`ddp-open-states` working checkout for ongoing engineering (per its own `CLAUDE.md`'s
PR-before-production rule), not a narrow Phase-1-only sandbox — check `git branch --show-current`
in each nested repo before assuming what's checked out; don't rely on this doc naming a specific
branch, since whatever's here will drift again the moment someone switches it for other work.

**Rebuilding the dev venv from scratch:** follow the same recipe as the production venv above
(`python3 -m venv .venv && pip install 'pip<24.1' && pip install --no-deps -r requirements-openstates.txt`),
but expect `pip install --no-deps -e openstates-core` to fail on this pip/setuptools combination —
the build subprocess can't see `setuptools` even though it's installed (`--no-build-isolation` just
trades it for a missing-`poetry` error instead). Worked around 2026-07-24 by hand-creating what a
successful editable install would have produced:

```bash
# Editable-install marker (adds openstates-core/ to the venv's import path):
echo "$PWD/openstates-core" > .venv/lib/python3.9/site-packages/openstates.pth

# Console-script wrappers -- one per [tool.poetry.scripts] entry in openstates-core/pyproject.toml
# (os-update, os-initdb, os-text-extract, os-people, os-committees, os-scrape, os-validate,
# os-relationships, os-update-computed, os-dbmakemigrations, os-us-to-yaml, os-people-repo-update).
# Each is a 7-line file -- copy the exact template from production's .venv/bin/os-update
# (production's install succeeded when the venv was first built, so its wrappers are the reference).
```

### `os-text-extract refresh-extraction` — retroactive re-extraction after an extractor fix

Neither `reextract` (filters to `is_error=True`) nor `recompute_diff_order` (recomputes from
already-stored `raw_text`) can make an extractor bug fix retroactive — the documents an extractor
fix targets typically extracted "successfully," just badly, so `reextract` skips them, and
`recompute_diff_order` would just recompute diffs from the same bad text. `refresh-extraction`
exists for exactly this: it walks bill by bill, re-extracts every document whose current extractor
output differs from what's stored, and only then recomputes that bill's diffs (order matters —
recomputing while any version still holds stale text reproduces the problem for that hop). Dry-run
by default (`--commit` to write), idempotent, reads only from the local archive (no re-fetching).

```bash
os-text-extract refresh-extraction ut              # dry run — reports counts, changes nothing
os-text-extract refresh-extraction ut --commit      # the real backfill
os-text-extract refresh-extraction all -n 50        # limit to 50 bills, for testing
```

**Run for real against production 2026-08-29** (OPEN-210/211/212, after the XML/WA-HTML
structure-aware extraction fix): Utah (1,021 bills / 3,100 documents), Washington (3,411 / 5,818),
United States (37,672 / 44,723) — zero documents refused in any of the three. One residual, recorded
rather than chased: 5 US documents (4 bills) have a `sha256_hash` from archive time but no
`archive_location`, so there is nothing local to re-extract from — verify directly in Postgres
(`select count(*) from ddp_bill_version_document where media_type in ('text/xml','text/html') and
not is_error and raw_text != '' and position(chr(10) in raw_text) = 0`) rather than trusting the
command's own summary line, which is exactly how that residual was caught.

Verify the same way as production: `.venv/bin/python -c "import openstates; print(openstates.__file__)"`
must point at the dev checkout's `openstates-core/`, not `site-packages`.

**Initializing the dev database** (only needed once, or after a wipe):

```bash
docker exec ddp-openstates-postgres-1 psql -U openstates -d openstates \
  -c "CREATE DATABASE openstates_dev OWNER openstates;"
source activate-dev.sh && os-initdb
```

---

## Scraper state

Scrapers run from `Digital-Democracy-Project/openstates-scrapers` fork `main` (formal org fork
as of 2026-07-03). `apply-local-patches.sh` no longer touches the scrapers — fork `main` IS the
patched state.

**Day-to-day workflow:**
- New fix: `git checkout -b feat/my-change` → PR to fork `main`
- Upstream sync (monthly): `git fetch upstream && git merge upstream/main && git push origin main`
- Upstream contribution: branch off `upstream/main`, cherry-pick the commit, PR to `openstates/openstates-scrapers`

### DDP commits on fork main (newest first)

| SHA | Description | Upstream target |
|---|---|---|
| `PR #8` | fix: pass House bioguide / Senate lis_id through as a resolvable vote identifier ([PR #8](https://github.com/Digital-Democracy-Project/openstates-scrapers/pull/8), **merged 2026-07-26**). Companion to `openstates-core` PR #2 and `ddp-open-states` PR #12 — fixes OPEN-2 (VoteBot's inflated "Unknown/Other" vote-party bucket) | upstream PR candidate |
| `PR #7` | fix(fl): scrape bills incrementally instead of batching the whole session ([PR #7](https://github.com/Digital-Democracy-Project/openstates-scrapers/pull/7), merged 2026-07-25) | upstream PR candidate |
| `PR #6` | fix(fl): don't crash the scrape when a vote's tally can't reconcile ([PR #6](https://github.com/Digital-Democracy-Project/openstates-scrapers/pull/6), merged 2026-07-23) | upstream PR candidate |
| `PR #5` | fix(fl): refresh flhouse.gov WAF session so long scrapes keep collecting House votes (branch `fix/fl-house-waf-session-refresh`, [PR #5](https://github.com/Digital-Democracy-Project/openstates-scrapers/pull/5), **merged 2026-07-18**). Supersedes the crash-avoidance in `565804c` — see "Florida House votes vanish on long scrapes" below | **upstream PR opened 2026-08-05** ([openstates/openstates-scrapers#5751](https://github.com/openstates/openstates-scrapers/pull/5751), OPEN-27) |
| `PR #4` | fix(va): skip not-yet-started sessions in `get_session_list` ([PR #4](https://github.com/Digital-Democracy-Project/openstates-scrapers/pull/4), merged 2026-07-13) | upstream PR candidate |
| `PR #3` | fix(va): guard `add_versions` against non-dict API responses ([PR #3](https://github.com/Digital-Democracy-Project/openstates-scrapers/pull/3), merged 2026-07-13) | upstream PR candidate |
| `PR #2` | fix(az): don't emit `VoteEvent`s for actions with no recorded vote ([PR #2](https://github.com/Digital-Democracy-Project/openstates-scrapers/pull/2), merged 2026-07-11) | upstream PR candidate |
| `PR #1` | feat(mi,wa): emit roll-call number into vote extras ([PR #1](https://github.com/Digital-Democracy-Project/openstates-scrapers/pull/1), merged 2026-07-11) | upstream PR candidate |
| `44db0a7` | fix(fl): don't crash the whole scrape on a doubled "final action:" PDF line (`UpperComVote`, `bills.py:614` — `re.split` → 2-tuple unpack `ValueError`; inherited upstream). Killed the FL 2023 historical backfill | upstream PR candidate |
| `807fa57` | fix(classifier): correct motion classification bugs across UT, VA, MI, FL, WA | Phase 3A |
| `65363ef` | fix(va): deduplicate bills from LIS API response | Phase 3A |
| `b7dfd2b` | feat: YAML-driven motion passage classification (all 8 jurs) | Phase 3A |
| `e6dce3c` | feat(ma): re-enable house and senate vote scraping | Phase 3A |
| `50422a9` | feat(va): add start= incremental filtering | Phase 3B |
| `58f006f` | feat(az): add start= incremental filtering | Phase 3B |
| `c211b35` | feat(ma): add start= incremental filtering | Phase 3B |
| `2c1d7a0` | feat(ut): add start= incremental filtering | Phase 3B |
| `8db6514` | feat(mi): add start= incremental filtering | Phase 3B |
| `5d6644b` | feat(wa): add start= incremental filtering | Phase 3B |
| `3295ea4` | feat(fl): add start= incremental filtering | Phase 3B |
| `6d5ce6d` | fix(usa): correct start= datetime format string | Phase 3B |
| `565804c` | FL: don't let flhouse.gov bot detection crash the scrape (crash-avoidance only — never recovered House votes; superseded by PR #5) | Phase 3A |

### `apply-local-patches.sh` (openstates-core and openstates-scrapers)

Run periodically (ddp-sync's nightly `openstates_patch_refresh` job) or whenever someone's
already touching either repo. Both repos are now formal forks — a plain `git checkout main &&
git pull origin main`, same as any other fork. The scrapers block moved to this model in
`8cca7a2` (2026-07-03); core followed 2026-08-01 (below).

**openstates-core retired the cherry-pick-line model 2026-08-01** (`PLAN-fork-management.md`
§6, "drop the cherry-pick-line model entirely and just become a clean fork like
openstates-scrapers"). From 2026-07-25 to 2026-08-01, DDP-only commits for `openstates-core`
landed on a standing `cherry-pick-line` branch, range-picked onto a freshly rebuilt
`local-patches` branch on every refresh — the editable install actually imported
`local-patches`, never `main` directly. Retired because upkeep cost kept exceeding the "cheap,
one commit" premise that justified it: a frozen local ref silently missed two merged PRs
(2026-07-27), `git cherry-pick` crashed on an ordinary merge commit (2026-07-27), and a PR
merged to the wrong base branch went unnoticed until the next rebuild (2026-07-26, see
`notes/openstates-core-cherry-pick-line-targeting-20260726.md` for that incident specifically —
kept for historical record; the targeting gotcha it describes no longer applies now that both
repos use the same plain-fork convention). The last three DDP fixes (core PRs #3, #5, #6) had
already started merging straight to fork `main` in practice, ahead of the docs catching up.

**Remote convention, now identical for both repos:** `origin` = the DDP fork
(`Digital-Democracy-Project/openstates-{core,scrapers}`), `upstream` = the real project
(`openstates/openstates-{core,scrapers}`). `openstates-core`'s remotes were renamed to match
2026-08-01 (previously `origin` = upstream, `ddp` = fork — the opposite of `openstates-scrapers`'
existing convention, itself a minor contributor to the wrong-branch-targeting confusion above).

**Historical: fixes merged via the retired `cherry-pick-line` route** (kept for record; already
part of fork `main` since 2026-08-01, no action needed):

| PR | Description | Status |
|---|---|---|
| [core PR #1](https://github.com/Digital-Democracy-Project/openstates-core/pull/1) | fix(archive): match FL scraper's retry settings for the document downloader | merged 2026-07-26 |
| [core PR #2](https://github.com/Digital-Democracy-Project/openstates-core/pull/2) | fix: resolve vote records by bioguide/lis identifier before falling back to name match (OPEN-2, companion to scrapers PR #8 / ddp-open-states PR #12) | merged 2026-07-26 (retargeted from `main` to `cherry-pick-line` before merge) |
| [core PR #3](https://github.com/Digital-Democracy-Project/openstates-core/pull/3) | fix(archive): detect bot-block/CAPTCHA pages before archiving them as real documents | merged 2026-07-28, direct to fork `main` |
| [core PR #6](https://github.com/Digital-Democracy-Project/openstates-core/pull/6) | OPEN-19: Barracuda-cookie-reuse fetcher for Michigan WAF bypass | merged 2026-08-01, direct to fork `main` |

### Upstream issues

| Issue | State | Description |
|---|---|---|
| #5697 | MI, FL, VA | Pagination overlap / API duplicates → `--allow_duplicates` on import for all three in `run-scrape.sh`; VA scraper-side dedup also added in `65363ef` |

### Recently merged upstream

| PR | Merged | What it fixed |
|---|---|---|
| #5696 | 2026-06-15 | MI House votes: regex mismatch + tab-separated names |
| #5695 | 2026-06-16 | UT 2025+ votes: `yield from` fix, XPath fix, duplicate vote identifier fix |

**On #5695 and OPEN-67 (added 2026-08-13):** this PR fixes a *missing-votes* bug (2025+
API-rendered UT bills emitted zero votes before the `yield from` fix) -- it is **not** confirmed
to be, and structurally could not have been, the fix for the separate House/Senate
chamber-assignment swap OPEN-67 investigated (2026-03-05–2026-04-26, `ddp-broker-py`'s dev DB).
The dead code this PR fixed produced no votes at all before it merged, so it can't have produced
wrong-chamber ones either. Full git archaeology across `openstates-scrapers` and
`openstates-core` found no reversed-then-fixed chamber mapping anywhere in either repo's history
for this window -- see `notes/open-67-utah-chamber-swap-investigation-20260813.md`. Don't cite
this PR as the chamber-swap fix without reading that note first.

---

## Incremental scraping

After each successful import, `run-scrape.sh` writes a UTC timestamp to
`logs/last-run/<key>.ts`. On the next run it reads this file, subtracts 1 hour
as a safety overlap, and passes `start=<timestamp>` to `os-update`. Each scraper
skips bills whose last-action date is ≤ the cutoff.

### Timestamp files

```
logs/last-run/
  fl_session_2026.ts          # last successful FL 2026 regular import
  fl_session_2026D.ts         # FL 2026D special
  fl_session_2026E.ts
  fl_session_2026F.ts
  wa.ts
  usa_session_119_chamber_lower.ts
  usa_session_119_chamber_upper.ts
  va.ts  mi.ts  ut.ts  az.ts  # secondary states (weekly Sunday)
  ma_session_194th.ts         # MA (session-keyed; backfilled 2026-07-03)
  # va.ts now present (as of 2026-07-18) — the 2026-06-29 DuplicateItemError on HB 1054 that
  #   kept VA on full-scrape-only is resolved (scraper-side dedup added 65363ef); incremental
  #   mode is live for VA like every other jurisdiction.
  # .count files store bill counts for anomaly detection (see below)
  fl_session_2026.count
  ...
```

### Force a full scrape

Delete the `.ts` file for that jurisdiction:

```bash
rm logs/last-run/fl_session_2026.ts
./run-scrape.sh fl "session=2026"    # will run full, then write a new timestamp
```

### Backfilling historical (non-scheduled) sessions

`ddp-sync`'s schedule (`ddp-sync/config/sync_schedule.yaml`) only tracks the **current**
session per jurisdiction, so the replica normally holds current-session bills only. When
the broker needs older sessions (e.g. cross-jurisdiction legislators' prior terms), scrape
them manually — one full scrape per session, no `.ts` file so each runs full:

```bash
source activate.sh
./run-scrape.sh fl "session=2024"                 # FL: --allow_duplicates applied automatically
./run-scrape.sh usa "session=118 chamber=lower"   # US: scrape each chamber separately
./run-scrape.sh usa "session=118 chamber=upper"
```

Closed sessions are static, so this is a one-time backfill (no need to add them to the
schedule). Historical scrapes exercise code paths the daily current-session runs never hit
— that is how the `bills.py:614` FL PDF-parse crash surfaced.

**FL multi-session backfill — use `backfill-fl-historical.sh`.** A single FL *regular*
session is a large full scrape (26–30+ hrs each), so a naive one-off
`./run-scrape.sh fl "session=2023"` gets preempted by the nightly runner before it finishes
and never writes a marker. (Historically these runs also crawled at ~1 bill/min because the
flhouse.gov WAF cookie expired after ~1 hr and every later House lookup hit a 60s backoff —
fixed in PR #5; see "Florida House votes vanish on long scrapes" below.) The driver script runs the
sessions sequentially, smallest-first, and **skips any session that already has a `.ts`
marker**, so it is resumable — re-run it and it picks up only what hasn't landed:

```bash
mkdir -p logs/backfill
# All 8 sessions 2023+ (detach — the 3 regulars take days; run off the nightly window):
nohup ./backfill-fl-historical.sh >> logs/backfill/fl-historical.out 2>&1 &
# Or an explicit subset (e.g. just the fast specials):
./backfill-fl-historical.sh 2023B 2023C 2025A 2025B 2025C
```

Live scraper output goes to `logs/scraper.log` (run-scrape.sh tees there); the per-session
`logs/backfill/fl_<id>.log` only holds the wrapper's own lines. Track the driver with
`grep -aE "DONE|FAILED|complete" logs/backfill/fl-historical.out`.

**Backfill status (updated 2026-07-21):**
- **US 118** — done 2026-07-08 (House 12,556 + Senate 6,759 = ~19,315 bills in the replica).
- **FL specials 2023B/2023C/2025A/2025B/2025C** — done 2026-07-16 (14/21/22/2/7 bills).
- **FL regular 2025** — done 2026-07-18 12:13 EDT, with the flhouse WAF fix (PR #5) live —
  1959 bills, 2148 vote events, DB-verified against `ddp-openstates-postgres-1`.
- **FL regular 2024 — RUNNING**, started 2026-07-21 12:28 EDT:
  `SKIP_PATCHES=1 nohup ./backfill-fl-historical.sh 2024 >> logs/backfill/fl-historical.out 2>&1 &`
  (`SKIP_PATCHES=1` needed — see the `apply-local-patches.sh` blocker note below). Next FL
  weekly scrape (wipes `_data/fl`) is Sun 2026-07-26 02:00 UTC — plenty of margin at the 2025
  run's actual rate (~13h for 1959 bills).
- **FL regular 2023 — STILL PENDING.** Run
  `SKIP_PATCHES=1 nohup ./backfill-fl-historical.sh 2023 >> logs/backfill/fl-historical.out 2>&1 &`
  after 2024 lands (markers make it safe to just re-run `./backfill-fl-historical.sh` with no
  args too — it skips anything already done). (Note: earlier Jul-8 FL 2023–2025 attempts failed
  to land — the first successful FL historical backfill is the 2026-07-16 specials run.)

**`apply-local-patches.sh` blocker (found 2026-07-21) — check before any manual `run-scrape.sh`
invocation.** The script's first step is `cd openstates-core && git checkout main`. If
`openstates-core` is parked on a feature branch with uncommitted changes (e.g. `phase1-bill-
provenance`, mid-work on `PLAN-bill-document-provenance.md`'s `diff_from_previous_version`
field as of 2026-07-20), that checkout fails with "local changes would be overwritten" and
`run-scrape.sh` aborts immediately via its `on_failure` trap — before the scrape itself even
starts. This also silently breaks the nightly `openstates_patch_refresh` ddp-sync job (cron
01:00 UTC) whenever core is left on a dirty feature branch. **Do not stash/discard that WIP to
unblock it** — pass `SKIP_PATCHES=1` to `run-scrape.sh` (or the backfill driver) instead; it's
safe as long as core's current branch already has whatever `apply-local-patches.sh`'s cherry-pick
list would apply (check its own commit history — e.g. `phase1-bill-provenance` already has
`d6653a5`'s content via `b0c297a`). Real fix is to get `openstates-core` back to a clean `main`
checkout (commit/push the WIP, or intentionally stash it) so the nightly patch refresh can
succeed again — not yet done as of 2026-07-21.

### Metrics and anomaly detection

Every run emits a clearly-visible summary line in `scraper.log`:

```
=== SCRAPE SUMMARY: fl session=2026 | mode=incremental | bills_scraped=47 | prev_run=62 (incremental) ===
```

And a warning if two consecutive incremental runs diverge by more than 80%:

```
WARNING: bills_scraped (3) is <20% of previous incremental run (62) — possible over-filtering for fl session=2026
```

**Incremental no-op (not a failure):** when an incremental run finds nothing changed since
the cutoff, openstates raises `no objects returned` and exits non-zero. `run-scrape.sh` detects
this in incremental mode and treats it as a clean **no-op** — it logs
`bills_scraped=0 | no changes since cutoff (no-op)`, advances the cutoff, skips the import, and
exits 0 (**no Slack alert**). Real failures, and any failure during a *full* scrape, still alert.

To check recent summaries:

```bash
grep "SCRAPE SUMMARY\|WARNING.*over-filtering" logs/scraper.log | tail -30
```

### Per-jurisdiction caveats

| State | Signal used | Known limitation |
|---|---|---|
| USA | GovInfo sitemap `lastmod` | None — clean server-side filter |
| FL | Last-action date in HTML `td[3]` | Column verified 2026-06-22; re-verify if flsenate.gov changes layout |
| WA | `CurrentStatus/ActionDate` from GetLegislation | Still O(n) GetLegislation calls; only downstream calls are skipped |
| MI | `dateFrom=` URL param in search | **Unverified**: may filter by intro date, not last-action date. If MI incremental runs return unexpectedly few bills, force a full scrape and compare counts |
| UT | `actionHistoryList[0].actionDate` | Saves processing time only; still one HTTP call per bill |
| MA | `PrimarySponsor.ResponseDate` | **Weak proxy** — sponsor date, not action date. Bills with new floor actions but unchanged sponsors will be incorrectly skipped. Note: MA does scrape vote events (re-enabled 2026-06-22) so this proxy is more risky than originally noted |
| AZ | `max(BillStatusAction.ReportDate)` | Still O(n) API calls; only sub-calls skipped |
| VA | `max(EventDate)` from events call | Events call unavoidable; saves 3 of 4 per-bill calls |
| NC | None | `scrapers/nc/bills.py`'s `scrape()` takes no `start=` argument — no incremental support at all, every run is a full walk (Phase 1 pilot state, onboarded 2026-08-31; see `PLAN-push-button-onboarding.md`) |

### ddp-sync compatibility

No changes needed in ddp-sync. It calls `run-scrape.sh <state> [session_arg]` with
`SKIP_PATCHES=1` — the incremental logic is entirely internal to `run-scrape.sh` and
invisible to the scheduler. The per-jurisdiction timeouts (FL=16h, WA=8h, USA=4h,
others=6h) were sized for full scrapes and remain valid as safety nets for the first
run of each state (when no `.ts` file exists yet).

Note: a ddp-sync scheduling bug caused secondary states (VA, MI, MA, UT, AZ) to run
on 2026-06-22 (Monday) when they should only run on Sundays. It also preempted WA
mid-scrape at ~18:38 by starting the secondary batch concurrently, leaving WA without
a completion marker. WA and USA were manually restarted. **Fixed/verified 2026-06-24:**
`secondary` is scoped to `sync_day: sunday`, and the running scheduler was confirmed
(`GET /ddp-sync/v1/schedule`) to fire secondaries Sunday-only. The separate scheduler
timezone bug (firing at local EDT instead of UTC) was also fixed for the openstates jobs
the same day. A coarse worktree lock (PID markers; `apply-local-patches.sh` + `run-scrape.sh`)
now prevents a manual patch rebuild from clobbering a running scrape.

### Recovery from a bad incremental run

If the incremental filter over-eagerly skipped bills (evidence: upstream has bills/votes
we're missing in the local DB):

```bash
# 1. Force full rescrape for the affected jurisdiction
rm logs/last-run/<key>.ts
./run-scrape.sh <state> [session=...]

# 2. Confirm counts look right after the full run
grep "SCRAPE SUMMARY" logs/scraper.log | tail -5
```

The full run re-imports everything and resets the timestamp cleanly.

---

## Verifying a Michigan scraper fix against the live site (OPEN-137)

Michigan is the fleet's most WAF-sensitive jurisdiction and the only one excluded from scrape
retries entirely (OPEN-53: retrying against a WAF worsens a block, because each attempt is more
traffic from an already-suspect client). So "just run the scraper and see" is the wrong instinct
here — a full MI run is roughly 3,800 requests and 7–8 hours at the live 10 rpm cap, and it has
been explicitly declined as a verification budget more than once.

This is the cheap procedure. Roughly three requests.

**Step 0 — check the fix is actually deployed before testing it.**

Easy to skip, and it invalidates everything after it. Merging a PR on GitHub does not update this
host; `apply-local-patches.sh` does, on its daily 01:00 UTC run
(`openstates_scrape.patch_refresh` in ddp-sync's `config/sync_schedule.yaml`).

**Check for the fix itself, not just for "up to date".** A zero commit count does not prove your
fix is present — the checkout could be diverged, dirty, or on another branch, and a non-zero count
may be entirely unrelated commits:

```bash
cd ~/Developer/repos/ddp-open-states/openstates-scrapers
git branch --show-current                       # expect: main
git status --porcelain | head                    # expect: empty
git fetch origin
git merge-base --is-ancestor <FIX_COMMIT> HEAD && echo "fix commit present"
grep -c '<FIX_SYMBOL>' scrapers/mi/bills.py      # expect: non-zero
```

`<FIX_SYMBOL>` is whatever the fix introduced — for OPEN-132 it was `_redirected_single_bill`.
The grep is the check that actually matters: it asks whether the running code contains the fix,
which is the question, rather than whether git thinks the branch is current.

**Two things worth knowing about the refresh, because they mislead in opposite directions.**

It works: the reflog shows real `pull origin main: Fast-forward` entries on consecutive days. So a
checkout that is a few commits behind is usually just "merged after last night's run", and waiting
until 01:00 UTC is a legitimate answer.

But it **skips silently when a scrape is running**, by design — both nested repos are installed as
pip *editable* packages, so pulling underneath a live scrape would swap the code out from under it.
The skip is logged to `scraper.log` as `skipping patch refresh (run manually after scrape
completes)`, and **ddp-sync still records the job as `done`**, because skipping is a clean exit.
There were 11 such skips in the retained logs. Nobody runs it manually afterwards.

So do not infer "deployed" from the job having run. Check the grep above. And if you do pull
manually, confirm no scrape is in flight first — `ls /tmp/ddp-openstates-scrapes/` must be empty —
for exactly the reason the script guards against. Nothing else happens after the pull loop (the
script is 56 lines), so a manual `git checkout main && git pull` really is doing that job early
rather than instead of it.

**Step 1 — is the thing you are about to "recover" actually missing?**

Free, and it has already saved one unnecessary scrape. A dropped bill often reappears in a later
run, so check before spending requests:

```bash
psql "$DATABASE_URL" -c "
SELECT b.identifier, b.created_at::date, b.updated_at::date
FROM opencivicdata_bill b
JOIN opencivicdata_legislativesession ls ON ls.id = b.legislative_session_id
JOIN opencivicdata_jurisdiction j ON j.id = ls.jurisdiction_id
WHERE j.name = 'Michigan' AND b.identifier = 'SR 135';"
```

If `updated_at` is later than the incident date, a subsequent run already picked it up and there
is nothing to recover. Verified 2026-08-23 for OPEN-132's dropped bill: `SR 135` present, created
2026-07-11, updated 2026-08-08 — the 2026-07-25 drop cost that run's update, not the bill.

> ### STOP — everything below writes to the production database
>
> Steps 2 and 3 run `run-scrape.sh`, which scrapes **and imports**. There is no dry-run flag.
> Proceed only with named approval from whoever owns the data, and record that approval on the
> ticket you are working. A read-only session stops here, at the end of step 1.

**Step 2 — one targeted bill fetch, if recovery IS needed.**

`bill_no=` targeting (OPEN-81) exists for exactly this and needs no full run:

```bash
source activate.sh
./run-scrape.sh mi bill_no=<BILL_NO_ARG>        # e.g. bill_no=SR135
```

Note the two formats differ and both are correct: the database stores `SR 135` with a space, the
scraper argument takes `SR135` without one. `_mi_bill_id_to_no()` normalises the padding and
spacing, so `SR135`, `sr 0135` and `SR 0135` all resolve to the same bill.

**Step 3 — confirm the behaviour, both directions.**

Over-firing matters as much as under-firing, so check both. The redirect case and the genuinely
empty case must be **distinguishable in `logs/scraper.log`**, not merely both "successful":

| Case | Expected `scraper.log` line |
|---|---|
| one match, redirected | `MI search matched exactly one bill and redirected to its page: ... (OPEN-132)` |
| genuinely empty window | `MI search returned a results page with no matching bills -- genuine empty result` |
| neither shape | `MI search response is neither a results page nor a bill page ...` |

Pass for the one-match case is the bill present in the database afterwards, **not** that the
scrape exited 0 — a silent drop exits 0, which is the entire reason OPEN-132 existed.

Choosing the windows is the fiddly part, and it is worth doing from the scrapelib cache before
spending any live request: `_cache/` already holds real `ExecuteSearch` responses for many
`dateFrom` values, so you can often find a one-match window without asking the site anything. See
`notes/open134-mi-recency-signal-investigation-20260823.md` for how to read them.

**If a targeted scrape imports something wrong**, the bill's row is updated rather than duplicated
(the importer matches on the natural key), so the remedy is a corrected re-scrape of the same
`bill_no=`, not a delete. Record what you ran either way.

**Record the cost on the ticket**, in the shape every prior MI investigation used: how many
requests you made, to which endpoints, and whether the cache could have answered it instead. Two
of them — OPEN-89 and OPEN-134 — answered their questions with **zero** live requests by reading
`_cache/` first, and both wrote that down, which is why the number is now the first thing anyone
asks. If a run starts making more requests than you expected, stop it rather than letting it
finish: MI is the one jurisdiction where the recovery from over-scraping costs more than the
information.

---

## Motion classification

`opencivicdata_voteevent.motion_classification` is a PostgreSQL ARRAY column. The scrapers
set it at scrape time using `classify_motion()` from `openstates-scrapers/scrapers/classify_motion.py`,
driven by YAML patterns in `openstates-scrapers/scrapers/config/motion_classification.yaml`.

### Current accuracy (as of 2026-07-03, after `807fa57`)

| Jurisdiction | Classified | Total votes | Notes |
|---|---|---|---|
| Arizona | 97% | 3,460 | "Retained on Calendar" correctly unclassified |
| Florida | 99% | 1,889 | A–XXXXXX amendment texts correctly unclassified |
| Massachusetts | 64% | 45 | "Item X passed over veto" intentionally unclassified |
| Michigan | 95% | 1,083 | Bare "roll call Roll Call #N" texts unclassified |
| United States | 58% | 732 | Cloture-to-proceed, recommit, table intentionally unclassified |
| Utah | 81% | 1,917 | "Senate/ passed 2nd reading" intentionally unclassified |
| Virginia | 77% | 11,526 | Many procedural VA texts unclassified by design |
| Washington | 89% | 2,302 | Per-amendment line-level texts (page/line refs) unclassified |

**Remaining unclassified that are intentional (not bugs):**
- UT "Senate/ passed 2nd reading": 2nd reading is an intermediate floor vote, not final passage
- MA "Item X passed over veto": veto overrides on specific budget line items — distinct action class
- USA cloture-to-proceed, recommit, table: procedural motions, not passage attempts
- WA page/line amendment texts: individual amendment votes at the amendment level
- VA constitutional reading dispensed, reconsider, insist: procedural non-passage votes

### Re-running the backfill

After changing `motion_classification.yaml`, re-run the backfill to update existing DB records
(records scraped before the current YAML revision):

```bash
# Dry run first to preview changes
python3 backfill-motion-classification.py --dry-run 2>&1 | head -30

# Live run
python3 backfill-motion-classification.py

# Regenerate audit files after backfill
python3 audit-motion-texts.py
```

The backfill unconditionally overwrites all records with the current YAML output — re-running
after a YAML fix always produces the correct state.

### Audit files

`audit-motion-texts.py` generates `motion-text-audit/<jurisdiction>.md` — one row per unique
motion text, with classification and pass/fail counts. Use these to identify unclassified texts
that might warrant new YAML patterns.

Pre-classifier baseline snapshots (before `b7dfd2b`) are in `motion-text-audit-before/` for
comparison.

```bash
# Quickly see unclassified texts by jurisdiction
grep "unclassified" motion-text-audit/utah.md

# Check overall coverage
for f in motion-text-audit/*.md; do
  name=$(basename "$f" .md)
  head -3 "$f" | tail -1
done
```

### Known classification design choices

- **VA**: The `bill_action` field (from `LegislationActionDescription`) is NULL on most subcommittee
  records scraped before `807fa57`. The YAML now falls back to motion_text-based patterns
  (`"^subcommittee recommends reporting"`, `"^reported from"`) for committee_passage classification.
- **MI**: `concurr`/`concur`/`conference report` were in `not_passage` (wrong — chamber concurrences
  and conference report adoptions ARE passage events). Removed in `807fa57`.
- **UT**: `concur` was in `not_passage` (wrong — chamber concurrences ARE final passage). Removed.

---

## Known gotchas

### Module name is `usa`, not `us`

```bash
# Wrong
os-update us --scrape bills session=119

# Correct
os-update usa --scrape bills session=119 chamber=lower
os-update usa --scrape bills session=119 chamber=upper
```

### `start=` date format (USA scraper — fixed)

`USBillScraper` previously had a strptime bug (`%I` instead of `%M`). Fixed in `ddp-incremental` commit `371e7e6`. Incremental mode for USA now works correctly via the GovInfo sitemap `lastmod` field.

### `docker-compose up -d --force-recreate` on `deploy/docker-compose.ddp.yml` recreates ALL services, not just the one you meant to update

Found 2026-07-29 deploying api-v3 fork PRs #1/#2: running `--force-recreate` with no service name
recreated `ddp-openstates-postgres-1` (the dedicated Postgres on :5433) along with
`ddp-openstates-api-1`, even though only the api image had changed. That Postgres is the same DB
`run-scrape.sh` writes to — two live scrapes (`va`, `ut`) were mid-write at the time and both got
killed with `OperationalError: server closed the connection unexpectedly`. No bill/vote data was
lost (both had already finished their scrape+import phase; what got killed was the separate,
long-running `os-text-extract archive` pass) and the incremental-cutoff marker files weren't
advanced by the failed runs, but both archive passes had to be manually restarted
(`bash run-scrape.sh ut` / `bash run-scrape.sh va session=...`), staggered — launching both at
the same instant races on `apply-local-patches.sh` and one will fail near-instantly with no scrape
output at all.

**Always target the specific service when only one changed:**
```bash
# Wrong — recreates postgres too
docker-compose -f deploy/docker-compose.ddp.yml up -d --force-recreate

# Correct — only the api container
docker-compose -f deploy/docker-compose.ddp.yml up -d --force-recreate api
```
Check `ps aux | grep run-scrape` for live scrapes before touching this compose stack at all, same
as the git-checkout rule at the top of this file — the dedicated Postgres is shared infrastructure,
not just an api-v3 implementation detail.

### Virginia requires an LIS API key

`os-update va` fails until `VA_API_KEY` is set. Registration: https://lis.virginia.gov/developers

When the key arrives, add to `activate.sh`:
```bash
export VA_API_KEY=<your-key>
```
Then restore `va` to `run-all-scrapes.sh`. No code changes needed — the scraper is fully implemented.

**LIS API structure** (from swagger.json):
- Auth: `WebAPIKey: <key>` header on all requests
- Bill list: `POST /Legislation/api/getlegislationlistasync` with `{"SessionCode": 20261, "IncludeFailed": true}`
- Session codes: `20261` = 2026 Regular, `20262` = 2026 Special I (from `__init__.py` extras)
- The scraper also calls `/LegislationEvent/api/` (actions) and separate vote/sponsor endpoints — all under `lis.virginia.gov`, all use the same key
- `SessionCode` is typed as integer in the Swagger but the scraper passes it as a string — usually fine, but if results come back empty this is the first thing to check

### Michigan needs `--allow_duplicates` on import

The MI scraper produces duplicate bill JSON files (pagination overlap, issue #5697).
`run-scrape.sh` handles this automatically for `mi`. Do not use bare `os-update mi --import`.

### Florida uses PDF parsing — requires PyMuPDF

`scrapers/fl/events.py` imports `fitz` (PyMuPDF). It's already pinned in
`requirements-openstates.txt` (the toolchain venv). If missing after a manual venv build:
```bash
.venv/bin/pip install pymupdf
```

### `os-people` subcommand is `to-database` (hyphen) and needs `OS_PEOPLE_DIRECTORY`

```bash
# Wrong
os-people to_database fl

# Correct (after source activate.sh)
$OS_PEOPLE to-database fl
```

### Florida House votes vanish on long scrapes (flhouse.gov session handling)

`flhouse.gov`'s bot-detection issues a session cookie that expires well before a full FL
scrape finishes. Once it expires, every subsequent House request gets rejected — silently
dropping all remaining House committee votes (not a crash, just missing data). Not rate/IP
based: a fresh cold request works fine; only the *stale* cookie is rejected.

**Fixed in PR #5** (`_FLHouseWAFSource` in `scrapers/fl/bills.py`): stale cookies are dropped
before each request, so every House search starts a fresh session. The earlier `565804c`
handling (accept the block page after a 60s sleep) only prevented a crash — it never
recovered the votes.

**Residual gap fixed in OPEN-63** (`HouseSearchPage.accept_response` in `scrapers/fl/bills.py`):
PR #5 fixed the *systemic* case (every request rejected once the cookie goes stale past the
~1-hour mark), but left a rarer, still-live gap — a one-off, *transient* WAF challenge or empty
search result unrelated to cookie staleness. `accept_response` used to accept that page
unconditionally (`return True`) on the very first try, so a single bad request permanently and
silently zeroed that bill's House committee votes with zero retries. It now returns `False` for
that page (up to `HOUSE_SEARCH_MAX_ATTEMPTS`, currently 3), which feeds spatula's own retry loop
— a fresh `get_response()` call, re-triggering `_FLHouseWAFSource`'s cookie-drop — before finally
giving up and falling back to today's accept-and-skip behavior. Bounded so it can never let
spatula's own retry budget run out and raise `RejectedResponse` (which would crash the scrape).
See `notes/fl-open-63-tier1-tier2-root-cause-and-fix-20260811.md` for the diagnosis and
before/after evidence.

If you see `flhouse.gov WAF rejection persists` warnings, the site behavior has changed again.
Full technical detail (WAF vendor/cookie specifics) is in `RUNBOOK.internal.md` (not public).

### Michigan blocking (Barracuda WAF) — cookie-reuse fetcher (OPEN-19)

`legislature.mi.gov` runs Barracuda's bot-detection/WAF, which validates clients via a
JavaScript challenge a plain `requests`/scrapelib client can't execute — the actual root
cause behind the `get_session_list()` crash (OPEN-17) and disguised-404 bill-fetch blocks
(OPEN-18), and behind the archiver's long-standing MI `fetch_errors`/circuit-breaker trips.

**Primary fix (this ticket):** `openstates.utils.mi_cookies.MI_COOKIE_PROVIDER` launches a
real Playwright browser once to pass the WAF challenge, extracts the two long-lived cookies
(`x-bni-fpc`/`x-bni-rncf`) that let a plain HTTP client back in, and caches them to disk
(`CACHE_DIR/mi_waf_cookies.json`, keyed by their real expiry) — see
`openstates/utils/cookie_provider.py` for the generic mechanism. `scrapers/mi/bills.py`,
`events.py`, `__init__.py`'s `get_session_list()`, and `os-text-extract archive mi` all
attach these cached cookies to every request via the shared `mi_waf_get`/`fetch_with_retry`
helpers, invalidating and re-warming exactly once on a detected block before treating it as
a real failure. Requires the Playwright browser binary — see "Playwright browser binaries"
above.

OPEN-17/OPEN-18's own fallbacks (known-sessions safety net, block-page heuristics) remain in
place as defense-in-depth for if/when this cookie strategy stops working — this is
behavioral evidence from testing, not a guarantee about Barracuda's internals (see the
module docstring in `mi_cookies.py`).

**Second-layer defense — disguised-404 blocks in `scrape_bill()` (OPEN-18):** even with cached
WAF cookies attached, a request can still come back as a *genuine* HTTP 404 whose body is
legislature.mi.gov's own generic "The specified URL cannot be found" error page — for a bill
that demonstrably exists (confirmed live 2026-08-01 via Playwright). This isn't caught by the
200-status `BLOCK_PAGE_MARKERS` heuristic above, so `mi_waf_get()`'s `do_request` also catches
`scrapelib.HTTPError` and checks the body against a separate marker,
`content_matches_fake_404_block()` (`openstates/utils/cookie_provider.py`) — a match raises
`WafBlockDetected` (feeding into the same invalidate-and-retry-once dance), while a body that
doesn't match re-raises the original `HTTPError` unchanged, so a real dead link (e.g. a
malformed `ObjectName`) still fails exactly as before. `MIBillScraper.scrape_bill()` catches a
`WafBlockDetected` that survives the retry, logs a warning, and skips just that bill — but
aborts the whole scrape with a `ScrapeError` after `MAX_CONSECUTIVE_WAF_BLOCKS` (3) consecutive
detections, so a fully-blocked run fails fast and visibly instead of silently skipping hundreds
of bills. Because the detection lives in the shared `mi_waf_get()`, `events.py`'s two call
sites benefit from the same block-vs-real-error distinction automatically.

**Circuit breaker parity for `MIEventScraper` (OPEN-22 AC7):** the counting/threshold/raise
logic above is shared (`scrapers/mi/_waf_circuit_breaker.py`, `MIWafCircuitBreakerMixin`) rather
than duplicated, so `MIBillScraper` and `MIEventScraper` can't drift into two different abort
conventions. `MIEventScraper.scrape_event_page()` (called once per event link found on the
calendar page, analogous to `scrape_bill()`'s per-bill loop) uses the same skip-and-count/abort-
at-`MAX_CONSECUTIVE_WAF_BLOCKS` pattern. `MIEventScraper.scrape()`'s calendar-page fetch is
different in kind — it runs exactly once per scrape, not in a loop — so there's nothing to count
to 3 against; a block surviving `mi_waf_get`'s own retry there aborts immediately with
`ScrapeError` instead of the 3-strikes wait, converting what used to be an uncaught
`WafBlockDetected` crash into an explicit, intentional abort.

**MI-specific rate limit + `http_resilience_mode` opt-in (OPEN-21):** scoping a fix for the
wider IP-reputation/rate-history problem found MI got exactly the same request pacing as every
other, less-sensitive jurisdiction — `Scraper.__init__` (`openstates-core`'s
`openstates/scrape/base.py`) applies the platform-wide `SCRAPELIB_RPM` default (60 req/min,
`openstates/settings.py`) uniformly, and the richer `http_resilience_mode` (jittered
per-request delay, circuit breaker, connection-pool reset, retry-with-backoff) sits unused —
wired only as an opt-in CLI flag, never set `True` anywhere. `MIBillScraper.__init__` and
`MIEventScraper.__init__` (both via a shared `MIResilientScraperMixin` in `scrapers/mi/bills.py`)
now force `http_resilience_mode=True` unconditionally, regardless of what the CLI/`State`
instantiation path passes for other jurisdictions, and lower `self.requests_per_minute` to
`MI_SCRAPELIB_RPM` (env var, default **10/min** — roughly 1/6th of the platform default, ~1
request every 6s). This is a deliberately conservative *starting point*, not a measured
threshold (none exists yet) — chosen to put several real seconds of spacing between requests on
top of `http_resilience_mode`'s own 1-3s jittered delay, without making a full MI scrape
impractically slow. **Trade-off:** MI scrapes run measurably slower than before in exchange for
a meaningfully lower request footprint against the one jurisdiction with a confirmed,
escalating reputation-based block — expected to be revisited once OPEN-22's
sustained-blocking-escalation investigation has more data on what volume/cadence actually
triggers or clears a reputation hit. `MI_SCRAPELIB_RPM` is env-configurable so it can be tuned
without a redeploy, matching this codebase's existing convention (`SCRAPELIB_RPM`,
`STATS_BATCH_SIZE`, etc.).

**Retry-stacking correction (also OPEN-21):** enabling `http_resilience_mode` naively would have
made things *worse*, not better. `scrapelib.HTTPError` inherits
`requests.exceptions.RequestException`, and `retry_on_connection_error`'s except clause already
catches bare `RequestException` — so both `scrapelib.HTTPError` and
`requests.exceptions.ConnectionError` would be retried there too (3x, exponential backoff
10s→20s→40s) *before* `mi_waf_get()`'s own invalidate-and-retry-once dance (above) ever saw
them, silently doubling MI's request volume on every WAF block instead of reducing it. Resolved
by adding a generic, opt-in `_resilience_retry_excluded_exceptions` attribute to
`openstates-core`'s `Scraper` base (`openstates/scrape/base.py`) — empty tuple by default, so
every existing/future `http_resilience_mode` consumer keeps today's broad retry behavior unless
it explicitly opts out — and having `MIResilientScraperMixin` set it to
`(scrapelib.HTTPError, requests.exceptions.ConnectionError)`. This keeps `mi_waf_get()`'s
invalidate-and-retry-once dance as the *only* retry layer for WAF-related failures, while
`http_resilience_mode`'s other benefits (jittered delay, circuit breaker, connection-pool reset,
retry-with-backoff for genuine timeouts/URL errors/connection resets unrelated to the WAF) still
apply normally. Chose this over tuning `retry_on_connection_error`'s own backoff numbers because
it fully removes the double-retry rather than just resizing it, and because it's a two-line,
backward-compatible change to shared code rather than a duplicated retry loop living only in
MI's module.

**Live-verified 2026-08-02** (not just unit-tested, per this ticket's AC) against the real
`legislature.mi.gov`, using a real Playwright cookie warm-up and a real `MIBillScraper`, with the
raw transport call (`scrapelib.Scraper.get`) instrumented to count physical HTTP attempts:
confirmed `http_resilience_mode is True`, `requests_per_minute == 10 < 60`, and
`_resilience_retry_excluded_exceptions == (scrapelib.HTTPError, requests.exceptions.ConnectionError)`
on a real instance. Two real scenarios both produced exactly **2** physical HTTP attempts (1
initial + `mi_waf_get()`'s 1 rewarm-retry) rather than the 6+ the un-excluded resilience layer
would have caused: (a) a real WAF block-page response (200 status, matched
`BLOCK_PAGE_MARKERS`) on both attempts, correctly raising `WafBlockDetected` after the retry was
exhausted; (b) a request made with deliberately corrupted cookie values, which got a real
disguised-404 (`scrapelib.HTTPError`, OPEN-18's `content_matches_fake_404_block()` heuristic) on
the first attempt and a real block-page match on the rewarm attempt — exercising both of
`mi_waf_get()`'s detection paths live in one low-footprint run (4 real GETs total across the
whole check). **Incidental finding, out of scope for this ticket:** the live Playwright warm-up
returned zero matching cookies in this run (`x-bni-fpc`/`x-bni-rncf` absent from the warmed set)
and every request in the check hit a real block regardless of cookies presented — consistent
with the reputation-based override already documented in `mi_cookies.py`'s docstring and
relevant to OPEN-19/OPEN-20/OPEN-22, but not something OPEN-21's rate-limit/retry-stacking scope
addresses.

**Cookie session presenting three inconsistent User-Agent identities (OPEN-23):** found
2026-08-02 while live-testing OPEN-21's fix with a real Playwright browser
(`notes/mi-ip-reputation-block-confirmed-20260802.md`). Independent of the IP-reputation/WAF
question above, a real, separate bug: within a single MI scrape attempt, the cached cookie pair
got reused across three mutually inconsistent browser/OS identities — the real headless Chromium
that minted the cookies (`MI_COOKIE_PROVIDER`'s Playwright warm-up), a hardcoded
`"Firefox/118.0 on Ubuntu Linux"` string (`scrapers/mi/bills.py`'s old module-level `USER_AGENT`
constant) that every cookie-authenticated request sent instead, and a third, randomly-rotated
identity from `get_random_user_agent()`'s 7-entry pool whenever `http_resilience_mode`'s circuit
breaker, connection-error handling, or periodic fresh-session reset fired — a direct, unintended
side effect of OPEN-21's own `http_resilience_mode=True` opt-in for MI, since none of that
rotation code ever ran for MI before OPEN-21. A single cookie session presenting as three-plus
unrelated identities within one scrape attempt, sometimes within seconds of each other, is exactly
the kind of inconsistency bot-mitigation products like Barracuda are built to flag.

**Fix, part 1 — capture and reuse the real warm-up UA:** `CookieProvider`'s Playwright warm-up
(`openstates/utils/cookie_provider.py`) now also captures `navigator.userAgent` from the exact
page/browser that receives the WAF-passing cookies (`page.evaluate("() => navigator.userAgent")`,
right after the page load, before the browser closes), and caches it alongside the cookies in the
same on-disk JSON file (a reserved `_meta.user_agent` key) — one warm-up populates both, never two
independent derivations. A cache file missing that key (e.g. one written before this change) is
treated like a missing/expired cookie: rewarmed once rather than silently handing back cookies
with no matching UA. `CookieProvider.get_user_agent()` mirrors `get_cookies()`, and
`fetch_with_retry(do_request)`'s contract changed so `do_request(cookies, user_agent)` always
receives a matched pair — including on the one retry-after-invalidate, so a mid-scrape re-warm
can never pair fresh cookies with a stale UA. `mi_waf_get()` (shared by `bills.py`, `events.py`,
`__init__.py`'s `get_session_list()`, and — found via a related-code search, not originally in
this ticket's file list — `openstates-core`'s `text_extract.py` archiver, which shares
`MI_COOKIE_PROVIDER.fetch_with_retry` and previously sent no MI-specific UA at all) passes this
through, and every call site now builds `headers={"User-Agent": user_agent}` explicitly from the
live value instead of a hardcoded/guessed string. `bills.py`'s old `USER_AGENT` constant is gone;
`events.py`'s two request sites, which previously set no explicit headers at all (silently
inheriting whatever resilience-mode's rotation last set), now get them too. Since scrapelib merges
explicit per-call headers over session-level `self.headers`, this explicit-per-request value is
what actually goes out on the wire regardless of `self.headers`' own state — the real correctness
mechanism.

**Correction, same day, post-merge:** an earlier revision of this fix also set
`self.headers["User-Agent"]` once at the top of each scraper's `scrape()`, purely for
introspection/logging hygiene (so a live debugger or log line would see the same consistent
identity too). **Reverted** — reviewed against the full `scrapers/mi/tests/` suite (not just the
subset this PR's own testing section originally ran) and found it forced an unscheduled
`MI_COOKIE_PROVIDER` warm-up at the very top of `scrape()`, before any request actually needed
one: an extra, unplanned hit against a WAF-sensitive site, and a footgun for any test that calls
`scrape()` without stubbing `get_user_agent()` — confirmed it broke 3 of `MIEventScraper`'s own
existing tests exactly that way (`ModuleNotFoundError` in an environment with no Playwright
installed; a real live warm-up attempt in one that has it). Not load-bearing for the actual fix
above, so simply removed rather than patched. Full suite: 34/34 passing after the revert.

**Fix, part 2 — stop `http_resilience_mode` from clobbering it:** a new
`_resilience_user_agent_rotation_enabled` flag on `openstates-core`'s `Scraper`
(`openstates/scrape/base.py`), default `True`, guards all 4 of `get_random_user_agent()`'s call
sites (`__init__`, the circuit breaker's post-timeout rotation, the generic connection-error
rotation, and `_create_fresh_session()`'s periodic reset) — mirrors OPEN-21's own
`_resilience_retry_excluded_exceptions` precedent (an opt-out attribute, not a platform-wide
behavior change) over the alternative of re-deriving the rotation from MI's own warm-up mechanism,
since it keeps `openstates-core` generic and is a smaller diff. `MIResilientScraperMixin`
(`scrapers/mi/bills.py`) sets it `False`. **Important implementation subtlety:** this had to be a
**class attribute**, not an instance attribute assigned inside `__init__` (which is how
`_resilience_retry_excluded_exceptions` itself works) — `Scraper.__init__`'s own rotation call
fires *during* `super().__init__()`, before a subclass mixin's post-`super()` `__init__` body ever
runs, so only a class-level override (resolved via MRO from the moment the instance exists) actually
suppresses that specific call site; an instance-attribute copy of the existing pattern would have
silently missed it. The rest of `http_resilience_mode` (jittered delay, circuit breaker pause,
connection-pool reset) stays fully intact for MI — only the `self.headers["User-Agent"]` mutation
itself is suppressed. Scoped to MI alone; no other jurisdiction currently uses
`http_resilience_mode`, and a regression test (`openstates/scrape/tests/test_scraper.py`) confirms
`get_random_user_agent()` still fires normally at every call site for a scraper that hasn't opted
out.

**Live-verified 2026-08-02** against the real `legislature.mi.gov`: a real Playwright warm-up
(fresh temp cache file, not the real `CACHE_DIR/mi_waf_cookies.json` a scheduled scrape might be
using) captured a genuine headless-Chromium UA
(`Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ... HeadlessChrome/151.0.7922.34 Safari/537.36`),
and a real `MIBillScraper` (`http_resilience_mode=True`,
`_resilience_user_agent_rotation_enabled=False` confirmed on the live instance) made two real
`mi_waf_get()`-wrapped requests against MI's own warm-up URL, with `requests.Session.send`
instrumented to record every real outgoing `User-Agent` header. All 4 physical GETs across both
attempts (each triggered `mi_waf_get()`'s own invalidate-and-retry-once, since both attempts hit a
real block) presented the identical, warm-up-captured UA — including the second attempt, made
*after* forcibly tripping the circuit breaker (`_consecutive_failures` set to threshold,
`_circuit_breaker_timeout` temporarily reduced to 1s to avoid a real 120s sleep) — confirming the
opt-out holds under a real resilience-mode event, not just in unit tests. **What this check
does not show:** it drove `mi_waf_get()` directly rather than a full `scrape()` call, so
`self.headers`'s own hygiene-only sync (part 1, above) wasn't exercised live — that's covered by
the unit tests in `scrapers/mi/tests/test_user_agent_consistency.py` instead. **Incidental
finding, same as OPEN-21's own live check:** every request in this run hit a real WAF block
regardless of the (correctly matched) cookies/UA presented, and the warm-up itself returned zero
of the required `x-bni-fpc`/`x-bni-rncf` cookies — consistent with the reputation-based override
documented in `mi_cookies.py`, not something this ticket claims to have solved. This ticket
removes one detection signal (identity inconsistency); it does not by itself clear the sustained
IP-reputation block OPEN-22 is tracking.

### Utah blocking (le.utah.gov WAF on default User-Agent) + closed-session incremental aborts (OPEN-106)

The weekly `ut` scrape failed 2026-08-15 with `CommandError: no sessions from
Utah.get_session_list()`. Two distinct, compounding causes, both confirmed live:

1. **`get_session_list()` had no resilience of its own.** It called `url_xpath()` with no
   `user_agent=`, falling back to `requests`' bare default UA. A direct repeated fetch of
   `le.utah.gov/bills/billSearch.jsp` with that default header came back `200 OK` with a
   246-byte `"Request Rejected"` WAF page — zero sessions, no exception, nothing to
   distinguish from a genuinely empty page. The same endpoint is also independently
   flaky/rate-limited on top of that (a bare-UA request failed twice then succeeded a third
   time with no code change at all) — a browser-shaped UA measurably reduces rejections but
   does not make the site reliable.
2. **An incremental scrape of a closed session legitimately yields zero bills, and that used
   to abort the whole run.** The weekly run scrapes every "active" session in one invocation
   (currently `2025S2`, a closed special, and `2026`, current) — every `2025S2` bill predates
   the incremental `start=` cutoff, so `UTBillScraper.scrape()` correctly yields nothing for
   it, but zero net output tripped `openstates-core`'s blanket `ScrapeError`, aborting the run
   before the still-active `2026` session (queued right after) was ever reached.

**Fixed in OPEN-106** ([PR #36](https://github.com/Digital-Democracy-Project/openstates-scrapers/pull/36),
merged 2026-08-21): `get_session_list()` sends a browser-shaped UA (`get_random_user_agent()`,
same helper FL/MI use) and retries 3× with backoff, raising a specific `ScrapeError` naming the
last real failure if still empty. `UTBillScraper` defaults to the same UA. `scrape()` now raises
`EmptyScrape` (the existing `openstates-core` escape hatch) when it found real bill-list
candidates but every one predates the incremental cutoff, instead of falling through to the
blanket `ScrapeError` — a session whose list page itself came back empty (real breakage) is
unchanged and still raises normally. Live-reverified post-merge against the real site: see
`notes/open-106-utah-session-list-waf-and-empty-scrape-fix-20260821.md` for the full trace
(exit 0, both sessions handled correctly, 1,021 bills checked in ~34 min at the platform's
60 req/min default).

Residual, explicitly out of scope: `le.utah.gov`'s own flakiness/rate-limiting beyond what a UA
change fixes. If `billlist.jsp` itself comes back genuinely empty (not just the incremental
filter finding nothing), that's still the ordinary "no objects returned" `ScrapeError` —
intentionally not masked.

### `SELECT DISTINCT + ORDER BY RANDOM()` fails in PostgreSQL

Must use a subquery. Already fixed in `quality_check.py`.

---

## Data quality check

`quality_check.py` samples bills and people from the local DB, fetches the same records
from both `localhost:8002` and `v3.openstates.org`, and diffs key fields.

**Expected warnings** (not failures):
- `local has MORE votes/data than live` — likely one of our fork-only fixes that hasn't been
  contributed upstream yet (the FL WAF session fix, AZ empty-vote-event filtering, MI/WA
  roll-call numbers, or the VA fixes — see "Scraper state" above). UT 2026 and MI House votes
  used to be the example of this via PRs #5695/#5696, but those merged upstream 2026-06-15/16,
  so that specific gap should have closed — a *new* instance pointing at those two now would be
  worth investigating. In general this class of warning is a sign our data is *better*, not
  broken.

**Actual failures to investigate:**
- `local is MISSING votes vs live` — we have fewer votes than upstream
- `title differs` — possible scraper or data normalization issue
- `missing from local api-v3` — bill exists upstream but we haven't scraped it

Default run uses 5 bills + 3 people per jurisdiction ≈ 56 requests, well within the 250/day limit.

**Coverage/completeness mode** (`--coverage`, see `PLAN-coverage-completeness-check.md` for the
full design): checks whether upstream has any bills we never scraped at all, not just whether
scraped bills match:

```bash
OPENSTATES_API_KEY=<key> python3 quality_check.py --coverage <jurisdiction> <session>
OPENSTATES_API_KEY=<key> python3 quality_check.py --coverage mi 2025-2026 --tier2-limit 500 --tier2-random
```

- `--tier2-limit N` caps the sub-record (Tier 2) check to N bills instead of every bill present
  in both APIs; omit for a full sweep.
- `--tier2-random` (combine with `--tier2-limit`) samples N bills at random instead of the first
  N in sorted order — without it, `--tier2-limit` always returns the same lowest-numbered,
  earliest-filed bills, which isn't a representative sample of a session's health.
- Output also written to `logs/quality-check/<jurisdiction>_<session>.log`.
- **Known caveat (2026-08-03):** running a Tier 2 sample concurrently with a separate Tier 1
  sweep can produce a burst of live-API `429 Too Many Requests` errors — each process
  self-rate-limits to the licensed tier's 2 req/sec but they don't coordinate with each other.
  These show up as `live API error` failures that are rate-limit noise, not real findings; don't
  run two coverage checks against the live API at the same time if avoidable.
- **US federal (`us`) coverage was broken until 2026-08-03** (fixed in
  [PR #69](https://github.com/Digital-Democracy-Project/ddp-open-states/pull/69)) — if you're
  reading an older `--coverage us <session>` log showing 100% of bills "missing," that's the bug,
  not a real gap.
- **Tier 2's "local" side does not read `DATABASE_URL` — it always hits the single shared
  `localhost:8002` api-v3 instance** (found 2026-08-13, OPEN-63 round-3 verification).
  `fetch_bill(LOCAL_API, ...)` uses the module-level `LOCAL_API = "http://localhost:8002"`
  constant unconditionally; only Tier 1's direct-DB identifier diff (`fetch_all_local_identifiers`)
  actually honors `DATABASE_URL`. On this Mac Studio, `localhost:8002` is always DDP's one
  always-on production api-v3 container (`docker-compose.ddp.yml`, `DATABASE_URL` hardcoded to
  the `openstates` DB) — so pointing your own shell's `DATABASE_URL` at `openstates_dev` (or any
  other DB) to test freshly-scraped dev data will make Tier 1's coverage numbers correct but
  **Tier 2's per-bill title/votes/sponsorships comparison will silently keep reading production
  data regardless.** Caught this by getting a Tier 2 result that flatly contradicted a direct
  query against `openstates_dev` for the same bill. If you need Tier 2 to genuinely test
  non-production data, either query the DB directly yourself for the "local" half instead of
  trusting Tier 2's own report, or stand up a second api-v3 container from the existing
  `ddp-openstates-api:local` image on a different host port with `DATABASE_URL` pointed at the DB
  you actually want to test (hit a Colima host-port-forwarding snag doing this once — worth
  budgeting time to debug that, or falling back to the direct-query workaround).

---

## First-time setup (for reference)

```bash
# 1. Create DB
docker exec -it ddp-agents-postgres-1 psql -U cams -c "
  CREATE USER openstates WITH PASSWORD 'openstates_dev';
  CREATE DATABASE openstates OWNER openstates;
  GRANT ALL PRIVILEGES ON DATABASE openstates TO openstates;"

# 2. Build the OpenStates toolchain venv (see "OpenStates toolchain venv" above)
/usr/bin/python3 -m venv .venv
.venv/bin/pip install 'pip<24.1'
.venv/bin/pip install --no-deps -r requirements-openstates.txt

# 3. Initialize schema + seed all jurisdictions (~5 min)
source activate.sh && $OS_INITDB

# 4. Import legislator YAML for target states
for state in fl wa us va mi ma ut az al; do
    $OS_PEOPLE to-database $state
done

# 5. api-v3 dependencies — OBSOLETE. api-v3 is now a Docker container (see "Services");
#    its deps live in the image, built from deploy/Dockerfile.ddp. Do NOT install these
#    into the toolchain venv or shared env — fastapi[all] pulls pydantic 2.x and breaks
#    the scrapers (this is precisely what happened Jun 2026). Kept for historical reference:
#    (cd api-v3 && pip3 install gunicorn fastapi[all] sqlalchemy==1.4.* psycopg2-binary \
#        sqlalchemy_utils sentry-sdk pybase62 python-slugify redis \
#        prometheus-fastapi-instrumentator uvicorn[standard])   # containerized 2026-06-24

# 6. Create api-v3 auth table + API key
docker exec -i ddp-agents-postgres-1 psql -U openstates -d openstates <<'SQL'
CREATE TABLE IF NOT EXISTS profiles_profile (
    id VARCHAR PRIMARY KEY, api_key VARCHAR, api_tier VARCHAR);
CREATE INDEX IF NOT EXISTS ix_profiles_profile_api_key ON profiles_profile (api_key);
INSERT INTO profiles_profile VALUES (
    '00000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000001', 'unlimited') ON CONFLICT DO NOTHING;
SQL

# 7. Register launchd services (scraping is scheduled by ddp-sync, not launchd).
#    Both are system LaunchDaemons (migrated 2026-07-17, PLAN-cams-hardening-isolation
#    Phase 2, ddp-agents repo) — installed/managed via the `cams` CLI, not a bare
#    `launchctl bootstrap gui/...` against a `~/Library/LaunchAgents` plist:
sudo cams install-daemons

# 8. Run initial scrapes
./run-scrape.sh ut "session=2026"
./run-scrape.sh mi
# ... etc
```

---

## api.digitaldemocracyproject.org proxy

`ddp-api` exposes the local api-v3 at `/openstates/*` via WireGuard for services
that don't have direct tunnel access (e.g. ddp-broker-py). Real WireGuard IP and AWS
role/secret names below are in `RUNBOOK.internal.md` (not public).

**Route:** `GET|POST https://api.digitaldemocracyproject.org/openstates/{path}`
**Auth:** Standard ddp-api bearer token — `Authorization: Bearer <ddp-api-token>`
**Forwards to:** `http://<mac-studio-wireguard-ip>:8002/{path}` (Mac Studio over WireGuard)
**Internal key:** The UUID key for api-v3 is injected transparently as `x-api-key` header. Callers never supply it.
**Code:** `ddp-api/app/routes/openstates_proxy.py`
**Env vars (ddp-api):** `OPENSTATES_SERVICE_URL=http://<mac-studio-wireguard-ip>:8002` (only one needed)

**Test:**
```bash
curl -si -H "Authorization: Bearer <ddp-api-token>" \
  "https://api.digitaldemocracyproject.org/openstates/bills?jurisdiction=ut&session=2026&identifier=HB+5"
```

ddp-sync and votebot (EC2, have WireGuard) hit `http://<mac-studio-wireguard-ip>:8002` directly at cutover —
they use the internal UUID key, **not** a ddp-api bearer token. ddp-broker-py (EC2, no WireGuard)
goes through `https://api.digitaldemocracyproject.org/openstates` and needs a ddp-api bearer token.

### ddp-api read key for the OpenStates proxy (issued 2026-06-25)

> **⚠️ 2026-06-27:** the `ddp-ro-…` key issued 2026-06-25 **is** persisted in the org-credentials
> secret — stored as `key_hash` (sha256), by design; the plaintext is shown once at issuance and is not
> recoverable. The `{"detail":"Invalid Bearer token"}` failure was a **wrong/lost plaintext**, not a
> missing key: the token being sent didn't hash to the stored `key_hash`. **Fix:** compare
> `printf '%s' "$TOKEN" | shasum -a 256 | cut -d' ' -f1` against the stored hash; if it differs and the
> original plaintext is lost, **rotate** (`POST /admin/keys/<id>/rotate`) to mint a fresh plaintext and
> update `DDP_OPENSTATES_BEARER_TOKEN` in prod ddp-broker-py. (Separately, the key store is being
> **decoupled onto a dedicated api-keys secret** for separation of concerns — ddp-api
> `PLAN_key_management.md` addendum 2026-06-27 — independent of this token issue, not yet deployed.)

A **read-scoped** managed key (`ddp-ro-…`) was issued for OpenStates consumers and loaded into
**prod ddp-broker-py** as `DDP_OPENSTATES_BEARER_TOKEN` (with `DDP_OPENSTATES_API_ROOT=https://api.digitaldemocracyproject.org/openstates`).
ddp-broker-py routes **only the jurisdictions in `DDP_OPENSTATES_JURISDICTIONS`** (comma-separated)
through the replica — everything else still hits real OpenStates. So cutover is **gradual and
per-jurisdiction**: start that var empty (credential staged, zero traffic), then add canary
jurisdictions (e.g. `UT,MI` — ones with validated data; **not MA yet**, vote data unvalidated).

**Key management** (admin auth — `Bearer $API_BEARER_TOKEN` or a `ddp-admin-…` key):
```bash
BASE=https://api.digitaldemocracyproject.org
curl -s -X POST "$BASE/admin/keys" -H "Authorization: Bearer $ADMIN" -H "Content-Type: application/json" \
  -d '{"name":"open-states-replica-read-only","scopes":["read"]}'   # issue (plaintext shown once)
curl -s "$BASE/admin/keys" -H "Authorization: Bearer $ADMIN"                 # list
curl -s -X DELETE "$BASE/admin/keys/<id>" -H "Authorization: Bearer $ADMIN"  # revoke
```
The ddp-api EC2 role needs **`secretsmanager:PutSecretValue`** on the org-credentials secret
for issuance/revocation/rotation (read-only `GetSecretValue` makes the *service* work but 500s on issue).
(Once the api-keys decoupling is deployed, that grant moves to the new secret; the
rewritten persist path also **500s loudly** on a missing-`PutSecretValue` write rather than silently
falling back to a local file. Exact role/secret names are in `RUNBOOK.internal.md`, not public.)
**ddp-api logs → journald:** `journalctl -u ddp-api -n 50` (the old `/var/log/ddp-api.*` file redirect
is removed; see ddp-api README).

---

## Cutover (future — not yet)

When the shadow pipeline has run reliably for ≥4 weeks:

1. Make `OPENSTATES_API_BASE` env-configurable in 7 files across ddp-broker-py, ddp-sync, votebot
2. Fix `GET /people/{id}` → `GET /people?id=` in `votebot/services/bill_votes.py`
3. Fix WA biennial + US Congress session aliases in votebot's `BillVotesService.get_bill_info()`
4. Set env vars per service:
   - `ddp-broker-py`: `OPENSTATES_API_BASE=http://localhost:8002`
   - `ddp-sync` (EC2): `OPENSTATES_API_BASE=http://<mac-studio-wireguard-ip>:8002`
   - `votebot` (EC2): `OPENSTATES_API_BASE=http://<mac-studio-wireguard-ip>:8002`
5. `OPENSTATES_API_KEY=00000000-0000-0000-0000-000000000001` in all three

Revert = restore original env vars + restart. No image rebuild.
