# PLAN: Local OpenStates Stack

**Status:** ACTIVE — running since 2026-06-13. Incremental scraping implemented 2026-06-22.

**Goal:** Run our own legislative data scrapers locally, building a shadow copy of OpenStates data on this machine. The local pipeline runs in parallel with — not instead of — the live `v3.openstates.org` API. Production services continue pointing at the remote API until we've validated local data is stable and reliable enough to switch. The cutover is a future decision, not part of this plan.

**Motivation:** OpenStates was acquired. Two bugs (UT #5695, MI #5696) went unnoticed until we filed PRs ourselves. Running our own scrapers gives us independence from upstream maintenance pace and a tested fallback path if the remote API degrades.

**Not a ground-up build.** All core infrastructure (PostgreSQL, Redis, Docker/Colima, Pinecone ingestion, bill/vote data models, ETL pipeline) already exists across the DDP stack. This plan wires the scrapers into what we already have.

**SSD headroom:** ~1TB free on local SSD. Full scrape of FL + WA + US federal + 6 secondary states is estimated at 20–50GB including indexes. No capacity concern.

**License:** OpenStates is open source (CC0 data, MIT code). No legal review needed.

---

## 1. What We Are NOT Building

Before scoping work, document what already exists so nothing is duplicated:

| Concern | Already solved by |
|---|---|
| Bill / Vote / Representative data models | `ddp-broker-py` (`common/models/`) |
| Bill import ETL (OpenStates → broker DB) | `ddp-broker-py` `OpenStatesService` + Celery tasks |
| Bill text → Pinecone ingestion | `ddp-sync` `BillVersionSyncService` |
| Legislator bio → Webflow | `ddp-sync` `LegislatorBioPipeline` |
| Bill-org cross-referencing | `ddp-sync` `webflow_cms/services/bill_org_sync.py` |
| PostgreSQL instance | Running at `localhost:5432` (CAMS Docker container) |
| Redis instance | Running at `localhost:6379/0` (CAMS Docker container) |
| Docker/Colima | Running via `com.ddp.colima` launchd service |
| scraper codebases | Cloned at `~/Developer/repos/ddp-open-states/openstates-scrapers` |
| openstates-core | Cloned at `~/Developer/repos/ddp-open-states/openstates-core` |
| People YAML data | Cloned at `~/Developer/repos/ddp-open-states/people` |
| Bill-tracking filter | `Bill.tracked` boolean already in broker DB |
| Rate limiting | `ddp-sync` `RateLimiter` class |
| Webflow CMS writes | `ddp-sync` `WebflowLookupService` |

**What this plan adds (shadow phase — no service rewiring yet):**
1. A dedicated `openstates` PostgreSQL database (on the existing container, port 5432)
2. `openstates-core` installed into a Poetry venv that can run `os-update`, `os-initdb`, `os-people`
3. Scraper configuration for FL, WA, US federal, and the secondary states
4. `api-v3` (already cloned at `~/Developer/repos/ddp-open-states/api-v3`) running locally on port 8002 — the real OpenStates API pointed at local data, available for manual queries and validation
5. A `com.ddp.openstates-scraper` launchd service for nightly scheduled scrapes

**What this plan defers (cutover — separate future decision):**
- Changing `OPENSTATES_API_BASE` in ddp-broker-py, ddp-sync, and votebot
- Session alias mapping for WA biennial and US Congress session formats
- Automated fallback/failover between local and remote API

---

## 2. Target Jurisdictions

Based on `ddp-sync`'s `JURISDICTION_MAP` (the canonical list of active jurisdictions) and `ddp-broker-py`'s tracked jurisdictions:

| State | OpenStates code | Session format | Scraper class | Notes |
|---|---|---|---|---|
| Florida | `fl` | `"2025"` | `FlBillScraper` | Primary. House + Senate, PDF vote parsing |
| Washington | `wa` | `"2025-2026"` | `WABillScraper` | Primary. Biennial, XML API |
| US Federal | `us` | `"119"` | `USBillScraper` | Primary. GovInfo XML, ~10k bills |
| Virginia | `va` | `"2026S1"` | `VABillScraper` | Secondary. LIS API key in `.env`. |
| Michigan | `mi` | `"2025-2026"` | `MIBillScraper` | Secondary. Recently fixed House votes |
| Massachusetts | `ma` | `"194th"` | `MABillScraper` | Secondary. Vote scraping re-enabled 2026-06-22 |
| Utah | `ut` | `"2025"` | `UTBillScraper` | Secondary. Recently fixed API path |
| Arizona | `az` | `"2025"` | `AZBillScraper` | Secondary |
| Alabama | `al` | — | `ALBillScraper` | Not tracked by DDP — omitted from nightly schedule |

**Bill scope strategy:** Run full-state scrapes. All bills land in the local openstates DB. The `Bill.tracked = True` filter in `ddp-broker-py` (already implemented) controls which bills flow through the DDP pipeline. No scraper-level filtering is needed. For US federal (10k+ bills/session), a bill-ID allowlist shim at the import step is available as an optional optimization (see Phase 2, §Bill Scope Optimization).

---

## 3. Architecture

**Shadow phase (this plan):**
```
Legislature Websites
  ▼
openstates-scrapers (FL, WA, US, VA, MI, MA, UT, AZ, AL)  ← nightly launchd
  ▼
os-update CLI (openstates-core)
  ▼
openstates PostgreSQL DB ← NEW (localhost:5432/openstates)
  ▼
api-v3 ← NEW (localhost:8002) — local data, manual queries + validation only

https://v3.openstates.org  ← production services still point here (UNCHANGED)
  ├── ddp-broker-py
  ├── ddp-sync
  └── votebot
```

**Future cutover (not this plan):**
```
Mac Studio
  └── api-v3 (0.0.0.0:8002)
        ├── ddp-broker-py [localhost:8002]          ← also on Mac Studio
        └── WireGuard VPN (10.0.0.8:8002)
              ├── ddp-sync  [10.0.0.8:8002]         ← on EC2
              └── votebot   [10.0.0.8:8002]         ← on EC2
```

The cutover is a single env-var flip per service. EC2 services already reach the Mac Studio over the existing WireGuard tunnel — no new infrastructure needed.

---

## 4. Infrastructure Map

### Ports (no conflicts)

| Service | Port | Status |
|---|---|---|
| CAMS API | 8000 | Existing |
| ddp-sync | 8001 | Existing |
| **os-api shim** | **8002** | **New** |
| PostgreSQL | 5432 | Existing (shared) |
| Redis | 6379 | Existing (shared) |
| Ollama | 11434 | Existing |
| Playwright CDP | 9222 | Existing |

### Databases (all on localhost:5432)

| Database | User | Owner | Notes |
|---|---|---|---|
| `cams` | `cams` | CAMS / ddp-agents | Existing, do not touch |
| `broker` | (broker user) | ddp-broker-py | Existing, do not touch |
| **`openstates`** | **`openstates`** | **os-api shim, os-update CLI** | **New** |

### Redis Keys

| Namespace | Database | Owner |
|---|---|---|
| `cams:*`, `queue:*`, `subtask:*` | `/0` | CAMS / ddp-agents |
| `ddp:*`, `votebot:*` | `/0` | ddp-sync / votebot |
| **`os:*`** | **`/1`** | **os-api shim (if caching needed)** |

The os-api shim is stateless; it queries the openstates PostgreSQL directly. Redis `/1` is reserved but not required initially.

### Log Files

| Service | Log path |
|---|---|
| CAMS | `logs/cams-server.log` |
| ddp-sync | systemd journal (EC2) |
| **os-scraper launchd** | **`~/Developer/repos/ddp-open-states/logs/scraper.log`** |
| **os-api shim** | **`~/Developer/repos/ddp-open-states/logs/os-api.log`** |

---

## 5. Phase 1: OpenStates Database & Core Installation

### 1.1 Create the openstates PostgreSQL database

The existing CAMS Docker container runs `postgres:16`. Create a new database and user within it.

```bash
# Connect to the existing container
docker exec -it ddp-agents-postgres-1 psql -U postgres

-- Inside psql:
CREATE USER openstates WITH PASSWORD '<LOCAL_DEV_DB_PASSWORD>';
CREATE DATABASE openstates OWNER openstates;
GRANT ALL PRIVILEGES ON DATABASE openstates TO openstates;
\q
```

Set `DATABASE_URL` for all openstates-core operations:
```bash
export DATABASE_URL="postgresql://openstates:<LOCAL_DEV_DB_PASSWORD>@localhost:5432/openstates"
```

**PostGIS note:** openstates-core's README uses `postgis://` in DATABASE_URL, but none of its models use spatial fields (no `PointField`, `PolygonField`, `GeometryField`). The `postgis://` prefix activates Django's PostGIS backend, which is unnecessary here. Use the plain `postgresql://` prefix with `django.db.backends.postgresql` in Django settings. If migrations fail with a PostGIS-related error, install `postgis` extension in the container: `CREATE EXTENSION IF NOT EXISTS postgis;` and switch to `postgis://`.

### 1.2 Install openstates-core

```bash
cd ~/Developer/repos/ddp-open-states/openstates-core

# Install with Poetry (already cloned)
poetry install

# Verify CLI commands are available
poetry run os-initdb --help
poetry run os-update --help
poetry run os-people --help
```

### 1.3 Configure openstates-core settings

openstates-core reads `DATABASE_URL` from the environment. Create a `.env` file at the repo root:

```
# ~/Developer/repos/ddp-open-states/openstates-core/.env
DATABASE_URL=postgresql://openstates:<LOCAL_DEV_DB_PASSWORD>@localhost:5432/openstates
SCRAPELIB_RPM=60
SCRAPED_DATA_DIR=./_data
CACHE_DIR=./_cache
```

Create a shell helper at `~/Developer/repos/ddp-open-states/activate.sh`:

```bash
#!/usr/bin/env bash
# Source this to set up the openstates environment
export DATABASE_URL="postgresql://openstates:<LOCAL_DEV_DB_PASSWORD>@localhost:5432/openstates"
export OS_PEOPLE_DIRECTORY="$HOME/Developer/repos/ddp-open-states/people"
export PYTHONPATH="/Users/agentsmith/Developer/repos/ddp-open-states/openstates-scrapers/scrapers"
export SCRAPELIB_RPM=60
export SCRAPED_DATA_DIR="$HOME/Developer/repos/ddp-open-states/openstates-scrapers/_data"
export CACHE_DIR="$HOME/Developer/repos/ddp-open-states/openstates-scrapers/_cache"
# CLI locations (installed via pip, not poetry)
export OS_INITDB="$HOME/Library/Python/3.9/bin/os-initdb"
export OS_UPDATE="$HOME/Library/Python/3.9/bin/os-update"
export OS_PEOPLE="$HOME/Library/Python/3.9/bin/os-people"
```

**Note:** openstates CLIs are at `~/Library/Python/3.9/bin/` (pip-installed, not poetry). `PYTHONPATH` must include the scrapers directory so `os-update ut` can import the `ut` module. `OS_PEOPLE_DIRECTORY` is required by `os-people to-database` (hyphen, not underscore).

### 1.4 Initialize the database schema

`os-initdb` runs Django migrations AND creates all jurisdiction/organization/post records for all 50 states + US Congress:

```bash
cd ~/Developer/repos/ddp-open-states/openstates-core
source ~/Developer/repos/ddp-open-states/activate.sh
poetry run os-initdb
```

This creates all `opencivicdata_*` tables and pre-populates:
- All `Jurisdiction` rows (state + federal)
- All `Organization` rows (legislature, upper chamber, lower chamber, executive per state)
- All `Post` rows (districts per chamber)
- All `Division` rows (OCD division IDs)

Expected runtime: 2–5 minutes. Expected tables created: ~25 (`opencivicdata_jurisdiction`, `opencivicdata_legislativesession`, `opencivicdata_bill`, `opencivicdata_billaction`, `opencivicdata_billsponsorship`, `opencivicdata_billversion`, `opencivicdata_billversionlink`, `opencivicdata_billdocument`, `opencivicdata_billabstract`, `opencivicdata_relatedbill`, `opencivicdata_voteevent`, `opencivicdata_votecount`, `opencivicdata_personvote`, `opencivicdata_organization`, `opencivicdata_membership`, `opencivicdata_person`, `opencivicdata_personidentifier`, `opencivicdata_personname`, `opencivicdata_personoffice`, `opencivicdata_post`, `opencivicdata_division`, `opencivicdata_event`, `opencivicdata_eventlocation`, `opencivicdata_searchablebill`, `openstates_personoffice`).

### 1.5 Import people (legislators) from YAML

The `people/` repo contains YAML files for all current and retired legislators. This is the authoritative source for `Person` + `Membership` records that vote-event importers resolve names against.

```bash
cd ~/Developer/repos/ddp-open-states/openstates-core
source ~/Developer/repos/ddp-open-states/activate.sh

# Import for each target state (run once; re-run to update)
for state in fl wa us va mi ma ut az al; do
    poetry run os-people to_database $state
done
```

**What this does:** Reads `~/Developer/repos/ddp-open-states/people/data/{state}/legislature/*.yaml`, creates `Person` + `PersonIdentifier` + `PersonName` + `PersonOffice` + `Membership` rows. Person rows have OCD person IDs (e.g., `ocd-person/12345abc-...`) that the vote importer uses to resolve voter names to person records.

**Important:** `os-people` only reads from the `people/` repo. Keep that repo updated (`git pull`) when roster changes (retirements, special elections).

---

## 6. Phase 2: Scraper Configuration & Bill Scoping ✓ (partial — UT 2026 + MI 2025-2026 complete)

### 2.1 Scraper installation

```bash
cd ~/Developer/repos/ddp-open-states/openstates-scrapers
poetry install
```

The scrapers depend on `openstates` (core) as a package. Poetry will install it from the local clone if configured in `pyproject.toml`, or from PyPI. Verify:

```bash
poetry run python -c "from openstates.scrape import Bill, VoteEvent; print('OK')"
```

### 2.2 Running a single-state scrape

`os-update` is the unified scrape+import command. It takes a module name matching a directory under `scrapers/`:

```bash
cd ~/Developer/repos/ddp-open-states/openstates-scrapers
source ~/Developer/repos/ddp-open-states/activate.sh

# Scrape Florida 2025 session (bills + votes)
poetry run os-update fl --scrape bills
# Output: _data/fl/bill_*.json, vote_event_*.json

# Import into local DB
poetry run os-update fl --import

# Or both in one command:
poetry run os-update fl
```

**Session argument:** By default `os-update` scrapes all active sessions. Pass `session=2025` as a scraper kwarg to restrict:

```bash
poetry run os-update fl --scrape bills session=2025
```

**Scraper-specific invocation patterns:**

| State | Command | Session kwarg | Notes |
|---|---|---|---|
| FL | `os-update fl --scrape bills session=2025` | `session=2025` | Requires `extras.session_number=98` in session metadata |
| WA | `os-update wa --scrape bills session=2025-2026` | `session=2025-2026` | Biennial — one scrape covers both years |
| US | `os-update usa --scrape bills session=119 chamber=lower` | `session=119 chamber=lower` | Module is `usa` not `us`. Run separately for `chamber=upper`. No `start=` needed — 119th Congress is 2025+ only. The `start=` date format has a bug (`%I` instead of `%M`) so don't use it. |
| VA/MI/MA/UT/AZ/AL | `os-update {state} --scrape bills` | (active session auto-detected) | Standard pattern |

### 2.3 Florida session metadata prerequisite

Florida's `FlBillScraper` requires `extras.session_number` in session metadata (used to construct House committee vote URLs). This is defined in `scrapers/fl/__init__.py`. Verify it has the current session before running:

```bash
grep -A5 '"2025"' ~/Developer/repos/ddp-open-states/openstates-scrapers/scrapers/fl/__init__.py
# Should show: "extras": {"session_number": "98"}
```

If a new year is added without `session_number`, House committee votes will be silently skipped. Update `__init__.py` with the correct session number from `flhouse.gov`.

### 2.4 Bill scope optimization (US federal only)

US federal scrapes produce ~10,000 bills per Congress. Full scrape is ~2–4 hours. Two options:

**Option A (recommended for now): Full scrape, filter on import.**

Run the full scrape but pass `start=` to only fetch bills updated since a cutoff date, reducing volume:

```bash
poetry run os-update us --scrape bills session=119 chamber=lower start="2025-01-01 00:00:00"
poetry run os-update us --scrape bills session=119 chamber=upper start="2025-01-01 00:00:00"
```

All bills land in the openstates DB. Only bills with `openstates_id` matching a tracked bill in `ddp-broker-py` (i.e., `Bill.tracked=True`) will flow through the Celery pipeline. No `ddp-broker-py` changes needed.

**Option B (future): Bill allowlist at import step.**

Create `~/Developer/repos/ddp-open-states/openstates-scrapers/scripts/import_tracked_bills.py` that:
1. Reads `tracked_bill_ids.txt` (a newline-separated list of US federal bill identifiers)
2. Calls `os-update us --import` but pre-filters the `_data/us/` directory to only include JSON files matching tracked bill identifiers before importing

This is a ~50-line script. Implement if full federal import becomes a performance problem.

### 2.5 Scraper known issues and fixes

**Superseded 2026-07-17/2026-07-25 — both repos are now formal DDP forks, not local-patch-only
checkouts, and the fix-tracking model below is stale.** `openstates-scrapers` went formal
2026-07-17 (`Digital-Democracy-Project/openstates-scrapers`) and `openstates-core` went formal
2026-07-19; the two use *different* fork models (see `PLAN-fork-management.md` §1 for the full
reasoning, and the `project-patch-convention` memory):

- **`openstates-scrapers`** — fixes merge via a normal branch → PR → the fork's own `main`, no
  cherry-picking. `apply-local-patches.sh` just does `git checkout main && git pull origin main`
  (`origin` here already **is** the DDP fork). The original UT (#5695) and MI (#5696) fixes
  described below in earlier revisions of this plan now live as normal commits on that `main`.
- **`openstates-core`** — fixes merge via branch → PR against the `cherry-pick-line` branch,
  **never `main`** (a PR opened against `main` there is a silent no-op — `main` is never read by
  anything; confirmed the hard way when `openstates-core` PR #2 was first opened against the
  wrong base, see `notes/openstates-core-cherry-pick-line-targeting-20260726.md`).
  `apply-local-patches.sh` rebuilds a throwaway `local-patches` branch every run: fresh public
  `main` (via `origin`, the public `openstates/openstates-core`) + a range-pick of everything on
  `cherry-pick-line` not yet upstream (`git cherry-pick --empty=drop
  "$(git merge-base main cherry-pick-line)..cherry-pick-line"`) — no more hand-listed individual
  commit SHAs. Add new DDP-only `openstates-core` fixes to `cherry-pick-line`; never hand-edit
  the cherry-pick list in `apply-local-patches.sh` again.
  **Bug found 2026-07-28 (PR #15, open, not yet merged):** this range-pick had been silently
  inert since the branch's creation — the script refreshed `main` every run but never fetched the
  *local* `cherry-pick-line` ref from its remote, so it sat frozen at its 2026-07-25 creation
  commit no matter what merged on GitHub afterward. Two PRs (#1, #2) merged into `cherry-pick-line`
  on GitHub during that window without ever actually reaching a real scrape — see §8.1a for the
  concrete impact. PR #15 adds the missing `git fetch ddp cherry-pick-line && git branch -f
  cherry-pick-line ddp/cherry-pick-line` step, plus `-m 1` on the cherry-pick so ordinary merge
  commits on `cherry-pick-line` don't crash the rebuild. Until #15 merges and a real
  `apply-local-patches.sh` run confirms it, don't assume a GitHub-merged `openstates-core` PR is
  actually live.
- Both refresh steps skip themselves (rather than mutate the tree) if a scrape is currently
  running, tracked via PID markers in `/tmp/ddp-openstates-scrapes`.

**MI pagination duplicates** (issue #5697, not yet fixed upstream as of last check): The MI
scraper produces duplicate bill JSON files due to pagination overlap. Workaround:
`--allow_duplicates` flag on import. `run-scrape.sh` handles this automatically for `mi`.

**CLIs are at `~/Library/Python/3.9/bin/`** (pip-installed, not poetry). `PYTHONPATH` must include the `scrapers/` directory. Both are set in `activate.sh`.

### 2.6 Incremental scraping's per-bill network floor (WA/UT/AZ/VA)

**Moved to `PLAN-incremental-scraping.md`.** Why a routine WA scrape takes ~70 minutes even
during an out-of-session week (a hard per-bill network floor that "incremental" scraping doesn't
remove for WA/UT/AZ, and only partially removes for VA) is a property of the incremental-scraping
implementation itself, not this plan — see **"Reopened 2026-07-27: the per-bill network floor
(WA/UT/AZ), plus two unclosed follow-ups"** in `PLAN-incremental-scraping.md` for the full
write-up, the per-jurisdiction table, and the still-open follow-ups (WA's unchecked WSDL upgrade
path, MI's unverified date-signal semantics).

---

## 7. Phase 3: Run api-v3 Locally ✓

### 7.1 What api-v3 is

`~/Developer/repos/ddp-open-states/api-v3` is the actual OpenStates REST API codebase — FastAPI + SQLAlchemy, already serving the exact `/bills`, `/people`, `/jurisdictions` endpoints in the exact v3 JSON format that `ddp-broker-py`, `ddp-sync`, and `votebot` already parse. Running it locally against our local `openstates` DB is the entire "local API shim." No custom code needed.

Endpoints it provides (from `api/bills.py`, `api/people.py`, `api/jurisdictions.py`):
- `GET /bills` — list/filter with `?jurisdiction=`, `?session=`, `?identifier=`, `?include=`
- `GET /bills/{jurisdiction}/{session}/{bill_id}` — single bill lookup
- `GET /people` — list/filter with `?jurisdiction=`, `?org_classification=`, `?include=`
- `GET /people/{person_id}` — single person lookup
- `GET /jurisdictions/{jurisdiction}` — jurisdiction detail with `?include=legislative_sessions`

This is everything all three services need.

### 7.2 Installation

```bash
cd ~/Developer/repos/ddp-open-states/api-v3
poetry install
```

### 7.3 API key setup

api-v3 stores API keys in a `Profile` model in the openstates DB. `ddp-broker-py`'s `openstates_client.py::authenticate()` validates the configured key locally using `uuid.UUID(key)` — **the key must be a valid UUID format**. Create a profile row with a UUID key:

```bash
docker exec -it ddp-agents-postgres-1 psql -U openstates -d openstates <<'EOF'
-- Create a minimal auth_user (required FK for Profile)
INSERT INTO auth_user (username, email, password, is_superuser, is_staff, is_active, date_joined, first_name, last_name)
VALUES ('local', 'local@ddp.local', '', false, false, true, NOW(), '', '')
ON CONFLICT DO NOTHING;

-- Create Profile with a fixed UUID API key
INSERT INTO openstates_profile (user_id, api_key, api_tier, api_tier_expires, num_requests_today, num_requests_current_month)
SELECT id, '00000000-0000-0000-0000-000000000001', 'default', NULL, 0, 0
FROM auth_user WHERE username = 'local'
ON CONFLICT DO NOTHING;
EOF
```

Then set this key in all three services:
```
OPENSTATES_API_KEY=00000000-0000-0000-0000-000000000001
```

**Note:** If the `auth_user` or `openstates_profile` tables don't exist after `os-initdb`, check the api-v3 migrations. api-v3 uses its own Django auth tables (from `openstates.org`) which `os-initdb` doesn't run. Alternative: disable auth in api-v3 for local use by setting `OPENSTATES_ALLOW_UNAUTHENTICATED=true` if that env var exists, or comment out the auth dependency in `api/auth.py` for local dev.

### 7.4 Startup

Create `~/Developer/repos/ddp-open-states/start-os-api.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/Users/agentsmith/Developer/repos/ddp-open-states"
VENV="$PROJECT_DIR/api-v3/.venv/bin"
LOG_PREFIX="[start-os-api]"

log() { echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ') $LOG_PREFIX $*"; }

# Load environment
if [ -f "$PROJECT_DIR/api-v3/.env" ]; then
    set -a; source "$PROJECT_DIR/api-v3/.env"; set +a
fi

# Wait for Postgres (same container as CAMS)
wait_for_postgres() {
    local attempts=0
    while ! docker exec ddp-agents-postgres-1 pg_isready -U openstates >/dev/null 2>&1; do
        attempts=$((attempts + 1))
        [ $attempts -ge 30 ] && { log "ERROR: PostgreSQL not ready"; exit 1; }
        sleep 1
    done
    log "PostgreSQL is healthy"
}

wait_for_postgres

log "Launching api-v3 on :8002"
exec "$VENV/uvicorn" api.main:app \
    --host 0.0.0.0 \
    --port 8002
```

Note `--host 0.0.0.0` — needed so EC2 services can reach api-v3 over the WireGuard VPN (Mac Studio is `10.0.0.8` on the tunnel). Port 8002 is not exposed to the public internet; WireGuard acts as the firewall. `exec` replaces the shell so launchd tracks the uvicorn process directly and restarts it immediately on exit. No `--workers` flag — matches the CAMS pattern.

Create `~/Library/LaunchAgents/com.ddp.openstates-api.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ddp.openstates-api</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/agentsmith/Developer/repos/ddp-open-states/start-os-api.sh</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/agentsmith/Developer/repos/ddp-open-states/api-v3</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>DATABASE_URL</key>
        <string>postgresql://openstates:<LOCAL_DEV_DB_PASSWORD>@localhost:5432/openstates</string>
        <key>REDIS_URL</key>
        <string>redis://localhost:6379/1</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ThrottleInterval</key>
    <integer>5</integer>
    <key>StandardOutPath</key>
    <string>/Users/agentsmith/Developer/repos/ddp-open-states/logs/os-api.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/agentsmith/Developer/repos/ddp-open-states/logs/os-api.log</string>
</dict>
</plist>
```

Register: `launchctl load ~/Library/LaunchAgents/com.ddp.openstates-api.plist`

### 7.5 Rate limiting

api-v3 has Redis-backed rate limiting. Locally this is a non-issue — configure it to allow unlimited requests by setting a very high tier limit in the Profile row, or disable the rate limiter via env if the option exists. Check `api/rate_limiter.py` for a kill-switch env var.

---

## 8. Phase 4: Future Cutover (not in scope for this plan)

Document here so the work is scoped when the time comes. Do not execute until the shadow pipeline has run reliably for several weeks.

> **Update 2026-07-21 — ddp-broker-py's cutover already happened, via a different mechanism
> than §8.2/8.3/10.3 below describe.** Those sections assume a single `OPENSTATES_API_BASE`
> env-var flip straight to the Mac Studio. What was actually built instead: `ddp-api` proxies
> `/openstates/*` over WireGuard with a read-scoped bearer token (`DDP_OPENSTATES_BEARER_TOKEN`
> + `DDP_OPENSTATES_API_ROOT=https://api.digitaldemocracyproject.org/openstates`), and
> ddp-broker-py's own `_get_client_for_jurisdiction()` (`openstates_service.py`) routes
> per-jurisdiction based on `DDP_OPENSTATES_JURISDICTIONS` (comma-separated ISO2 codes) —
> everything else still hits real OpenStates. This is a **gradual, per-jurisdiction** cutover,
> not the one-shot flip this section was written for. As of 2026-07-21 the local checkout's
> `.env` shows `DDP_OPENSTATES_JURISDICTIONS=US,FL,MI,AZ,VA,WA,UT` — **7 of 8 tracked
> jurisdictions already routed to the replica; only MA remains.** §8.2 and §10.3 are superseded
> for ddp-broker-py (kept below for ddp-sync/votebot, which still use the original
> WireGuard-direct design). See §8.1a for what's actually left.
>
> **Correction (2026-07-23) — the line above describes the local checkout's config, not what's
> live in prod.** Confirmed directly with Ramon (see `project_openstates_fork_readiness` memory):
> **production is still running the code default, `DDP_OPENSTATES_JURISDICTIONS=UT,MI` only.**
> The gradual per-jurisdiction cutover has not actually started beyond the two canary
> jurisdictions. The hold is explicitly tied to confidence in the FL 2024 historical backfill
> (§8.1a below) — which as of today is still actively failing, not close to done — so this is
> unlikely to move soon. Correct "7 of 8 tracked jurisdictions already routed" above before
> anyone reads it as prod state.
>
> **Confirmed critical bug in this Mac's api-v3 instance, prod impact unverified (2026-07-28) —
> corrected 2026-07-28 PM review pass: the severity below originally overstated this as
> "prod has likely been served stale data"; that part is still unconfirmed, not established.**
> What IS confirmed: this Mac's `api-v3` container has been connected to the wrong, frozen
> 2026-06-24 Postgres snapshot since it was created — see the first item in §8.1a for the full
> diagnosis. Found while investigating what looked like two separate api-v3 bugs (MA votes
> always empty, FL's whole 2023 session unreachable); both turned out to be this one root cause,
> a Docker networking misconfiguration, not separate data-quality issues. **What is NOT yet
> confirmed:** whether prod's `UT,MI` canary traffic (routed through `ddp-api`'s proxy to this
> same Mac Studio `:8002`) has actually been affected — that depends on whether those two
> jurisdictions are really live in prod (itself only "believed," not verified, per the
> 2026-07-23 correction above) and needs its own explicit check, not assumed from this bug alone.
> Confirmed, unconditional impact: **any confidence built on api-v3 responses on this Mac since
> 2026-06-24 — local validation, the parallel diffs in §10.2, anything — was unknowingly checked
> against stale data.** Note that most of this session's own validation work (org/person-
> resolution counts, bill/session tallies, etc.) queried the Postgres DB directly, not through
> api-v3, and is unaffected by this specific bug — only checks that went through `:8002` are in
> question. Re-verify anything that specifically used the local api-v3 endpoint after the fix
> below lands.

### 8.1 Prerequisites before cutover

- Shadow scrapes have run nightly for ≥ 4 weeks with no silent gaps
- Parallel validation (§10.2) has passed, **per jurisdiction, before that jurisdiction is added**
  — **corrected 2026-07-28 (2nd PM review pass): rewritten from a single "all 8 jurisdictions"
  gate**, which no longer matches the staged rollout in the deploy-gap item below (jurisdictions
  are added to `DDP_OPENSTATES_JURISDICTIONS` incrementally as each one's own validation/repair
  closes, not all at once). The 8 tracked jurisdictions are FL/WA/US/VA/MI/MA/UT/AZ; AL is
  explicitly untracked per §2 and was never part of this count.
- Session alias mapping resolved (see below)
- pg_dump backup confirmed working

### 8.1a ddp-broker-py remaining blockers (found 2026-07-21)

- [ ] **CRITICAL — api-v3 has been serving a Postgres snapshot frozen 2026-06-24, not the live
      replica, since the container was created. Root cause found and fix scoped 2026-07-28;
      not yet applied.** Discovered while running the MA vote-data validation below: MA bills
      resolved correctly via `api-v3` but `votes` always came back empty even for bills with
      confirmed vote data in the DB (`H 4240`: 16 vote events; `H 58`: 2). A second, seemingly
      unrelated symptom — FL's entire 2023 session (1,828 bills, the recently-completed
      historical backfill) returning **zero** results from `/bills?jurisdiction=fl&session=2023`
      with no identifier filter at all — turned out to be **the same bug**, not a second one.

      **Root cause, traced precisely:** `deploy/docker-compose.ddp.yml`'s `api` service is
      attached to two Docker networks — this project's own `default` network (where the
      `postgres` service, container `ddp-openstates-postgres-1`, actually lives) and the
      external `ddp-agents_default` network (needed only to reach `ddp-agents-redis-1` for the
      rate limiter). `DATABASE_URL` uses the bare hostname `postgres` — but CAMS's own
      docker-compose project *also* has a service aliased `postgres` (container
      `ddp-agents-postgres-1`) reachable on `ddp-agents_default`. Since the `api` container sits
      on both networks, Docker's embedded DNS resolves the ambiguous `postgres` hostname to
      **whichever network's alias wins** — confirmed via `socket.gethostbyname('postgres')`
      *from inside the running `ddp-openstates-api-1` container*: it resolves to CAMS's Postgres
      (`172.18.0.4`), not the dedicated one (`172.20.0.2`). Confirmed directly: CAMS's own
      `ddp-agents-postgres-1` has a database literally named `openstates` with exactly the same
      row counts as what `api-v3` has been serving (41,829 bills, `max(updated_at) = 2026-06-24
      03:01:42`) — this is the **old, pre-migration copy** `PLAN-production-hardening.md`'s WS0b
      explicitly kept around for a soak period before decommissioning (never decommissioned).
      `ddp-openstates-api-1` was created `2026-06-24T21:56:40Z` — matching the freeze almost to
      the hour, meaning **this has been broken since the container's very first boot**, not a
      recent regression. The dedicated `ddp-openstates-postgres-1` (correct, live, host port
      5433) has 71,800 bills and does contain the MA votes and FL 2023 session data that were
      "missing" — this was never a data or scraper problem.

      **Why the fix is small, and where the correct pattern already exists in the same file:**
      the same compose file's Redis config already avoids this exact ambiguity —
      `RRL_REDIS_HOST: "ddp-agents-redis-1"` uses the specific, globally-unique container name
      rather than a generic service alias, precisely because it also needs to reach across
      networks. The `DATABASE_URL` line just never got the same treatment. Fix is one line:
      ```yaml
      # deploy/docker-compose.ddp.yml, api service:
      # before:
      DATABASE_URL: "postgresql://openstates:openstates_dev@postgres:5432/openstates"
      # after:
      DATABASE_URL: "postgresql://openstates:openstates_dev@ddp-openstates-postgres-1:5432/openstates"
      ```
      Then recreate the `api` container (`docker-compose -f deploy/docker-compose.ddp.yml up -d
      --force-recreate api`) and confirm via the same `socket.gethostbyname`/row-count checks
      used to diagnose this that it now resolves to `ddp-openstates-postgres-1`. No changes
      needed to `openstates-network`, no service restructuring, no touching CAMS's compose
      project at all — just qualifying one hostname to the one that's already unique.

      **On the target hostname's stability (2026-07-28, PM review):** `ddp-openstates-postgres-1`
      is an explicit `container_name:` set directly in `docker-compose.ddp.yml`, not a name
      auto-generated from the Compose project directory or `COMPOSE_PROJECT_NAME` — so unlike a
      derived name, it won't silently change if the repo is moved or Compose is invoked
      differently. No extra network-alias config needed beyond what's already there.

      **Acceptance checklist for this fix (added 2026-07-28, PM review):**
      - [ ] `docker exec ddp-openstates-api-1 python3 -c "import socket;
            print(socket.gethostbyname('ddp-openstates-postgres-1'))"` resolves to
            `ddp-openstates-postgres-1`'s actual IP on the `default` network (currently
            `172.20.0.2`), not the CAMS one.
      - [ ] Bill count from inside the container now matches the dedicated DB (~71,800+, not
            41,829) and `max(updated_at)` is recent, not frozen at `2026-06-24`.
      - [ ] `GET /bills?jurisdiction=ma&session=194th&identifier=H4240&include=votes` returns 16
            vote events (not 0).
      - [ ] `GET /bills?jurisdiction=fl&session=2023&identifier=HB1285` returns the bill (not
            zero results).
      - [ ] **Separately, not blocking this fix:** verify whether prod's actual `UT,MI` canary
            traffic (if truly live — still only "believed," see the correction above) was
            affected, using the same kind of check as the other deploy-gap item's validation
            step. This is a distinct, not-yet-done action — the local fix above doesn't by
            itself confirm or resolve prod impact.

      **Rollback:** revert the one `DATABASE_URL` line and re-run the same `--force-recreate`
      command. Since the container has been pointed at the *wrong* DB this whole time, "rollback"
      here only restores prior (broken) behavior — there's no data-correctness reason to revert,
      only an availability one if the new connection somehow fails.
- [ ] **Missing `bulk_dataexport` table causes a 500 on every `/jurisdictions/{state}?include=
      legislative_sessions` call — found 2026-07-28 while investigating the item above, unrelated
      to the stale-database bug.** `os-initdb` never creates this table (confirmed: `relation
      "bulk_dataexport" does not exist`, from the container's own traceback), but api-v3's
      jurisdiction-detail endpoint unconditionally queries it via a `selectinload` on
      `LegislativeSession` → `BulkDataExport`. This affects every jurisdiction, not just FL —
      it's a schema/migration gap, not a data problem. **Right-sized fix (guarding against
      over-building an unused feature):** DDP has no use for bulk CSV data export — the
      `os-initdb`/`os-update` pipeline this plan is built around never produces or needs
      `BulkDataExport` rows. Rather than adding a migration to create and maintain an entirely
      unused table (real ongoing surface: schema drift risk, more to keep in sync with upstream),
      the smaller, right-sized fix is to stop eagerly loading it when it isn't needed: change the
      jurisdiction-detail endpoint's `legislative_sessions` include to `noload` (or drop) the
      `BulkDataExport` relationship rather than `selectinload` it, matching the pattern this same
      codebase already uses elsewhere (`Pagination.select_or_noload()`) to skip relationships
      that aren't requested. This is an `api-v3` code change, and `api-v3` is currently a plain,
      unmodified upstream checkout with no fork/patch mechanism (see §8.3's session-alias
      decision) — so landing this fix durably needs the same prerequisite noted there: `api-v3`
      would need to become a fourth formal DDP fork (or gain some other local-patch mechanism)
      before a fix like this survives a future `git pull`. Not yet scoped further — this is a
      small, contained code fix once that prerequisite is decided.

      **Confirmed 2026-07-28 (PM review) — this is the only touchpoint; no other endpoint can
      hit the missing table.** Grepped `api-v3` for every reference to `BulkDataExport`/
      `bulk_dataexport`: the model definition itself (`api/db/models/jurisdiction.py`), and
      exactly one usage — `LegislativeSession.downloads` (the actual relationship attribute
      name) in `JurisdictionPagination.include_map_overrides`'s
      `["legislative_sessions", "legislative_sessions.downloads"]` entry
      (`api/jurisdictions.py`). Nothing else in the codebase touches it. **Expected behavior
      after the fix:** `GET /jurisdictions/{state}?include=legislative_sessions` should return
      each session without a `downloads`/bulk-export field at all (same as today for any
      `include=` that isn't requested) — this is a pure bug fix restoring the endpoint to
      working, not a behavior change any current caller depends on, since the endpoint 500s for
      every jurisdiction today and so has no working callers to preserve compatibility with.
- [ ] **MA vote-data validation.** MA is the only jurisdiction still excluded from the *local
      checkout's target* `DDP_OPENSTATES_JURISDICTIONS` list (**clarified 2026-07-28, 2nd PM
      review pass, to avoid the same local-vs-prod ambiguity flagged elsewhere in this
      section** — prod itself is still `UT,MI` only, per the deploy-gap item below; this bullet
      is about local validation readiness, not prod exposure). The replica has 45 vote events
      across 10,959 MA bills,
      matching the motion-classifier's known total (RUNBOOK "Motion classification"), so the
      scraper itself works — but the formal §10.2 parallel diff against live
      `v3.openstates.org` hasn't been run/recorded for MA specifically. Run it, then add `MA`
      to the jurisdictions list.

      **Scoped 2026-07-28 — concrete bills to use for the diff.** Queried the local replica for
      real MA bills with vote data to use, following the same pattern as §10.2's FL HB1 example:

      ```bash
      # Primary case — H 4240 (194th session), 16 vote events, the most vote-heavy MA bill
      # in the replica, good stress test for motion_text/counts/individual-vote parsing:
      curl "http://localhost:8002/bills?jurisdiction=ma&session=194th&identifier=H4240&include=votes,actions,sponsorships" \
        | jq . > local_ma_h4240.json
      curl "https://v3.openstates.org/bills?jurisdiction=ma&session=194th&identifier=H4240&include=votes,actions,sponsorships&apikey=$OPENSTATES_API_KEY" \
        | jq . > live_ma_h4240.json
      diff local_ma_h4240.json live_ma_h4240.json

      # Secondary case — H 58 (194th session), 2 vote events, simpler bill for a sanity check
      curl "http://localhost:8002/bills?jurisdiction=ma&session=194th&identifier=H58&include=votes,actions,sponsorships" \
        | jq . > local_ma_h58.json
      curl "https://v3.openstates.org/bills?jurisdiction=ma&session=194th&identifier=H58&include=votes,actions,sponsorships&apikey=$OPENSTATES_API_KEY" \
        | jq . > live_ma_h58.json
      diff local_ma_h58.json live_ma_h58.json
      ```

      Check the same fields §10.2 already lists (motion_text, vote counts, individual votes,
      sponsorships, people's name/district/division_id). If both diff clean, MA is validated —
      run the checklist add-to-`DDP_OPENSTATES_JURISDICTIONS` step next (see item 1 above, which
      found that step itself has no documented deploy path yet on the actual prod host — MA's
      addition is blocked on the same prerequisite, not just its own validation).
- [x] **`openstates-core`'s `apply-local-patches.sh` tooling gap — FIXED 2026-07-21 (commit
      `af9ad95` on `phase1-bill-provenance`).** `openstates-core` sits on `phase1-bill-provenance`, which per
      `ddp-infra/PLAN-bill-document-provenance.md` is **intentionally held back** — its
      bill-document-archive feature is fully built but deliberately kept off the live checkout
      until a rollout/scheduling design exists, specifically because a first-ever run per
      jurisdiction would fire ~9,800+ PDF fetches at once with no sequencing built yet (verified
      live against FL, then deliberately killed before it reached all ~3,900 bills). **That hold
      is correct and should stay.** The actual bug is narrower: on top of the held branch,
      `openstates-core` also has *uncommitted* WIP (`text_extract.py`, `bill.py`, an untracked
      migration), which would have broken `apply-local-patches.sh`'s unrelated `git checkout
      main` step for the nightly `openstates_patch_refresh` job (which applies the
      actually-live `d6653a5` CACHE_DIR/SCRAPED_DATA_DIR patch). **Checked 2026-07-21, corrected
      from an earlier overstated claim:** the job had NOT actually failed as of this fix — its
      last completed run (2026-07-20 21:00 EDT) succeeded, and the uncommitted changes only
      appeared a couple hours afterward that same evening, so it was only a risk for the next
      run, not a confirmed past failure. No Slack alert is wired for this job either way, which
      is why this was worth fixing rather than relying on luck. **Resolved:** the loose changes
      were only the smaller "compare each version's text against the one before it" add-on —
      the bulk of the archive feature was already safely saved in an earlier commit. Committed
      the add-on to `phase1-bill-provenance` (preserving the hold; `openstates-core`'s tracked
      files are clean again). The hold itself was not touched.

      **Update 2026-07-26/27 — the hold was lifted; Phase 1 archiving is now live, gated
      per-jurisdiction.** `run-scrape.sh` now calls `archive_if_enabled()` after every scrape
      (scrape or no-op), gated by `ARCHIVE_ENABLED_STATES` in `activate.sh` — currently set to
      `fl` only, so the "fire ~9,800+ PDF fetches at once with no sequencing" risk this hold
      existed to prevent is scoped to one jurisdiction at a time by design, not solved generally.
      A full FL archive run completed 2026-07-26 (`logs/fl-full-archive-20260726.log`): 7,685
      bills checked, 19,521 documents fetched/archived, **499 fetch errors** (all unretried HTTP
      429s — see the correction below), 1 extract error, 0 conflicts, all 19,521 successfully
      fetched documents verified in S3. Since the original hold was written,
      `apply-local-patches.sh` also stopped hand-listing individual cherry-picked commits for
      `openstates-core` — it now range-picks everything on the `cherry-pick-line` branch not yet
      upstream (`PLAN-fork-management.md` §1, recommendation H); see §2.5/§11.4 below, updated to
      match. Extending `ARCHIVE_ENABLED_STATES` beyond `fl` is future work, not yet scheduled.

      **Correction 2026-07-28 — the archive-downloader retry-settings fix (PR #1) and the OPEN-2
      vote-person fix (PR #2) both merged on GitHub 2026-07-26 but neither was actually live in
      production, because `apply-local-patches.sh` never synced the *local* `cherry-pick-line`
      ref from its remote — it only ever refreshed `main`.** The local ref had been frozen at its
      2026-07-25 creation commit the whole time, so every nightly `local-patches` rebuild silently
      kept using the old, unpatched code regardless of what merged on GitHub. This is exactly why
      the FL full-archive run above logged 499 unretried 429s: `scraper.retry_attempts` was still
      scrapelib's bare default of `0`, not the `5` PR #1 was supposed to set. Found investigating
      those 499 errors; a second bug surfaced while fixing the first — once `cherry-pick-line` is
      actually synced, its history contains ordinary GitHub merge commits, which `git
      cherry-pick`'s range-pick can't replay without `-m 1`, which would crash the whole nightly
      rebuild the next time any PR merges into that branch normally. **Both fixes shipped in
      `ddp-open-states` PR #15 (`fix/apply-local-patches-sync-cherry-pick-line`), merged
      2026-07-28 during a confirmed quiet window (no scrape running).**

      **Confirmed live 2026-07-28:** ran `apply-local-patches.sh` for real after the merge —
      `local-patches` now includes both PR #1 (retry settings) and PR #2 (OPEN-2 vote-person
      resolution), and `openstates-core/openstates/cli/text_extract.py` shows
      `scraper.retry_attempts = 5` / `retry_wait_seconds = 5` as expected. Also re-ran
      `os-text-extract archive fl` (no `--session`) to sweep up the ~499 documents that failed
      with unretried 429s during the 2026-07-26 run; the natural-key check correctly skipped
      everything already archived and only re-fetched the previously-failed ones. **Both fixes
      are genuinely live now — the "not yet live" caveat below no longer applies.**
- [ ] **US federal vote-person resolution gap (OPEN-2) — separate from the FL/MA org-resolution
      gap above. Fix confirmed live in production as of 2026-07-28. The one-time backfill for
      already-scraped rows is the only remaining step.** Distinct issue: ~27.6% of US
      Congress person-vote rows (147,473 of 534,522, across 1,535 roll calls) had a null
      `voter_id` because same-surname legislators (three different Garcias, three different
      Carters, etc.) couldn't be disambiguated by name-matching alone, even though the House
      Clerk's own XML already provides a stable bioguide/LIS identifier for exactly this purpose
      — our scraper extracted it but only ever passed it through as an inert `note=` string (see
      `notes/votebot-unknown-vote-party-breakdown-20260726.md`). VoteBot itself has no bug; it
      just faithfully displays whatever party OpenStates returns. Fixed across three repos:
      `openstates-core` (`VoteEvent.vote()` now accepts `id=`, `resolve_person()` tries an
      identifier match before falling back to name-matching — PR #2, merged to `cherry-pick-line`
      on GitHub, **not** `main`, per the fork's convention, see
      `notes/openstates-core-cherry-pick-line-targeting-20260726.md` — **confirmed applied to a
      real `local-patches` build 2026-07-28**, see the correction above), `openstates-scrapers`
      (`scrapers/usa/votes.py` now passes `id=bioguide`/`id=lis_id` — PR #8, fork `main`, also
      live), and `ddp-open-states` (`backfill-vote-person-resolution.py`, PR #12, `main` —
      re-resolves already-scraped null-`voter_id` rows without re-scraping, and doesn't depend on
      `local-patches` at all since it works directly off the `note` column already sitting in the
      DB). `--dry-run` against the real local DB shows 144,340 of 147,473 (97.9%) would resolve;
      the remaining ~3,100 have no matching identifier (e.g. former members not in `people/`) and
      are left alone. **The backfill script has not been run for real yet** — it mutates the
      production Postgres DB, so that's an explicit separate action, now the only thing left open
      on this item since the code fix itself is confirmed live for new scrapes going forward.

      **Before running it for real (added 2026-07-28, PM review; extended in the 2nd pass to
      make the dump actually durable and verified):** take a `pg_dump` of the `openstates` DB
      first — this is a one-time bulk write against `opencivicdata_personvote`, and a plain
      pre-run dump is the simplest possible undo path if some rows resolve to the wrong person.
      **Copy it out of the container immediately** (a dump left inside `/tmp` in the container
      doesn't survive the container being recreated or cleaned up — see the same class of
      concern already raised for the broker EC2 deploy above) and **verify it's a valid,
      restorable dump** with `pg_restore --list` before proceeding:
      ```bash
      DUMP_NAME="openstates-pre-backfill-$(date +%Y%m%d).dump"
      DUMP_PATH="$HOME/Developer/repos/ddp-open-states/logs/db-backups/$DUMP_NAME"
      docker exec ddp-agents-postgres-1 pg_dump -U openstates -d openstates -Fc -f "/tmp/$DUMP_NAME"
      docker cp "ddp-agents-postgres-1:/tmp/$DUMP_NAME" "$DUMP_PATH"
      pg_restore --list "$DUMP_PATH" | head -5
      # Restore procedure, if ever needed (fixed 2026-07-28, 3rd PM review pass -- the earlier
      # draft redirected from the bare filename, not the durable path it was actually copied to):
      # first stop anything that could write to the DB concurrently with the restore (the
      # nightly scrape/import via launchd, and api-v3 if it's running), then:
      #   docker exec -i ddp-agents-postgres-1 pg_restore -U openstates -d openstates --clean --if-exists < "$DUMP_PATH"
      ```
- [x] **UT has zero bill-version/document links — found 2026-07-28, root cause corrected same
      day, fixed via `openstates-scrapers` PR #10.** Running `os-text-extract archive ut` (the
      very first attempt to archive anything for UT) completed cleanly but fetched **nothing**:
      1,021 bills checked, 0 fetched/skipped/archived. Confirmed via direct DB query: **0**
      `BillVersionLink`/`BillDocumentLink` rows exist for Utah — and, checked more thoroughly
      later the same day, **0** actions and **0** sponsorships too, across all 1,021 bills.

      **The diagnosis below (kept for context) was wrong — corrected 2026-07-28, same day, after
      actually running the scraper live against real data.** `scrape_bill_details_from_api()`
      does call `add_version_link()`/`add_document_link()`, and has since well before this
      session (public upstream, 2025-10-30) — running it directly against a real live UT bill
      produced correct versions and documents. **The real bug:** an incremental-scraping
      optimization added 2026-06-30 (`2c1d7a0d`, `start=` filtering) makes
      `scrape_bill_details_from_api()` return early — skipping all enrichment — when a bill's
      last action predates the scrape's cutoff. But `scrape_bill()` still unconditionally
      yielded the (now-empty) bill afterward. `openstates-core`'s importer treats "the new
      scrape found zero of these related items" as "delete whatever's already in the database"
      for that bill. Net effect: every incremental UT run since 2026-06-30 has been silently
      deleting each *unchanged* bill's already-good versions/documents/actions/sponsorships,
      which is why the DB now shows zero across the board despite a clean full scrape having
      populated all of it correctly on 2026-06-14 (before the `start=` feature existed).
      **Fixed:** `openstates-scrapers` PR #10 — the skip case now signals back to `scrape_bill()`
      (via `yield from`'s captured return value) so it returns before ever yielding the bare
      bill, leaving existing data alone. Verified live: the skip path now yields nothing; the
      normal path still populates versions/documents exactly as before.

      **Still needed, not yet done:** once PR #10 is merged and synced to production, UT needs a
      **fresh full scrape** (not just an incremental one) to actually repopulate the data this
      bug already deleted — an incremental run alone won't backfill bills whose last action is
      older than any future cutoff. Re-run `os-text-extract archive ut` afterward to confirm it
      now finds and archives real documents, matching AZ/FL's clean results.

      **Original (partially superseded) diagnosis, kept for its still-useful history:**

      **The likely connection to why UT/MI are the two jurisdictions already loaded from our
      fork in prod today:** this plan's own Motivation section (top of document) cites "Two bugs
      (UT #5695, MI #5696) went unnoticed until we filed PRs ourselves" as the founding reason
      DDP built this whole local-replica project — and `DDP_OPENSTATES_JURISDICTIONS`'s prod
      code-default is, not coincidentally, exactly those same two states (`UT,MI`). Re-read
      `openstates-scrapers` PR #5695 directly (commit `5e345a2d0`, "UT: fix votes not scraped for
      2025+ sessions"): before that fix, the call site was
      `self.scrape_bill_details_from_api(bill, url, session_slug)` — a **plain function call on a
      generator, with no `yield from` and no iteration at all**. Since Python generator bodies
      don't execute a single line until iterated, this means **absolutely nothing** in that
      function ran for any 2025+ UT bill before the fix — not just votes, but sponsors, actions,
      *and* whatever version/document handling might have existed — it was all silently inert.
      The fix added `yield from`, which correctly restored sponsors/actions/votes (all of which
      the fix's own commit message describes the function as already "handling"). But
      `add_version_link()`/`add_document_link()` were **never actually written into this
      function** at all, even after the fix — confirmed by grep: those calls exist only in
      `parse_bill_details_from_html()`, the legacy pre-2025 path. So the fix that made UT trustworthy
      enough to become a canary jurisdiction was real and correct for what it covered
      (votes/sponsors/actions) — but it never extended to bill text, because that capability was
      never ported to the new API-rendered code path in the first place. The gap has been sitting
      there, unnoticed, since the 2025 rendering switch, through every incremental UT scrape run
      since — this is the first time anyone tried to consume UT's version/document data (via the
      archive step) and actually noticed nothing was there.

      **Superseded by the correction above:** the claim that `add_version_link()`/
      `add_document_link()` were never written into `scrape_bill_details_from_api()` at all was
      the wrong part of this diagnosis — they were, and still are. The generator-laziness finding
      about PR #5695 above is still accurate for what it actually fixed (votes/sponsors/actions
      were truly inert before that `yield from` was added), it just doesn't explain the
      version/document gap the way this section originally assumed. See the corrected root
      cause and fix (`openstates-scrapers` PR #10) above.
- [ ] **FL vote-completeness gap from the WAF outage — corrected 2026-07-28: this was never a
      prod data-quality incident, but it IS a real, unrepaired gap in the local replica.** The
      premise in this item's original wording ("FL is already in `DDP_OPENSTATES_JURISDICTIONS`")
      was stale — it was written before, and never updated to reflect, the 2026-07-23 correction
      at the top of §8 and item 1 above: FL was never actually flipped on in prod (still
      `UT,MI` only as of the most recent check), so nothing affected by this bug ever reached a
      real consumer. The actual exposure is confined to the local shadow-scrape DB used for QA.

      **What's actually confirmed broken, with evidence:** PR #5 (the `_FLHouseWAFSource` cookie
      fix) merged 2026-07-18T03:01:02Z. FL session **`"2026"`** (the current regular session) was
      scraped full-mode 2026-06-25→06-26 — *before* the fix — hit `flhouse.gov` bot-detection
      backoffs starting 29 seconds into the run and continuing throughout (2,435 House-search
      fetches, 538 backoffs, 539 "could not find bill in House Search" errors, a ~22% loss rate)
      — and this run **was successfully imported** into the replica. **540 distinct FL bill
      numbers** hit at least one bot-detection event in that run (re-verified 2026-07-28 directly
      against `logs/scraper.log.20260714T020000Z.gz`, lines 21838-51119 — the earlier ~496/538
      estimates were close but not exact) — candidates for silently-missing House votes. Every FL
      "2026" scrape since has been an incremental no-op (0 bills changed),
      so nothing has backfilled this gap — it's been sitting unrepaired since 2026-06-26. All
      other FL sessions currently in the replica (2023/2024/2025 + specials) were scraped/backfilled
      on or after 2026-07-16, after the fix was live, and are confirmed clean per `RUNBOOK.md`.

      **Concrete steps to close this out, before FL is ever added to the prod jurisdiction list:**

      **Corrected 2026-07-28 (PM review) — validate against the actual known-affected bill list,
      not a random sample.** A generic `quality_check.py --bills 50` sample has no particular
      reason to land on the 540 bills that actually hit a WAF backoff during the bad run — it
      could easily report "clean" while missing the real gap. Extract the actual candidate list
      from the archived 2026-06-25/26 log first, then check specifically against it:
      ```bash
      cd ~/Developer/repos/ddp-open-states

      # 1. Extract the candidate bill numbers that hit a WAF backoff in the bad run. Verified
      #    2026-07-28: the correct archive is scraper.log.20260714T020000Z.gz (NOT
      #    scraper.log.20260624.gz, which predates the run and was wrongly cited in an earlier
      #    draft of this item). The bad run spans lines 21838-51119 in that archive (bounded by
      #    its own "Starting scrape: fl session=2026 (full)" / next-marker lines, same
      #    shared-log-interleaving trap as the org/person-resolution table above) — 540 distinct
      #    bill numbers confirmed, close to the ~496-538 estimated originally:
      gzcat logs/scraper.log.20260714T020000Z.gz | sed -n '21838,51119p' \
        | grep "flhouse.gov bot detection" | grep -oE "BillNumber=[0-9]+" | grep -oE "[0-9]+" \
        | sort -un > /tmp/fl-2026-waf-affected-bills.txt
      wc -l /tmp/fl-2026-waf-affected-bills.txt   # expect 540

      # 2. Targeted BEFORE count — run this same query now, before touching anything, so there's
      #    an actual before/after comparison (2nd PM review pass: the original draft only ran
      #    this after the re-scrape, which can't prove the repair changed anything). Caveat:
      #    b.identifier is stored with a chamber prefix (e.g. "HB 170"), but the extracted
      #    candidate list above is bare numbers -- matching on the numeric part alone with
      #    regexp_replace is intentionally a superset match (it can't distinguish "HB 170" from
      #    "SB 170"). That's fine for this purpose -- a superset only makes the "did the count go
      #    up" signal more conservative, never less -- but don't treat this count as an exact
      #    per-bill accounting:
      docker exec ddp-agents-postgres-1 psql -U openstates -d openstates -c "
      SELECT count(DISTINCT v.id) AS house_vote_events
      FROM opencivicdata_bill b
      JOIN opencivicdata_legislativesession ls ON b.legislative_session_id = ls.id
      JOIN opencivicdata_voteevent v ON v.bill_id = b.id
      JOIN opencivicdata_organization o ON v.organization_id = o.id
      WHERE ls.jurisdiction_id = 'ocd-jurisdiction/country:us/state:fl/government'
        AND ls.identifier = '2026' AND o.classification = 'lower'
        AND regexp_replace(b.identifier, '[^0-9]', '', 'g') = ANY(string_to_array('$(paste -sd, /tmp/fl-2026-waf-affected-bills.txt)', ','));
      "
      # Record this number before proceeding.

      # 3. The actual fix — force a full re-scrape of session 2026 (the one confirmed-bad,
      #    never-repaired session), now that the WAF fix and its retry-settings follow-up are
      #    both live:
      rm -f logs/last-run/fl_session_2026.ts   # clears the incremental cutoff so it runs full
      ./run-scrape.sh fl "session=2026"

      # 4. Re-run the exact same query from step 2 — the count should go up, not stay flat,
      #    for bills that actually had missing votes.
      docker exec ddp-agents-postgres-1 psql -U openstates -d openstates -c "
      SELECT count(DISTINCT v.id) AS house_vote_events
      FROM opencivicdata_bill b
      JOIN opencivicdata_legislativesession ls ON b.legislative_session_id = ls.id
      JOIN opencivicdata_voteevent v ON v.bill_id = b.id
      JOIN opencivicdata_organization o ON v.organization_id = o.id
      WHERE ls.jurisdiction_id = 'ocd-jurisdiction/country:us/state:fl/government'
        AND ls.identifier = '2026' AND o.classification = 'lower'
        AND regexp_replace(b.identifier, '[^0-9]', '', 'g') = ANY(string_to_array('$(paste -sd, /tmp/fl-2026-waf-affected-bills.txt)', ','));
      "

      # 5. Stronger than the aggregate count alone (2nd PM review pass): pick 2-3 specific
      #    affected bills from the candidate list and diff them against live v3.openstates.org,
      #    the same pattern already used for the MA validation above -- this actually confirms
      #    the repaired votes match live data, not just that *some* count went up.
      #    Corrected 2026-07-28 (3rd PM review pass): derive the actual bill numbers to check
      #    FROM the candidate file rather than guessing an example -- an earlier draft hardcoded
      #    "HB170" without confirming it was really one of the 540 affected bills. Check both
      #    HB/SB prefixes since the affected-bill list is bare numbers spanning both chambers:
      for num in $(head -3 /tmp/fl-2026-waf-affected-bills.txt); do
        for prefix in HB SB; do
          curl -s "http://localhost:8002/bills?jurisdiction=fl&session=2026&identifier=${prefix}${num}&include=votes,actions" \
            | jq -e '.results[0]' >/dev/null 2>&1 || continue   # skip if this prefix/number doesn't exist
          curl -s "http://localhost:8002/bills?jurisdiction=fl&session=2026&identifier=${prefix}${num}&include=votes,actions" \
            | jq . > "local_fl_${prefix}${num}.json"
          curl -s "https://v3.openstates.org/bills?jurisdiction=fl&session=2026&identifier=${prefix}${num}&include=votes,actions&apikey=$OPENSTATES_API_KEY" \
            | jq . > "live_fl_${prefix}${num}.json"
          diff "local_fl_${prefix}${num}.json" "live_fl_${prefix}${num}.json"
        done
      done

      # 6. Also run the generic quality_check.py pass as a broader sanity check
      OPENSTATES_API_KEY=<your v3.openstates.org key> python3 quality_check.py \
        --jurisdiction fl --bills 50 --no-people
      ```

      This also means: fix the stale premise itself, not just the data — this checklist item
      should not be read as "FL cutover is blocked on a prod incident," since no such incident
      occurred. It's a one-time local-DB repair, decoupled from whether/when FL gets added to
      `DDP_OPENSTATES_JURISDICTIONS` (see item 1 above for that separate blocker).
- [x] **FL historical backfill (2023/2024 regular)** — **DONE 2026-07-25.** The root-cause fix
      (`db7ab1cc0`, "use `self.source.url` instead of nonexistent `self.url` in FloorVote")
      merged via `openstates-scrapers` PR #6 (`fix/fl-floor-vote-source-url`), along with a
      follow-up fix (`2f1754d2f`, skip a vote whose reconciled tally doesn't add up instead of
      crashing). `2024` retried clean 2026-07-24 15:20 EDT (1,902 bills, 0 errors), then
      auto-chained into `2023` which finished 2026-07-25 05:24 EDT (1,828 bills, 2,601 vote
      events). Combined with specials + 2025 (already done), the replica now holds all FL
      sessions 2023+. See [[project-fl-historical-backfill]].
- [x] **FL's automated scrape schedule re-enabled, 2026-07-25.** `ddp-sync`'s `openstates_fl_scrape`
      job had been paused (`config/sync_schedule.yaml`, `enabled: false`) since 2026-07-24 to keep
      the historical backfill above from colliding with a scheduled run against the same shared
      `_data/fl` folder. With both sessions confirmed finished, re-enabled and `ddp-sync` restarted
      — confirmed live via `GET /ddp-sync/v1/schedule`, `openstates_fl_scrape` now shows next run
      2026-07-26 02:00 UTC (weekly, Sunday, per the existing out-of-session cadence).
- [ ] **Org/person-resolution gaps at import time — NOT FL-specific, confirmed across most
      jurisdictions (found 2026-07-25, extended 2026-07-25).** Every completed FL historical
      import (2024, 2025, 2023 regular) logs import-time errors from pupa: `cannot resolve pseudo
      id to Organization: ~{"name": "<name>"}` and `no people returned for spec`. Checked the
      other 6 tracked jurisdictions the same way (bounding each jurisdiction's own `Scrape done:
      <j>. Starting import...` → `Import done: <j>.` block in `logs/scraper.log`/archived
      `.gz` logs, to avoid the shared-log interleaving trap — a naive whole-file grep picks up
      other jurisdictions' errors too):

      | jurisdiction | sample | bills | vote_events | unresolved orgs (unique) | no-people-returned |
      |---|---|---|---|---|---|
      | FL 2024 | full | 1,902 | 2,607 | 57 | 33 |
      | FL 2025 | full | 1,959 | 2,148 | 56 | 13 |
      | FL 2023 | full | 1,828 | 2,601 | 56 | 8 |
      | **MA** | full (2026-06-16, pre-vote-fix) | 10,891 | — | **215** | **348** |
      | VA | incremental (2026-07-18) | 27 new/213 upd | 12 new/8 upd | 0 | 28 |
      | UT | incremental (2026-06-22) | 5 new/1016 upd | 10 new/1907 upd | 0 | 4 |
      | UT | incremental (2026-07-11) | 0 new/1021 upd | — | 0 | 0 |
      | WA | full (2026-06-23) | 0 new/3411 upd | 0 new/2302 upd | 0 | 1 |
      | AZ | incremental (2026-07-18) | 896 noop only | — | 0 | 0 |
      | MI | incremental (2026-07-18) | 36 new | — | 0 | 0 |

      **MA is worse than FL, not better** — 215 unique unresolved orgs and 348 no-people errors on
      a 10,891-bill full import. But note the sample predates the MA vote-scraping fixes (broken
      yield chain + case-sensitivity, see [[project-ma-votes]] / `project-ma-votes.md`,
      2026-06-22) and no full re-import has run since, so this number may not reflect current
      behavior — needs a fresh full MA import to re-measure. **VA** shows a real but smaller
      no-people gap (28 errors on just 12 new vote events — a high ratio for such a small run) with
      zero org-resolution errors. **UT/WA** show only trace amounts. **AZ/MI** show zero, but both
      samples were thin (AZ was pure no-op/noop-only, MI only 36 new bills) — not strong evidence
      of absence, just no evidence yet either way.

      **Root cause differs by jurisdiction, same failure shape:** in FL
      (`openstates-scrapers/scrapers/fl/bills.py:444-450`,
      `self.input.add_action(action, date, organization=actor, ...)`), bill actions/committee
      votes are recorded with a raw committee-name string rather than a resolved Organization
      reference, and pupa's importer resolves that string by name-matching against Organizations
      already scraped for the jurisdiction. FL's failure mode is **temporal**: committees are
      renamed/restructured every 2-year term (e.g. `"Higher Education Appropriations
      Subcommittee"`), and the org/people scrape only ever captures the *currently active* roster,
      so historical-session committees fail to resolve. MA's unresolved names
      (`"Attorney General"`, `"Auditor of the Commonwealth"`, `"Bristol District Attorney"`,
      `"Cannabis Control Commission"`, etc. — sampled from the 215) are **not** legislative
      committees at all — they're external entities (agencies, boards, district attorneys) that
      bill actions reference (e.g. "referred to the Attorney General") but that MA's org/people
      scrape was never going to capture, since it only scrapes the legislature itself. So this is
      a **categorical** mismatch for MA, not a renaming problem — a different root cause with the
      same symptom. VA/UT's smaller people-resolution gaps haven't been root-caused yet.

      In all cases the bill/vote-event record itself still imports (no data loss at that level —
      the `bill`/`vote_event` counts above are all "new"/"updated", none dropped); only the
      Organization attribution on the affected action/vote, or the affected individual voter's
      choice within an otherwise-complete roll call, is silently left unset/missing.

      **Decision, scoped 2026-07-28 — fix vs. accept, per jurisdiction:**

      - **FL: accept as a documented limitation, no fix planned.** Root cause (committee
        renaming across terms) would require a per-session historical committee scrape — real
        scraper work — to fix, and severity is low: nothing here drops bill/vote data, it only
        leaves some Organization attribution unset on already-imported records. **Correction
        2026-07-28 (PM review caught this):** FL is only in the *local checkout's target*
        `DDP_OPENSTATES_JURISDICTIONS` list — per the deploy-gap item below, it is **not**
        actually live in prod yet. So this is a decision about whether FL is *fit* to be added,
        not about live prod data. Revisit only if a consumer specifically needs committee-level
        historical attribution (none currently does).
      - **MA: get a fresh number first, then apply the same accept-as-limitation reasoning as
        FL — but this one actually gates a decision, not just documentation.** Unlike FL, MA
        hasn't been added to `DDP_OPENSTATES_JURISDICTIONS` yet, so this number is a live input
        to the MA vote-data validation item above, not just a nice-to-have. Re-run a full MA
        import post-vote-fix to replace the stale, pre-fix 215/348 numbers before deciding. If
        the fresh numbers are in the same range, the reasoning is identical to FL's (external
        entities, not legislative committees — a categorical scraper-scope gap, not a temporal
        one) and the same accept decision applies; a fix would mean extending MA's org/people
        scraper to also capture the external entity types (Attorney General, DAs, agencies, etc)
        bill actions reference, which is more speculative scope than FL's fix and not recommended
        unless the fresh number turns out much worse than expected.
      - **VA: root cause traced 2026-07-28, needs one more reproduction step before it's a fully
        scoped fix.** `scrapers/va/bills.py`'s `add_votes()` (line 394-397) and `add_sponsors()`
        (line 233-246) both pass only `MemberDisplayName` — a bare name string, no stable
        identifier — to `bill.vote()`/`add_sponsorship()`, the same shape of gap OPEN-2 found and
        fixed for US federal votes. Unlike OPEN-2, though, VA's own `people/` YAML has no clean
        structured identifier to key off (its LIS member code, e.g. `S113`, is embedded in a link
        URL, not a dedicated `identifiers:` field), and the actual failing names aren't visible in
        the current logs — `openstates-core/openstates/importers/base.py:663`'s
        `"no people returned for spec"` error is logged generically without the name that failed,
        confirmed by reading the importer code directly. **Next step:** write a short read-only
        script that re-runs the same name-matching query (`base.py`'s `Q(name__iexact=...) |
        Q(other_names__name__iexact=...) | Q(family_name__iexact=...)`) against every
        `MemberDisplayName` VA's vote/sponsor API actually returns, to surface the specific
        mismatching names (likely a formatting difference — e.g. "Last, First" vs "First Last",
        a nickname, or a suffix) rather than guessing. Only after that reproduction is a real fix
        (probably adding `other_names` aliases to the affected `people/` YAML entries) scoped.
        **Not a cutover blocker (clarified 2026-07-28, 3rd PM review pass):** same low-severity
        reasoning as FL/UT applies — bill/vote data still imports completely, only some
        individual voter attribution is silently missing — so VA stays in Stage 1 of the
        `DDP_OPENSTATES_JURISDICTIONS` rollout below while this investigation continues.
      - **UT: accept, monitor only.** Same shape of gap as VA (name-only matching in
        `scrapers/ut/bills.py`), but the actual error counts are trace (4 errors on a 1,907-vote-
        event run, then 0 on the next) — not enough signal to justify the VA-style investigation
        above. No action; revisit if future UT runs show a growing error count.

      Severity across all four remains low for bill-text/status use cases (nothing here affects
      bill data itself); the above should be treated as final for FL/UT and provisional for
      MA/VA pending the one remaining step each (fresh MA import; VA name-mismatch reproduction).
- [x] **Off-host backup (WS9, `PLAN-production-hardening.md`)** — **DONE, found already resolved
      while updating this checklist 2026-07-25.** No longer blocked on AWS creds: `backup-openstates-db.sh`
      now pushes nightly `pg_dump`s off-host via the `ddp-prod-s3-openstates-backups` proxy wrapper
      (commit `0276b3a`, merged via PR #7 `fix/ws9-s3-proxy-wrapper`), and `com.ddp.openstates-db-backup`
      already runs this nightly at 07:00 local as a system LaunchDaemon (`ddp-infra/README.md`). This
      item was stale on this branch — the fix landed on `main` while this branch sat unmerged.
- [ ] Confirm the `DDP_OPENSTATES_JURISDICTIONS` value in the *actual* EC2 deployment matches
      the local checkout's `.env` (`US,FL,MI,AZ,VA,WA,UT`) — **CONFIRMED 2026-07-23: it does
      NOT match.** Prod runs the code default (`UT,MI` only); the local `.env`'s wider list has
      not been deployed. See the correction note at the top of §8.

      **Scoped 2026-07-28 — this is not a small "flip a config value" task; there is currently no
      documented or scripted way to deploy this change at all.** `ddp-broker-py` production runs
      on its own dedicated EC2 host (separate from the WireGuard-connected "civic" instance that
      runs ddp-sync/votebot/ddp-api), managed by a systemd unit
      (`infra/systemd/ddp-broker.service`) that only starts/stops a Docker Compose stack from
      whatever is already checked out at `/opt/ddp-broker-py` — it doesn't pull code or touch env
      vars. There is no CI/CD pipeline (no `.github/workflows/`), no Ansible/Terraform, and no
      Secrets Manager/SSM usage for this service. The one deploy script that exists
      (`infra/scripts/deploy-broker-runtime.sh`) is explicitly documented in two places
      (`ddp-broker-py/RUNBOOK.local.md` and a prior deploy-night handoff note) as **dev-only** —
      it drives a local Mac Studio Docker stack, not the real EC2 box, and both docs say outright
      that the real EC2 deploy process (SSH target, script, whatever it is) isn't established
      anywhere yet. `ddp-infra/README.md` independently flags the identical gap ("EC2 service
      management... not yet documented"). The read-only prod-access tools that do exist
      (`ddp-prod-rds-readonly` etc.) only reach RDS/S3 through proxy wrappers, not the broker
      host itself.

      **Concrete steps, once SSH access to the broker host is established (the actual blocker):**

      **Gated 2026-07-28 (PM review caught this) — do not deploy the full 7-jurisdiction list as
      a single step; FL, MA, and US each have an open prerequisite above that must close first.**
      FL should not be included until the WAF-outage re-scrape (item above) has actually been run
      and `quality_check.py` confirms the gap is closed — right now FL's local replica has a
      known, unrepaired vote-completeness hole. MA should not be included until its §10.2 diff
      (item above) has actually been run and passed. **US should not be included until the
      OPEN-2 vote-person backfill (item above) has actually been run for real** (added in the
      2nd PM review pass — the code fix is live for new scrapes, but every already-scraped US
      Congress roll call still has its ~27.6% null-`voter_id` gap until the one-time backfill
      runs; unlike FL/MA's org-resolution gaps, which the plan already decided to accept as
      permanent documented limitations, this one has a ready, tested fix sitting unrun — no
      reason to expose it before running a ~30-minute script). Deploy in stages, not all at once:

      1. **Stage 1 (deployable now):** `DDP_OPENSTATES_JURISDICTIONS=MI,AZ,VA,WA,UT` — i.e. the
         target list minus FL, MA, and US, all three still gated on open items above.
         **Why these five are safe (added 2026-07-28, 3rd PM review pass):** MI and UT are
         already live in prod today as the two canary jurisdictions — no change in exposure for
         them. AZ and WA have no open item anywhere in this checklist. **VA has an open
         org/person-resolution investigation (above) but it is explicitly *not* a cutover
         blocker** — same low-severity reasoning already applied to FL/UT (bill/vote data still
         imports completely; only some individual voter attribution is silently missing), the
         investigation is about narrowing down the exact cause for a possible *future* fix, not
         about whether VA is safe to expose today. If that reasoning changes, revisit VA's
         inclusion here explicitly rather than silently.
      2. Edit the one line in `/opt/ddp-broker-py/.env` with the stage's value.
      3. Recreate — not just restart — the containers that read it, since env vars are baked in
         at container creation: `web`, `celery`, **and** `celery-beat` (the fetch/routing logic
         is shared by the API views and the Celery tasks, so recreating only `web` would leave
         scheduled scrapes routing the old 2 jurisdictions while the API serves the new ones — a
         silent inconsistency window):
         ```
         cd /opt/ddp-broker-py
         docker compose -p ddp-broker-py --env-file /opt/ddp-broker-py/.env \
           -f infra/compose/prod.yml up -d --no-deps web celery celery-beat
         ```
      4. **Verify all three containers actually picked up the new value** (easy to miss since
         it's baked in at creation, not read live). If any of the three don't show the expected
         value, re-run step 3 with `--force-recreate` appended (added 2026-07-28, 3rd PM review
         pass — compose sometimes skips recreation if it doesn't detect a meaningful change):
         ```
         docker compose -p ddp-broker-py exec web env | grep DDP_OPENSTATES_JURISDICTIONS
         docker compose -p ddp-broker-py exec celery env | grep DDP_OPENSTATES_JURISDICTIONS
         docker compose -p ddp-broker-py exec celery-beat env | grep DDP_OPENSTATES_JURISDICTIONS
         ```
      5. Validate: confirm a newly-added jurisdiction (MI/AZ/VA/WA/UT) is actually resolving
         through the DDP replica rather than live OpenStates. **Concrete evidence (added 2026-07-28,
         3rd PM review pass — the earlier draft only gestured at "the routing-decision log
         line" without naming it):** `openstates_service.py`'s `_get_client_for_jurisdiction()`
         logs `Routing {jurisdiction_iso2} to DDP OpenStates replica` at debug level
         (`openstates_service.py:1292`) — grep the broker's logs for this exact string with the
         new jurisdiction's ISO2 code after triggering a fetch for it. Also check the broker's
         logs after the next scheduled Celery fetch for that jurisdiction completes (not a formal
         monitoring window — just confirm the first real scheduled run after the flip doesn't
         error) before moving on to Stage 2.
      6. Rollback, if needed, is low-risk and symmetric: revert the one `.env` line (or remove it
         to fall back to the `UT,MI` code default) and re-run the same recreate command. No
         migrations, no schema changes — this flag doesn't change any served JSON shape.
      7. **Stage 2, once each item's prerequisite closes:** add `US` once the OPEN-2 backfill has
         actually been run; add `FL` once the WAF re-scrape/validation above is done; add `MA`
         once its §10.2 diff passes. Each addition repeats
         steps 2-5 above with the updated value.

      There is no staging/blue-green environment for this service, so this change goes live for
      real traffic the moment the containers recreate — no canary option exists.

      **Open question this raises for the rest of §8.1a:** whatever validation/confidence work
      has already been done against "prod" for FL/AZ/VA/WA (e.g. the WAF-outage audit below, or
      the org/person-resolution counts above) may have actually run against the local Mac Studio
      dev stack rather than real prod traffic, since prod was never actually running the wider
      jurisdiction list to begin with. Worth double-checking which environment each of those
      checks actually targeted before treating them as prod-validated.
- [ ] **People/roster data has no cutover path at all yet — found 2026-07-27, DDP now has its own
      fork of `people` too.** Everything in §8.1-8.3 is about the *bills/votes* path
      (`ddp-api` → api-v3 over WireGuard). Legislator roster data (`Role`/tenure dates) reaches
      ddp-broker-py through a completely different mechanism: a directly-mounted git clone of
      `openstates/people` (`OPENSTATES_PEOPLE_REPO_VOLUME_TARGET`), refreshed by a host-side
      `git pull` — no HTTP layer, no `ddp-api` involvement, in dev *or* prod. `people` just
      joined `openstates-core`/`openstates-scrapers` as a third DDP fork
      (`Digital-Democracy-Project/people`, see `PLAN-fork-management.md` §1) — its first use was
      openstates/people#3902, fixing Susan Valdés's missing FL House 2022-2024 term (found while
      debugging why her votes from that period weren't attributable). That fix only helps
      production once **upstream actually merges the PR** and prod's own clone re-pulls it —
      there is currently no way for prod to read a DDP-fork-only fix (one not yet accepted
      upstream, or never going to be) at all. Before relying on `people`-repo fixes for
      production correctness: either (a) give prod's people-clone a path to read DDP's fork
      directly (matching the bills/votes pattern — `ddp-api` would need a new proxied endpoint
      or a repointed git remote, TBD which), or (b) accept that DDP-fork-only roster fixes are
      dev-only until they land upstream, and budget for the upstream review-and-merge latency
      when prioritizing this class of fix. Not scoped further yet — needs its own design pass,
      probably as a new §8.1b once someone picks this up.

- [ ] **The S3 bill-archive relay is undersized and already gets overloaded at today's
      concurrency — found 2026-07-29 while restarting archive runs after the UT/VA fixes.**
      `os-text-extract archive`'s S3 upload step never talks to AWS directly (per
      `ddp-infra/Production_S3_Wrappers.md`, no raw AWS credentials exist on this Mac by
      design): it shells out to a sudo-gated local wrapper
      (`/usr/local/db-proxy/s3-bill-archive.sh`), which SSHes into a small dedicated EC2 box
      (`ubuntu@10.0.0.1`, referred to here as the "S3 relay") and runs the real `aws s3`/`aws
      s3api` command there. Every archived document costs **two** round trips through this
      relay (`_upload_and_verify()` in `text_extract.py`: one `put`, one `info` to confirm the
      upload via ETag).

      **What was actually found, ruled out in order:** a single `info` call was taking
      consistently ~7-8 seconds. Checked and ruled out, in sequence: (1) this Mac's own `aws`
      CLI usage isn't the path at all — the wrapper relays everything over SSH, so nothing
      about credentials or environment on this Mac is even in play; (2) SSH connection-reuse
      (`ControlMaster`/`ControlPersist`) was missing, added, confirmed working (a live
      multiplexed socket existed), and made **no difference** — ruling out SSH handshake
      overhead; (3) `aws --version` alone, run directly on the relay box with no network call
      and no credentials involved at all, still took ~6 seconds with real CPU time consumed (not
      idle waiting) — ruling out AWS/network entirely and pointing at the relay box itself; (4)
      `nproc`/`uptime`/`top` on the relay box confirmed it: **2 vCPUs, load average ~5.9-5.9,
      four separate `aws` processes observed running concurrently**, each getting roughly a
      third of a core. The relay box simply doesn't have enough processing power for the number
      of `aws` invocations arriving at once, so every single one queues and takes several
      seconds instead of a fraction of one.

      **Not just a testing artifact — this concurrency is already part of the real schedule.**
      The four concurrent `aws` processes observed were almost certainly this session's parallel
      archive test runs (WA/VA/MA/US federal all archiving at once), but `ddp-sync`'s existing
      Sunday `secondary` group (§13 below) already runs VA/MI/UT/AZ **simultaneously** every
      week in normal, already-scheduled operation — a very similar shape of concurrent load to
      what triggered this. This isn't a hypothetical scaling concern; today's actual weekly
      schedule already produces the conditions that overload this relay.

      **Directly relevant to §13's open EC2-sizing question below** — that section asks how
      much compute a 51-jurisdiction future would need and proposes a "spike" to measure it;
      this is real, already-collected evidence that the *existing* small-scale relay
      infrastructure is under-provisioned for even today's 8-jurisdiction load, before any
      scale-up discussion.

      **Not yet fixed — two remediation paths, not mutually exclusive:**
      1. Resize the relay EC2 instance to more vCPUs — the direct fix, removes the contention
         outright.
      2. Reduce how many jurisdictions archive concurrently (e.g. stagger the Sunday secondary
         group instead of running it simultaneously) — cheaper, no infra change, but works
         against the existing `sync_schedule.yaml` design rationale (§13/`PLAN-bill-document-
         provenance.md` Phase 1's own note treats simultaneous secondary-group execution as
         already-acceptable).
      3. Independent of either: `_upload_and_verify()`'s two-calls-per-document design could be
         cut to one, halving the relay's load regardless of which of the above is chosen —
         not scoped further here.

      **Why this belongs in the cutover strategy:** full production cutover means more
      jurisdictions and/or larger backfill volumes archiving through this same single relay,
      not fewer — whatever concurrency exists today only grows from here. This should be
      resolved (or explicitly accepted as a known limit) before treating the archive pipeline as
      cutover-ready, not discovered again under real production load.

**Not blockers** (clarifying since they're easy to conflate with the above): the WA/US-Congress
session-alias-mapping problem (§8.3) is a **votebot**-only issue — ddp-broker-py looks up
sessions by explicit code, not by year-probing, so it's unaffected. The `OPENSTATES_API_BASE`
env-var-flip code change in §8.2 is moot for ddp-broker-py — superseded by the proxy + bearer
token design already live.

### 8.2 Code changes (one-time, per service)

Make `OPENSTATES_API_BASE` env-configurable in each service (all currently hardcode `"https://v3.openstates.org"`):

| File | Change |
|---|---|
| `ddp-broker-py/src/fetch/interfaces/OpenStates/openstates_client.py` | `API_ROOT = os.getenv("OPENSTATES_API_BASE", "https://v3.openstates.org")` |
| `ddp-sync/src/ddp_sync/pipelines/bill_sync.py` | `OPENSTATES_API_BASE` class constant → `os.getenv()` |
| `ddp-sync/src/ddp_sync/services/openstates_people.py` | `BASE_URL` → `os.getenv()` |
| `ddp-sync/src/ddp_sync/ingestion/sources/openstates.py` | base URL → `os.getenv()` |
| `votebot/src/votebot/services/bill_votes.py` | `base_url` → `os.getenv()` |
| `votebot/src/votebot/utils/federal_legislator_cache.py` | base URL → `os.getenv()` |
| `votebot/src/votebot/config.py` | add `openstates_api_base: str` field |

After these changes, cutover = set `.env` in each service and restart. The right address depends on where each service runs and whether it has WireGuard:

| Service | Runs on | WireGuard | `OPENSTATES_API_BASE` |
|---|---|---|---|
| `ddp-broker-py` | EC2 (no WireGuard) | ✗ | `https://api.digitaldemocracyproject.org/openstates` |
| `ddp-sync` | EC2 (has WireGuard) | ✓ | `http://10.0.0.8:8002` |
| `votebot` | EC2 (has WireGuard) | ✓ | `http://10.0.0.8:8002` |

`10.0.0.8` is the Mac Studio's WireGuard VPN address. ddp-broker-py routes through `ddp-api` at `api.digitaldemocracyproject.org/openstates/*`, which proxies over WireGuard to Mac Studio :8002. See `ddp-api/app/routes/openstates_proxy.py`.

**ddp-broker-py `OPENSTATES_API_KEY`** — the proxy strips any incoming `?apikey=` and injects the internal UUID via `x-api-key` header transparently. ddp-broker-py still needs a UUID-format value to pass its local `uuid.UUID(key)` validation — use the existing real OpenStates key (see `.env`/Secrets Manager — not recorded here) or any valid UUID. It is not forwarded to api-v3.

ddp-sync and votebot: keep their existing `OPENSTATES_API_KEY` unchanged (they hit api-v3 directly over WireGuard, same key works).

Revert = restore original env vars and restart. No image rebuild required.

### 8.3 Session alias mapping (must resolve before votebot cutover)

`votebot`'s `BillVotesService.get_bill_info()` probes session identifiers as year strings: `"2026"`, `"2025"`, `"2024"`. This works for FL but not for:
- **WA** — session stored as `"2025-2026"`, not `"2025"`; a year probe returns 404
- **US federal** — session stored as `"119"` (Congress number), not a year

The live `v3.openstates.org` resolves this internally. The local api-v3 does exact matching.

**Decision, scoped 2026-07-28 — Option 1 (jurisdiction-aware resolver inside votebot), not a static
table or an api-v3 patch.** Checked the real session-identifier format for all 8 tracked
jurisdictions directly against each scraper's `__init__.py` (the plan's own §2 table turns out to
be wrong for AZ — it lists `"2025"`, but AZ's actual format is `"57th-1st-regular"`):

| Jurisdiction | Actual format | Derivable from a plain year by formula? |
|---|---|---|
| FL | `"2025"`, specials `"2025C"` | Yes |
| VA | `"2026"`, specials `"2026S1"` | Yes (regular sessions) |
| UT | `"2025"`, specials `"2025S1"` | Yes (regular sessions) |
| **WA** | `"2025-2026"` (biennium) | Yes — deterministic |
| **MI** | `"2025-2026"` (biennium) | Yes — deterministic |
| **US** | `"119"` (Congress number) | Yes — deterministic (`(year-1789)//2+1`) |
| MA | `"194th"` (Great Court ordinal) | No — needs an anchor constant |
| AZ | `"57th-1st-regular"` | No — needs an anchor constant (§2's table is wrong here) |

Only MA and AZ are genuinely non-formulaic, and neither is named as a §8.3 blocker — WA, MI, and
US (the jurisdictions that actually matter here) are 100% derivable from a calendar year with a
closed-form rule that never goes stale. That rules out **Option 3** (a static
`(jurisdiction, year) → session` table): WA/MI/US would need a manually-added row every year/
biennium/Congress forever, for jurisdictions that don't actually need it — pure maintenance
overhead with no upside over a formula. It also rules out **Option 2** (patching api-v3's route):
`ddp-open-states/api-v3` is a plain, unmodified checkout of upstream `openstates/api-v3` — unlike
`openstates-core`/`openstates-scrapers`/`people`, it is **not** one of DDP's three formal forks
(`PLAN-fork-management.md`) and has no mechanism to preserve a local edit across future syncs; a
hand-edit would be silently clobbered on the next `git pull`. It would also only fix a
votebot-specific problem while adding an unmanaged fork liability — `ddp-broker-py`/`ddp-sync`
already look up sessions by explicit code, unaffected either way.

**Implementation — `votebot/src/votebot/services/bill_votes.py`, `get_bill_info()`:**

```python
class BillVotesService:
    ...
    # Jurisdictions whose session identifier is a biennium range, e.g. "2025-2026".
    # A *format rule*, not a per-year lookup table -- grows only when a new jurisdiction
    # with the same naming scheme is onboarded, never because a year changed.
    _BIENNIUM_JURISDICTIONS = {"wa", "mi"}

    @staticmethod
    def _session_candidates(jurisdiction: str, session: str) -> list[str]:
        """Translate a caller-supplied session/year hint into an ordered list of
        session identifiers to probe, in the jurisdiction's actual format. `session`
        may already be an exact identifier ("2025-2026", "2026S1", "194th") -- those
        pass through unchanged."""
        jurisdiction = jurisdiction.lower()
        try:
            year = int(session)
        except ValueError:
            return [session]  # not a bare integer -- trust the caller as-is

        if jurisdiction == "us":
            if year >= 1000:  # looks like a calendar year, not a Congress number
                congress = (year - 1789) // 2 + 1
                return [str(congress), str(congress - 1)]
            return [str(year), str(year - 1)]  # already a Congress number

        if jurisdiction in BillVotesService._BIENNIUM_JURISDICTIONS:
            start = year if year % 2 == 1 else year - 1
            return [f"{start}-{start + 1}", f"{start - 2}-{start - 1}"]

        return [str(year), str(year - 1), str(year - 2)]  # FL/UT/AZ/VA-style, unchanged
```

Then in `get_bill_info()`, replace the current year-probe block with
`sessions_to_try = self._session_candidates(jurisdiction, session)`. This is a no-op for the
existing FL/UT/AZ/VA path, self-heals WA/MI/US, and needs no maintenance as years pass. It also
transparently fixes two duplicated "no session provided" defaults in `agent.py` (~lines 1705 and
2078, which today compute `session = str(year)` for every non-US jurisdiction — correct for FL,
wrong for WA/MI) since those callers just pass a bare year into `get_bill_info()`.

**Flag for later, not blocking:** MA/AZ aren't derivable from a year without an anchor constant.
Not needed now since neither is a §8.3 blocker, but if either is promoted to the votebot cutover
path, `_session_candidates` needs an anchor-based branch for them — and §2's session-format
table should be corrected for AZ regardless of when that happens.

**Person lookup endpoint difference — corrected 2026-07-28: wrong file, and not a one-line fix.**
Every live party-enrichment call in votebot's actual request path (`bill_votes.py`'s
`_get_legislator_parties`, `federal_legislator_cache.py`'s `_fetch_chamber_members`) already
correctly uses the bulk-list form (`GET /people?jurisdiction=...&org_classification=...`) — those
are fine against api-v3 as-is. The real `GET /people/{person_id}` call is in
**`votebot/scripts/refresh_openstates_cache.py`** (lines 103 and 111, a 429-retry duplicate),
inside `fetch_legislators_for_state()` — a standalone offline maintenance script, not part of
votebot's live request path, and not currently listed in §8.2's file table either. Since the
response shape changes (single object → paginated list), the fix is ~5 lines across both call
sites, not one line:

```python
detail_response = await client.get(f"{base_url}/people", params={"id": person_id}, headers=headers)
...
if detail_response.status_code == 200:
    results = detail_response.json().get("results", [])
    full_person = results[0] if results else person  # fall back to basic data
```

---

## 9. Phase 5: Scheduling & Automation ✓

### 9.1 Scrape schedule

| Jurisdiction | Frequency | Time (local) | Rationale |
|---|---|---|---|
| FL | Daily (session: Jan–May) | 2:00 AM | Active session; bills move daily |
| FL | Weekly (off-session) | Sunday 2:00 AM | Special sessions possible |
| WA | Daily (session: Jan–Mar) | 2:30 AM | Active session; biennial |
| WA | Weekly (off-session) | Sunday 2:30 AM | |
| US | Daily (Congress in session) | 3:00 AM | GovInfo updated daily |
| US | Weekly (recess) | Sunday 3:00 AM | |
| VA/MI/MA/UT/AZ/AL | Weekly | Sunday 3:30 AM | Secondary; less time-sensitive |

For session detection, use `ddp-sync`'s `StateLegislativeCalendar.is_in_session(state_code)` — it already has hardcoded session date ranges for all 50 states and is the single source of truth.

### 9.2 Scraper runner script

`~/Developer/repos/ddp-open-states/run-scrape.sh` — already written (2026-06-14). Key points:

- Sources `activate.sh` for `PYTHONPATH`, `DATABASE_URL`, `OS_UPDATE` path
- Applies `apply-local-patches.sh` before every scrape
- Posts to `#automation-errors` via Slack on `ERR` trap
- Michigan uses `--allow_duplicates` on import (issue #5697); all other states use strict import
- `OS_UPDATE` is `~/Library/Python/3.9/bin/os-update` — **not `poetry run os-update`**

```bash
# Michigan gets --allow_duplicates; all others strict
if [ "$STATE" = "mi" ]; then
    $OS_UPDATE "$STATE" --import --allow_duplicates >> "$LOG_DIR/scraper.log" 2>&1
else
    $OS_UPDATE "$STATE" --import >> "$LOG_DIR/scraper.log" 2>&1
fi
```

### 9.3 launchd scraper service

Unlike CAMS (which runs continuously), the scraper is a periodic job. Use `launchd` with `StartCalendarInterval` rather than `KeepAlive`.

Create `~/Library/LaunchAgents/com.ddp.openstates-scraper.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ddp.openstates-scraper</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/Users/agentsmith/Developer/repos/ddp-open-states/run-all-scrapes.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <array>
        <!-- Daily primary states: 2:00 AM -->
        <dict>
            <key>Hour</key>
            <integer>2</integer>
            <key>Minute</key>
            <integer>0</integer>
        </dict>
    </array>
    <key>StandardOutPath</key>
    <string>/Users/agentsmith/Developer/repos/ddp-open-states/logs/scraper.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/agentsmith/Developer/repos/ddp-open-states/logs/scraper.log</string>
</dict>
</plist>
```

Create `~/Developer/repos/ddp-open-states/run-all-scrapes.sh`:

```bash
#!/usr/bin/env bash
# Run all active jurisdiction scrapes. Called by launchd nightly.
set -e
DAY=$(date +%u)  # 1=Mon, 7=Sun

# Primary states: run daily
for state in fl wa us; do
    bash ~/Developer/repos/ddp-open-states/run-scrape.sh "$state" || echo "ERROR: $state scrape failed" 
done

# Secondary states: run weekly on Sunday (day 7)
if [ "$DAY" = "7" ]; then
    for state in va mi ma ut az al; do
        bash ~/Developer/repos/ddp-open-states/run-scrape.sh "$state" || echo "ERROR: $state scrape failed"
    done
fi
```

Register: `launchctl load ~/Library/LaunchAgents/com.ddp.openstates-scraper.plist`

### 9.4 People refresh

Legislator YAML changes when members retire, are elected in special elections, or change party. Run a weekly refresh:

```bash
# Add to run-all-scrapes.sh on Sundays:
cd ~/Developer/repos/ddp-open-states/people && git pull --ff-only
for state in fl wa us va mi ma ut az al; do
    cd ~/Developer/repos/ddp-open-states/openstates-core
    poetry run os-people to_database "$state"
done
```

---

## 10. Phase 6: Cutover & Validation

### 10.1 Pre-cutover checklist

Before pointing any service at `localhost:8002`:

- [ ] `os-initdb` completed without errors
- [ ] `os-people to_database` completed for all target states
- [ ] FL 2025 scrape completed; `opencivicdata_bill` has > 500 FL 2025 rows
- [ ] WA 2025-2026 scrape completed; `opencivicdata_bill` has > 300 WA rows
- [ ] US 119 scrape completed; `opencivicdata_bill` has > 2000 US rows
- [ ] `opencivicdata_voteevent` has vote records for FL, WA, US bills
- [ ] `opencivicdata_person` + `opencivicdata_membership` populated for all target states
- [ ] os-api shim starts cleanly on :8002 with zero errors
- [ ] `curl http://localhost:8002/bills?jurisdiction=fl&session=2025&apikey=test` returns valid JSON
- [ ] `curl http://localhost:8002/people?jurisdiction=fl&org_classification=lower&apikey=test` returns > 100 people
- [ ] `curl http://localhost:8002/jurisdictions/fl?include=legislative_sessions&apikey=test` returns session list

### 10.2 Parallel validation (before hard cutover)

Before changing service env vars, run a spot check by calling the local shim in parallel with the live OpenStates API and diffing responses:

```bash
# For a tracked bill (e.g., FL HB1 2025):
curl "http://localhost:8002/bills?jurisdiction=fl&session=2025&identifier=HB1&include=votes,actions,sponsorships" | jq . > local.json
curl "https://v3.openstates.org/bills?jurisdiction=fl&session=2025&identifier=HB1&include=votes,actions,sponsorships&apikey=$OPENSTATES_API_KEY" | jq . > live.json
diff local.json live.json
```

Key fields to verify match:
- `bill.identifier` (normalized)
- `bill.latest_action_description`
- `bill.votes[].motion_text`
- `bill.votes[].counts[].value` (yes/no counts)
- `bill.votes[].votes[]` (individual vote records)
- `bill.sponsorships[].name`
- `people[].name`, `people[].current_role.district`, `people[].current_role.division_id`

### 10.3 Soft cutover: ddp-broker-py first

> **Superseded 2026-07-21 — see the update note at the top of §8.** ddp-broker-py did not cut
> over via this env-var flip; it uses the ddp-api proxy + `DDP_OPENSTATES_JURISDICTIONS`
> gradual per-jurisdiction gate instead, and 7 of 8 jurisdictions are already routed to the
> replica. The steps below are kept for historical reference and because they describe the
> intended design for ddp-sync/votebot, which have not cut over.

1. Set `OPENSTATES_API_BASE=http://localhost:8002` in `ddp-broker-py/.env`
2. Restart Celery workers
3. Manually trigger `fetch_openstates_session_data` for FL: `celery call ddpbroker.fetch_openstates_session_data --args='[fl_jurisdiction_id]'`
4. Verify `LegislativeSession` records updated in broker DB
5. Manually trigger `fetch_openstates_bill_data` for a single tracked FL bill
6. Verify `Motion` + `Vote` records created/updated in broker DB
7. Monitor `logs/celery.log` for any HTTP errors or schema mismatches

### 10.4 Soft cutover: ddp-sync second

1. Set `OPENSTATES_API_BASE=http://localhost:8002` in `ddp-sync/.env`
2. Restart ddp-sync service
3. Trigger `/trigger/bill-status-sync?jurisdiction=fl&dry_run=true`
4. Verify response shows correct bill statuses from local shim
5. Trigger `/trigger/bill-version-check` for a single FL bill (use `limit=1`)
6. Verify Pinecone is updated and Redis bill_version cache reflects local data

### 10.5 Soft cutover: votebot last

1. Set `OPENSTATES_API_BASE=http://localhost:8002` in `votebot/.env`
2. Restart votebot service
3. Send a test chat message about a tracked FL bill that should trigger the Bill Votes Tool (use a bill not in Pinecone to force RAG confidence < 0.4)
4. Verify votebot returns accurate vote data from the local shim
5. Send a dispute message ("are you sure about those votes?") to trigger vote verification path

---

## 11. Ongoing Maintenance

### 11.1 Upstream scraper changes

Monitor `openstates/openstates-scrapers` for:
- New sessions added to FL/WA/US `__init__.py` — update scraper schedule
- Breaking changes to scraper output schema — will surface as `os-update` import errors
- New bugs introduced in our states — our PRs (#5695, #5696) may conflict with upstream changes after merge

Check `git log upstream/main -- scrapers/fl scrapers/wa scrapers/ut scrapers/mi` weekly.

### 11.2 Session transitions

When a new legislative session begins:
1. Update session metadata in `openstates-scrapers/scrapers/{state}/__init__.py` if the scrapers don't auto-detect it
2. Run `os-update {state} --scrape bills` for the new session
3. Run `os-people to_database {state}` (new members after elections)
4. Verify the os-api shim returns the new session in `GET /jurisdictions/{state}?include=legislative_sessions`
5. Update `ddp-broker-py` and `ddp-sync` session configurations if they hardcode session years

### 11.3 Monitoring

There are two existing systems to plug into — no new monitoring infrastructure needed.

#### api-v3 service health

`com.ddp.health-monitor` (`deployment/launchd/com.ddp.health-monitor.plist` in ddp-agents) already runs `health-check-slack.sh` every 5 minutes and posts to Slack when a service is unreachable. Add api-v3 to that script:

```bash
# In ddp-agents/deployment/scripts/health-check-slack.sh, add alongside the CAMS check:
if ! curl -sf --max-time 5 http://localhost:8002/health >/dev/null 2>&1; then
    post_slack "⚠️ *os-api (OpenStates local) is down* — check :8002"
fi
```

The existing script already handles Slack token lookup, boot grace period, and repeat-alert throttling. Nothing else needed.

#### Scraper failure alerts

**Implemented — and evolved past the original design below.** The scraper is a nightly job that
exits rather than a persistent service, so health-monitor doesn't apply. The original design was
a Slack-only `trap ... ERR` posting to `#automation-errors`; `run-scrape.sh` now does that *and*
POSTs a structured failure report to CAMS's own failure listener
(`$CAMS_URL/api/v1/failures`, service=`ddp-open-states`, with `error_type`/`message` parsed out
of the scrape/import output where possible) so a real recurring scrape bug reaches Agent Smith
triage, not just a Slack ping (`fix/report-scrape-failures-to-cams`, PR #3, 2026-07-23). Both the
Slack post and the CAMS report are best-effort (`curl -sf ... || true`) — a reporting failure
itself (CAMS down, bad token, network) never fails the scrape.

**Known gap this fixed, and the pattern it set:** a real crash inside `run-scrape.sh` (a bash
quirk — a background-pipeline failure that halts the script via `set -e` but never fires the
`ERR` trap) went completely unreported: no Slack message, no CAMS report. The bill-document
archive step (§8.1a) hit the same class of gap — a failing `os-text-extract archive` invocation
died on its first unhandled exception rather than looping, and relying solely on the generic
`ERR` trap risked masking *which* step actually failed. Fixed the same way in both places:
explicitly capture the step's own output, parse out a real `error_type`/`message` when present,
and call `on_failure` directly rather than trusting the trap to catch everything
(`fix/archive-failure-reporting`, PR #11, 2026-07-26). Any new scrape-pipeline step going forward
should follow this same explicit-report pattern rather than relying on the ambient trap.

#### Scraper staleness watchdog (scoped 2026-07-28, not yet built)

**Gap this fixes:** every failure-reporting path above fires from *inside* a `run-scrape.sh`
invocation — an `ERR` trap or an explicit `on_failure` call. Both require the script to actually
run and hit a recognizable failure. Neither fires when a job silently never finishes or never
starts at all. That's exactly what happened with MA: from 2026-06-16 until the fix this session,
the weekly MA scrape ran for ~12h against the wrong cache key every single Sunday, never crashed,
never hit the `ERR` trap, and so never posted to Slack or CAMS — six weeks of silence despite a
real, ongoing bug. `codebot_allowlist.yaml`/CAMS's listener is correctly wired and was verified
working end-to-end this session; it simply had nothing to listen for, because nothing upstream of
it can detect "this job should have produced a fresh timestamp by now and didn't."

**Signal to reuse:** every `run-scrape.sh` invocation already writes `logs/last-run/<SCRAPE_KEY>.ts`
on success (both the normal completion path and the incremental `finish_no_op()` no-op path
touch it — see `run-scrape.sh`). A key's `.ts` mtime going stale beyond its own expected cadence
is a direct, no-new-instrumentation signal that the job has stopped running to completion,
whether from a hang, a silently-swallowed exception, or a scheduling problem — the exact class of
bug that produced the MA gap.

**Explicit key → cadence map** (deliberately a hardcoded allowlist, not "every file under
`logs/last-run/`" — a growing directory of one-time historical-backfill keys must NOT be watched,
since they are done and correctly will never produce a newer timestamp again):

| Group | Keys | Expected cadence | Alert threshold |
|---|---|---|---|
| Daily | `fl_session_2026`, `fl_session_2026D`, `fl_session_2026E`, `fl_session_2026F`, `wa`, `usa_session_119_chamber_lower`, `usa_session_119_chamber_upper` | nightly (`run-all-scrapes.sh`, every day) | 48h (covers one missed night + buffer) |
| Weekly | `va`, `mi`, `ut`, `az`, `ma_session_194th` | Sundays only (`run-all-scrapes.sh`'s `DAY = 7` block) | 9.5 days (covers one missed Sunday + buffer) |

Explicitly **excluded** (one-time backfills, never expected to update again):
`fl_session_2023`, `fl_session_2023B`, `fl_session_2023C`, `fl_session_2024`, `fl_session_2025`,
`fl_session_2025A`, `fl_session_2025B`, `fl_session_2025C`, `usa_session_118_chamber_lower`,
`usa_session_118_chamber_upper`.

**Missing file counts as maximally stale, not "skip."** `ma_session_194th.ts` was deleted as part
of this session's MA fix and won't exist again until the next successful Sunday run. If the
watchdog treated an absent file as "nothing to check yet," it would have missed the exact MA bug
it exists to catch — a key that's supposed to be running but silently produces no timestamp file
at all is the failure mode, not an edge case to special-case away.

**Design (bash, matching `run-scrape.sh`'s own idioms — no new language/runtime to maintain):**

```bash
# check-scrape-staleness.sh — run once daily, appended to the end of run-all-scrapes.sh
# (already runs daily via the existing com.ddp.openstates-scraper launchd job — no new
# launchd job needed).
LAST_RUN_DIR="$SCRIPT_DIR/logs/last-run"
NOW=$(date +%s)

check_key() {
    local key=$1 threshold_hours=$2
    local ts_file="$LAST_RUN_DIR/${key}.ts"
    local sentinel="$LAST_RUN_DIR/${key}.stale-alerted"
    local age_hours=999999
    if [ -f "$ts_file" ]; then
        local mtime; mtime=$(stat -f%m "$ts_file")
        age_hours=$(( (NOW - mtime) / 3600 ))
    fi
    if [ "$age_hours" -ge "$threshold_hours" ]; then
        # Already alerted for this ongoing episode — don't re-fire every day it stays stuck.
        [ -f "$sentinel" ] && return 0
        touch "$sentinel"
        FAILURE_ERROR_TYPE="ScrapeStalenessDetected" \
        FAILURE_MESSAGE="$key has not completed in ${age_hours}h (threshold ${threshold_hours}h)" \
            report_staleness_to_cams "$key"   # same payload shape/endpoint as report_failure_to_cams()
    else
        # Fresh again — clear the sentinel so a future recurrence re-alerts.
        rm -f "$sentinel"
    fi
}

check_key fl_session_2026 48
check_key fl_session_2026D 48
check_key fl_session_2026E 48
check_key fl_session_2026F 48
check_key wa 48
check_key usa_session_119_chamber_lower 48
check_key usa_session_119_chamber_upper 48
check_key va 228        # 9.5 days
check_key mi 228
check_key ut 228
check_key az 228
check_key ma_session_194th 228
```

`report_staleness_to_cams()` reuses `report_failure_to_cams()`'s exact payload shape and POST
mechanics from `run-scrape.sh` (`service: "ddp-open-states"`, POST to `$CAMS_URL/api/v1/failures`
with `Authorization: Bearer $CAMS_TOKEN`, `curl -sf ... || true` so a reporting hiccup never
breaks the nightly run) — factor the shared bits into a small sourced helper rather than
duplicating the `python3 -c` JSON-building inline in both scripts.

**Rejected alternative:** watching `/tmp/ddp-openstates-scrapes/<pid>` reader-lock markers
instead of `.ts` files. Rejected because `apply-local-patches.sh` already sweeps that directory
clean on its own nightly schedule — by the time a watchdog ran, the evidence a job was ever stuck
would already be gone. `.ts` files are untouched by that cleanup and are already the source of
truth incremental scraping itself relies on.

**Not yet built or deployed** — this is the scope only. Next step when asked to build it:
add `check-scrape-staleness.sh`, extract the shared CAMS-POST helper out of `run-scrape.sh` (or
duplicate the ~15 lines — small enough that duplication may be simpler than a new shared-sourced
file), append the call to the end of `run-all-scrapes.sh`, and verify against the current MA gap
(the `ma_session_194th` key is absent right now, so a dry run should immediately alert once,
which doubles as an integration test).

#### Flagged idea: containerize scraper runs (raised 2026-07-28, not scoped, not decided)

The underlying problem: `ddp-open-states` has exactly one production checkout, shared by every
scrape regardless of jurisdiction. `~/Developer/repos/ddp-open-states-dev` (built 2026-07-24,
after a live FL backfill was mid-run when `run-scrape.sh` itself got edited on disk — see
`ddp-infra/PLAN-bill-document-provenance.md`'s Risk Register and Open Question 21a) solved "don't
develop against the live checkout," but deliberately left the harder half unsolved: *deploying*
a merged fix into the one shared production checkout still requires a quiet window with no scrape
running anywhere in the repo — there's still no way to promote new code without racing whatever's
currently running there.

The idea: have each scrape/archive invocation run in its own container built from an image
snapshot of the code, the way Postgres and `api-v3` already run. A merge/rebuild could never race
a running process, since the running process's container already has its own immutable copy —
this closes the gap the dev checkout didn't, without the bigger EC2/RDS split in §13.

**Why this isn't free:** the toolchain is already known to be finicky to package — the pinned
`pydantic<2` + `pip<24.1` + editable-install setup needed a real workaround just to build once
(`RUNBOOK.md`). A container image build would need to reproduce that reliably, likely on every
merge. The archive step also reaches outside a natural container boundary in two ways that would
need explicit wiring: the host-mounted `/Volumes/DDP-HOT` volume, and the sudo-gated
`ddp-prod-s3-bill-archive` wrapper (`/Users/agentsmith/bin/`), which is deliberately host-side only
(see `ddp-infra/Production_S3_Wrappers.md` — no raw AWS credentials exist inside any container or
checkout by design).

**Not scoped, not decided.** Revisit if the "wait for a quiet window before syncing" pain keeps
recurring (as it did prompting this note) — cross-reference §13's EC2/RDS question, since both
are ways of addressing the same single-shared-Mac-Studio risk concentration, at different scales.

### 11.4 Scraper fixes and upstream contributions

**Superseded 2026-07-17 onward — see §2.5.** The "maintain cherry-picks until upstream merges"
model this section originally described no longer applies to either repo: both
`openstates-scrapers` and `openstates-core` are now formal DDP forks with their own `main`
(`openstates-scrapers`) or `cherry-pick-line` (`openstates-core`) branch as the real target for
new fixes — public-upstream merge is no longer the gate for a fix reaching a live scrape.
`PLAN-fork-management.md` is the authoritative doc for this model, including the still-open
question of how DDP keeps receiving *upstream's* fixes going forward (not just shipping its own).

For a new scraper fix:
1. `openstates-scrapers`: branch off the fork's `main`, open a PR against fork `main`, merge —
   picked up automatically by `apply-local-patches.sh`'s plain `git pull origin main` on the
   next run.
2. `openstates-core`: branch off `cherry-pick-line`, open a PR against `cherry-pick-line`
   (**not** `main` — see §2.5), merge — picked up automatically by the range-pick on the next
   run. Double-check the PR's base ref before merging; a PR merged into the wrong base doesn't
   error, it's just silently inert.

Also monitor `openstates/openstates-scrapers` (public upstream) for whether the original UT
(#5695) and MI (#5696) fixes referenced in earlier revisions of this section have since merged
there — not re-checked as part of this update.

---

## 12. Effort Estimate

**Shadow phase (this plan):**

| Phase | Work | Est. Time |
|---|---|---|
| Phase 1: DB + openstates-core | Create DB, install, os-initdb, os-people | 3–4 hrs |
| Phase 2: Scrapers | Install, run FL+WA+US scrapes, debug | 4–6 hrs |
| Phase 3: api-v3 setup | Install, configure DB URL + API key, start, verify | 1–2 hrs |
| Phase 5: Scheduling | launchd plists + runner scripts | 2–3 hrs |
| **Shadow total** | | **10–15 hrs** |

**Future cutover (separate plan):**

| Phase | Work | Est. Time |
|---|---|---|
| Phase 4: Service rewiring | 7 small code edits + env var changes | 2–3 hrs |
| Phase 6: Cutover validation | Parallel diff testing, soft cutover per service | 3–4 hrs |
| Session alias fix (votebot) | ~10-line mapping for WA + US federal | 1 hr |
| **Cutover total** | | **6–8 hrs** |

Phase 3 is minimal — `api-v3` is already built and tested by OpenStates. The scrapes (Phase 2) are the most time-variable depending on how many states need debugging.

**Stale as of 2026-07-28 (PM review caught this) — the cutover total above doesn't reflect
what's actually been discovered since.** It predates: establishing broker-host deploy access
(currently unscoped — no estimate possible until SSH access exists), the people-repo
`cherry-pick-line` cutover design (small, comparable to the `openstates-core` work already done,
but not yet estimated in hours), the FL WAF re-scrape + targeted validation (~1 hr, mostly
wait-time for the re-scrape itself), the US vote-person backfill (~30 min including the
pre-run `pg_dump`), and VA's name-mismatch reproduction script (~1-2 hrs, not yet written). Not
re-totaled here — treat the `6–8 hrs` figure as covering only the original Phase 4/6/session-alias
scope, not these newer items.

---

## 13. Future Consideration: EC2/RDS Hosting at 50-State + Congress Scale

**Status: DRAFT, not decided — raised 2026-07-28 during a `ddp-infra/PLAN-bill-document-provenance.md` design discussion, not yet a scoped or committed piece of work.** Recorded here because it's a direct *alternative* to §3/§8's target architecture (Mac Studio hosts `openstates` + `api-v3` indefinitely; EC2 consumers reach it over WireGuard or `ddp-api`'s proxy), not an addition to it — if adopted, this would replace real infrastructure that's already partially live (§8.1a: `DDP_OPENSTATES_JURISDICTIONS=UT,MI` in prod today, `ddp-api`'s `openstates_proxy.py` already built), not extend it.

### The question

Today's target state (§3, §8.2) keeps the OpenStates replica — Postgres, `api-v3`, the scrapers themselves — on the Mac Studio permanently, with EC2 services reaching it over WireGuard (`ddp-sync`/`votebot` directly; `ddp-broker-py` via `ddp-api`'s proxy, since EC2 broker has no WireGuard peer). That was the right call at 8 tracked jurisdictions. The question raised while discussing `ddp-broker-py`'s `BillArtifact` design in the provenance plan: does it stay the right call once DDP tracks all 50 states + Congress (51 jurisdictions — a ~6.4x jump from today's 8), or is there a case for running the scrapers on EC2 instead, with `openstates` living in RDS as a separate database alongside (not merged with) `ddp-broker-py`'s?

### Why this isn't free to answer either way

**Case for moving:** the Mac Studio is already on a path to concentrate risk — it hosts the scrapers, `openstates` Postgres, and `api-v3` today, and per `PLAN-bill-document-provenance.md` Phase 8/9 will also host LegBot/MLX/Ollama and, eventually, `ddp-sync` itself. That concentration is already a named, deliberately-deferred risk in that plan's Risk Register ("Mac Studio becomes a heavier single point of failure... a separate redundancy plan is being scoped later, not part of this document"). Moving scraping + its DB to EC2/RDS directly mitigates that risk, and RDS's snapshot/backup posture is a stronger floor than a Docker-container Postgres backed by a home-grown `pg_dump`-to-S3 script (`PLAN-production-hardening.md` WS9). It would also likely retire `ddp-api`'s `openstates_proxy.py` — that proxy exists purely because the Mac Studio isn't reachable from all EC2 instances directly; if the data it fronts lived in the VPC instead, the proxy's reason for existing goes away.

**Case against:** this repo's own recent history is a cautionary tale, not a hypothetical one. `ddp-open-states` didn't have a real dev/prod split until three days ago (`ddp-open-states-dev`), and this same week found two real, previously-undetected bugs in `apply-local-patches.sh`'s core reactivation mechanism (never syncing the local `cherry-pick-line` ref from its remote; a merge-commit cherry-pick crash) that had silently no-op'd a merged fix for two days — see §2.5 and §8.1a above. Migrating scraping + its database to a new host is a materially bigger, riskier undertaking than the local-venv fix that already produced that fragility. It also isn't free (RDS sizing/ongoing AWS cost vs. hardware already owned) and doesn't touch the upstream-fork maintenance burden (`PLAN-fork-management.md`) at all — that's orthogonal to which box runs the code.

**It also directly undercuts `PLAN-bill-document-provenance.md`'s own Phase 9 reasoning.** Phase 9 (consolidate `ddp-sync` onto the Mac Studio) is justified specifically because, once Webflow is gone, `ddp-sync`'s remaining dependencies — `api-v3`, OpenStates Postgres, Ollama — are *entirely* on the Mac Studio, making `ddp-sync` on EC2 "a WireGuard hop with no resiliency upside." If OpenStates data moves to EC2/RDS, that premise breaks: `ddp-sync`'s dependencies split again (broker RDS + now openstates RDS, both EC2-side; only LLM dispatch stays Mac-Studio-adjacent, and that already goes through CAMS's task API rather than a direct call). Adopting this proposal argues for the *opposite* of Phase 9 — keeping `ddp-sync` on EC2, near both RDS databases. Whoever decides this should decide both questions together, not in isolation.

### Resource/compute spike — proposed scope, not yet run

Before writing a real design note (this section is explicitly not one), the actual sizing question needs an answer: how much EC2 compute would 51 concurrent jurisdictions realistically need, given that the Mac Studio's abundant RAM has meant parallel-scrape memory has never once been a constraint worth measuring — and that headroom doesn't transfer to a provisioned, costed EC2 fleet.

**What's already known, no new scraping needed:**
- Today's real concurrency ceiling is only 8 jurisdictions (FL/VA/WA/UT/AZ/MI/MA + US), not 51.
- There's already a real (if unmeasured) concurrency data point: `ddp-sync`'s `secondary` group (VA/MI/MA/UT/AZ, §9.1 / `sync_schedule.yaml`) already runs **simultaneously** every Sunday 02:00 UTC with no reported memory problems — nobody's ever attached a profiler to it.
- A quick live sample taken during this discussion: the archive-sweep process (`os-text-extract archive fl`) sits around 300–330MB RSS — but that's the lightweight fetch/extract/upload step, not the scraper+importer itself, which holds full `Bill`/`VoteEvent`/`Person` object graphs in memory and is almost certainly heavier.
- **A real memory anti-pattern is already known and directly relevant.** FL's scraper (inherited from public upstream, not DDP-authored — a 2025-03-05 commit, "handle blockages from fl website") used to wrap its *entire* session's bill generator in `retry_on_connection_error(lambda: list(do_scrape_with_retry()))`, buffering every bill's text/floor-votes/committee-votes fully in memory before writing anything to disk. Fixed for FL (`fix/fl-incremental-bill-scrape`, see §2.5), but nobody's checked whether any other state's scraper class — especially the high-volume states DDP doesn't track yet (CA, NY, TX, IL by legislative volume) — has the same pattern. This is exactly the kind of per-state variance that would break a naive "average memory × 51" estimate.
- **Not memory, but a real CPU/capacity data point now exists, found 2026-07-29 (§8.1a above).** The S3 bill-archive relay — a small dedicated EC2 box (2 vCPUs) everything's document uploads pass through — was found overloaded (load average ~5.9 on 2 cores) simply from today's normal Sunday secondary-group concurrency (VA/MI/UT/AZ archiving simultaneously, the same "no reported memory problems" group cited above). Nobody had profiled it because nothing had looked broken from the Mac Studio side — the pipeline still completed, just many times slower than it should have. Worth treating as a preview of what "nobody profiled it" can hide even at today's 8-jurisdiction scale, before extrapolating that same lack-of-signal to 51.

**What the spike needs to measure:**
1. Peak RSS **separately** for the scrape step and the import step, per jurisdiction — different memory shapes (HTTP fetch/parse vs. bulk Django ORM writes), averaging them together hides the real peak.
2. A sample across bill-volume tiers, not just the 7 states currently tracked — the highest-volume states are exactly the ones with zero real data today.
3. A code-read check (cheap — grep, not a live run) for the FL-style full-session-buffering pattern in any state before running it for real.
4. **The concurrency model itself, not just a number** — is the design target "all 51 run at the same clock time" (memory scales linearly with jurisdiction count), or a bounded worker pool that processes N at a time regardless of total jurisdictions (memory stays flat, wall-clock time grows instead)? Today's schedule already staggers rather than truly parallelizing all 8 (§9.1) — that's a de facto worker-pool model already, and probably the single highest-leverage decision in this whole question, ahead of any specific RSS number.
5. Translate (1)–(4) into an actual EC2 instance-family/cost estimate — likely memory-optimized (`r`-family), since scraping is I/O-bound (waiting on state legislature websites, not CPU-bound), once a real peak-per-worker-slot number and a chosen concurrency bound exist.

**Proposed cheap first pass (not yet run, needs sign-off before executing):** instrument the archive-sweep and the next Sunday secondary-group run for real RSS/CPU numbers (free — already-scheduled work, just needs a profiler attached); separately, grep `openstates-scrapers` for the FL-style buffering pattern across all currently-tracked states. Only after that decide whether fresh test scrapes against untracked high-volume states (CA/NY/TX/IL) are worth running before committing to a concurrency-model decision.

**Cross-reference:** `ddp-infra/PLAN-bill-document-provenance.md` Phase 1 (the document-archive step's ownership split assumes `ddp-open-states` and `DDP-HOT` are physically co-located) and Phase 9 (the `ddp-sync` consolidation logic this would directly affect — see above).

---

## Appendix A: Files to Create

| File | Purpose |
|---|---|
| `~/Developer/repos/ddp-open-states/activate.sh` | Environment setup helper |
| `~/Developer/repos/ddp-open-states/apply-local-patches.sh` | Apply UT+MI scraper patches |
| `~/Developer/repos/ddp-open-states/run-scrape.sh` | Single-state scrape+import |
| `~/Developer/repos/ddp-open-states/run-all-scrapes.sh` | Nightly all-states runner |
| `~/Developer/repos/ddp-open-states/start-os-api.sh` | api-v3 startup script |
| `~/Developer/repos/ddp-open-states/logs/` | Log directory (create it) |
| `~/Library/LaunchAgents/com.ddp.openstates-api.plist` | api-v3 launchd service |
| `~/Library/LaunchAgents/com.ddp.openstates-scraper.plist` | Scraper launchd job |
| `~/Developer/repos/ddp-open-states/openstates-core/.env` | openstates-core env |
| `ddp-broker-py/.env` (add 2 lines) | `OPENSTATES_API_BASE=http://localhost:8002` |
| `ddp-sync/.env` (add 2 lines) | `OPENSTATES_API_BASE=http://localhost:8002` |
| `votebot/.env` (add 2 lines) | `OPENSTATES_API_BASE=http://localhost:8002` |

## Appendix B: Shadow Phase — One DB Insert + No Code Changes

**Shadow phase requires no code changes to ddp-broker-py, ddp-sync, or votebot.** Those services continue pointing at `v3.openstates.org` unchanged.

**One-time SQL** (Phase 3.3 — needed to query local api-v3 manually):
Insert a `Profile` row with API key `00000000-0000-0000-0000-000000000001`.

**Cutover phase code changes** (documented in Phase 4, deferred):
See Phase 8.2 table — 7 small edits across 7 files, all adding `os.getenv("OPENSTATES_API_BASE", "https://v3.openstates.org")`.

## Appendix C: Conflict Avoidance Summary

| Resource | CAMS | ddp-sync | votebot | **os stack (new)** |
|---|---|---|---|---|
| PostgreSQL DB | `cams` | (uses broker) | — | **`openstates`** |
| Redis DB | `/0` | `/0` | `/0` | **`/1`** (if needed) |
| API port | 8000 | 8001 | 8000 | **8002** |
| Log file | `logs/cams-server.log` | systemd journal | `logs/queries/` | **`logs/scraper.log`, `logs/os-api.log`** |
| launchd label | `com.ddp.cams-server` | `com.ddp.broker` | — | **`com.ddp.openstates-api`, `com.ddp.openstates-scraper`** |
| Browser profile | `~/.config/grantbot/` | — | — | **none** (no browser needed) |

## Appendix D: Known bug — `/jurisdictions/{iso2}?include=legislative_sessions` returns HTTP 500

**Found:** 2026-07-28, while building `ddp-next`'s `/explore` feature
(`ddp-next/PLAN-openstates-integration.md`), which needed a session picker and so called
`OpenStates.get_jurisdiction_detail(iso2)` (`ddp-broker-py`:
`fetch/interfaces/OpenStates/openstates_client.py:136-158`) against the DDP replica for the
first time — this exact code path (this method, with its default
`include=["legislative_sessions"]`) had apparently never been exercised against the live
replica before.

**Symptom:** `GET https://api.digitaldemocracyproject.org/openstates/jurisdictions/{iso2}?include=legislative_sessions`
returns `HTTP 500` (empty-ish body, 21 bytes) for every tracked jurisdiction tested (FL, UT, MI,
US) — not jurisdiction-specific.

**Isolated to the `include` param:** the same request *without*
`include=legislative_sessions` succeeds (200) against the replica. The failure is specifically
in whatever server-side logic resolves the `legislative_sessions` include on `/jurisdictions/{iso2}`
in this deployment of `api-v3`.

**Impact:** `ddp-broker-py`'s new `GET /api/openstates-jurisdictions/<iso2>/sessions/` endpoint
(added for `ddp-next`'s session picker) correctly catches this as an upstream failure and
returns a clean `503` rather than crashing — so this isn't causing any 500s to leak out of
`ddp-broker-py`. But the session picker itself has no working data source until this is fixed
here, in the replica.

**Update 2026-07-29 — root cause found**, in `api-v3/api/db/models/jurisdiction.py`. Two
relationships declare a one-sided `back_populates` that its partner doesn't reciprocate:

```python
# Jurisdiction (line 26-30)
legislative_sessions = relationship(
    "LegislativeSession",
    order_by="LegislativeSession.start_date",
    back_populates="jurisdiction",   # <-- expects LegislativeSession.jurisdiction to reciprocate
)
```
```python
# LegislativeSession (line 54) -- does NOT reciprocate
jurisdiction = relationship("Jurisdiction")   # no back_populates at all
```

Same broken pattern a second time, one level down:

```python
# LegislativeSession (line 56-60)
downloads = relationship(
    "DataExport",
    back_populates="session",   # <-- expects DataExport.session to reciprocate
    primaryjoin="...",
)
```
```python
# DataExport (line 73) -- does NOT reciprocate
session = relationship(LegislativeSession)   # no back_populates at all
```

SQLAlchemy only raises a mapper-configuration error for a mismatched `back_populates` pair
the first time it actually has to fully configure that relationship — which happens on eager
load. `include_map_overrides` (`api-v3/api/pagination.py`'s `JurisdictionPagination`) maps
`legislative_sessions` to `selectinload("legislative_sessions")` *and*
`selectinload("legislative_sessions.downloads")` — i.e. asking for this one include forces
SQLAlchemy to configure **both** broken pairs at once. That's why it's 500 for every
jurisdiction (a mapper/schema bug, not data-dependent) and why omitting the include avoids the
crash entirely (neither relationship ever gets resolved).

**This is genuine upstream code, not a DDP patch** — confirmed via `PRIMITIVES.md`'s own
description of `api-v3/` as a pristine, gitignored, deliberately-unpatched checkout ("kept out
of the public `api-v3/` checkout on purpose, so that checkout stays pristine/upstream-mergeable").
So this bug (if it isn't already fixed in a newer upstream commit) most likely exists in the
public `openstates/api-v3` project itself, not something DDP introduced.

**Options, not yet acted on:**
1. Report/fix upstream (`https://github.com/openstates/issues/`, per `api-v3`'s own README) —
   the "correct" fix given this repo's stay-pristine convention for `api-v3/`.
2. Patch the local checkout directly — works, but breaks the pristine/upstream-mergeable
   property this repo deliberately maintains for `api-v3/`, and wouldn't survive a fresh
   upstream sync.
3. Leave it broken and keep working around it downstream — current state; `ddp-next` has
   disabled the one feature (session picker) that exercises this code path
   (`ddp-next/PLAN-openstates-integration.md`, and the fix commit disabling the client-side
   sessions fetch) rather than depend on a fix here.
