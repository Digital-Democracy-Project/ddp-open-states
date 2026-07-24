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

**Open PRs (not yet merged upstream):**

- **UT votes** (PR #5695, branch `fix-ut-votes-api-path`): Three fixes discovered during first full scrape run (2026-06-14):
  1. `yield from` fix — `scrape_bill_details_from_api` was discarding yielded objects
  2. `parse_html_vote` XPath fix — lxml normalizes invalid HTML, breaking `//b` selector
  3. Duplicate vote identifier fix — when a bill has concurrent House+Senate votes, both got `identifier="283"`. Fixed to `f"{voteID}-{voteHouse}"` (e.g. `"283-H"`, `"283-S"`). This fix was discovered during import, not scrape — `DuplicateItemError` on `os-update ut --import`.

- **MI House votes** (PR #5696, branch `fix-mi-house-votes`): Regex + tab-separated name fix.

- **MI pagination duplicates** (issue #5697, not yet fixed upstream): The MI scraper produces duplicate bill JSON files due to pagination overlap. Workaround: `--allow_duplicates` flag on import. The `run-scrape.sh` script handles this automatically for `mi`.

**`apply-local-patches.sh`** cherry-picks all three UT commits plus the MI fix onto a `local-patches` branch:

```bash
git cherry-pick ade373f  # MI: fix House votes (PR #5696)
git cherry-pick 38e0206  # UT: fix votes not scraped for 2025+ sessions (PR #5695)
git cherry-pick abea3cd  # UT: fix duplicate vote identifier for concurrent chamber votes
```

Run after every upstream `git pull`.

**CLIs are at `~/Library/Python/3.9/bin/`** (pip-installed, not poetry). `PYTHONPATH` must include the `scrapers/` directory. Both are set in `activate.sh`.

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

### 8.1 Prerequisites before cutover

- Shadow scrapes have run nightly for ≥ 4 weeks with no silent gaps
- Parallel validation (§10.2) has passed for all 9 jurisdictions
- Session alias mapping resolved (see below)
- pg_dump backup confirmed working

### 8.1a ddp-broker-py remaining blockers (found 2026-07-21)

- [ ] **MA vote-data validation.** MA is the only jurisdiction still excluded from
      `DDP_OPENSTATES_JURISDICTIONS`. The replica has 45 vote events across 10,959 MA bills,
      matching the motion-classifier's known total (RUNBOOK "Motion classification"), so the
      scraper itself works — but the formal §10.2 parallel diff against live
      `v3.openstates.org` hasn't been run/recorded for MA specifically. Run it, then add `MA`
      to the jurisdictions list.
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
- [ ] **FL vote-completeness audit across the WAF-outage window.** The flhouse.gov WAF-cookie
      bug (fixed fork PR #5, merged 2026-07-18) silently dropped House committee votes on
      scrapes running past ~1 hour. FL is *already* in `DDP_OPENSTATES_JURISDICTIONS`, so if it
      was routed there before the fix, some House votes served to prod during that window may
      be missing. Run a targeted vote-count check (or a full `quality_check.py` diff) for FL's
      current session(s) before fully trusting this data.
- [ ] **FL historical backfill (2023/2024 regular)** — not yet landed as of last confirmed run.
      **Update (2026-07-24):** the root-cause fix (`db7ab1cc0`, "use `self.source.url` instead
      of nonexistent `self.url` in FloorVote") **has now merged** — `openstates-scrapers` PR #6
      (`fix/fl-floor-vote-source-url`) landed on that fork's `main`, along with a related
      follow-up fix (`2f1754d2f`, skip a vote whose reconciled tally doesn't add up instead of
      crashing). Separately, `ddp-open-states` PR #3 (`fix/report-scrape-failures-to-cams`) also
      merged, wiring scrape/import failures into CAMS's failure listener, and
      `apply-local-patches.sh` now auto-syncs the `openstates-scrapers` checkout back to `main`
      on every run (closing the "stuck on a stale branch for 2 days" gap that let this failure
      recur unnoticed 07-21/22/23). **Not yet confirmed:** no successful FL 2024 backfill run has
      landed in `logs/backfill/fl_2024.log` since the fix merged — last entry is still the
      07-23 14:29:26 failure, predating the fix. Watch the next scheduled run to confirm it
      actually clears; if it does, 2023 regular (queued behind 2024) and the old-DB decommission
      in `PLAN-production-hardening.md` can both proceed.
- [ ] **Off-host backup (WS9, `PLAN-production-hardening.md`)** — still blocked on AWS creds.
      The replica DB's only backup today lives on the same Mac's disk as the live data — a
      real single point of failure now that prod partially depends on this replica.
- [x] Confirm the `DDP_OPENSTATES_JURISDICTIONS` value in the *actual* EC2 deployment matches
      the local checkout's `.env` (`US,FL,MI,AZ,VA,WA,UT`) — **CONFIRMED 2026-07-23: it does
      NOT match.** Prod runs the code default (`UT,MI` only); the local `.env`'s wider list has
      not been deployed. See the correction note at the top of §8.

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

**Fix options (choose one at cutover time):**
1. Add a jurisdiction→session alias map in `BillVotesService.get_bill_info()` (~10 lines)
2. Add a fuzzy session resolver in api-v3's `/bills/{jurisdiction}/{session}/{bill_id}` route that accepts a year and resolves it to the matching session identifier
3. Populate a `KNOWN_SESSIONS` config in votebot that maps `(jurisdiction, year) → session_identifier`

ddp-broker-py and ddp-sync are unaffected — they look up sessions by explicit code from the broker DB, not by year probing.

**Person lookup endpoint difference** — votebot calls `GET /people/{person_id}` for party enrichment on vote records. api-v3 does not have this route; the correct form is `GET /people?id={person_id}`. One-line fix in `votebot/src/votebot/services/bill_votes.py` at cutover time.

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

The scraper is a nightly job that exits rather than a persistent service, so health-monitor doesn't apply. Instead, post to Slack directly from `run-scrape.sh` on failure. Add a trap at the top of the script:

```bash
# In run-scrape.sh, add after the log() function definition:
SLACK_TOKEN=$(grep -E '^SLACK_BOT_TOKEN=' /Users/agentsmith/Developer/repos/ddp-agents/.env \
    | head -1 | cut -d'=' -f2- | tr -d '"'"'" | awk '{print $1}')

on_failure() {
    local state=$1
    [ -n "$SLACK_TOKEN" ] && curl -sf --max-time 10 \
        -X POST https://slack.com/api/chat.postMessage \
        -H "Authorization: Bearer $SLACK_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"channel\": \"#automation-errors\", \"text\": \"⚠️ *OpenStates scrape failed: $state* — check ~/Developer/repos/ddp-open-states/logs/scraper.log\"}" \
        >/dev/null || true
}
trap 'on_failure "$STATE"' ERR
```

This reuses the same Slack token and channel as the CAMS health monitor. A failed FL scrape at 2 AM shows up in `#automation-errors` the same way a CAMS outage does.

### 11.4 Scraper fixes and upstream contributions

Maintain the patch-apply workflow (`apply-local-patches.sh`) until PRs #5695 and #5696 are merged. After merge:
1. Remove the cherry-picks from `apply-local-patches.sh`
2. Run `git pull --ff-only` in openstates-scrapers
3. Verify the fixes are present: `git log --oneline -- scrapers/ut/bills.py`

For future scraper fixes, prefer opening upstream PRs immediately (as we did for MI and UT). Local patches are a maintenance burden.

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
