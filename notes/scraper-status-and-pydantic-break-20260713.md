# OpenStates replica: scraper status + `os-people` pydantic break (2026-07-13)

Findings from a status check of the OpenStates scraping toolchain on the Mac Studio
(the machine that runs the scrapers and hosts the local replica). Two parts: (1) overall
scraper health, and (2) a deep-dive on why the nightly **people/roster refresh** has been
silently failing.

> **UPDATE 2026-07-15 — RESOLVED.** Both the surgical fix and the durable fix are applied:
> pydantic downgraded to v1, people backfill run (7/9 states; MA/AL need `--purge`), and the
> OpenStates toolchain moved into its own venv (`.venv/`) so another service's install can no
> longer change its pydantic. Details in "Fix" below; operational docs in `RUNBOOK.md` →
> "OpenStates toolchain venv".
>
> **UPDATE 2026-07-16 — FL historical backfill.** Goal set: replica must hold **all FL
> sessions from 2023 onward** (was current-2026 only). Added `backfill-fl-historical.sh`
> (sequential, smallest-first, marker-skipping → resumable). DB audit confirmed the Jul-8 FL
> 2023–2025 attempts had **never landed** (only US 118 did). Ran the 5 special sessions:
> 2023B/2023C/2025A/2025B/2025C now in the replica (14/21/22/2/7 bills). The **3 regular
> sessions (2023/2024/2025) are still pending** — deferred as ~4-day heavy runs to an
> off-hours window; nightly scheduler left untouched. Procedure + status in `RUNBOOK.md` →
> "Backfilling historical (non-scheduled) sessions".

---

## 1. Scraper status — mostly healthy

Schedule (`run-all-scrapes.sh`) is **UTC-based**: primary states run nightly, secondary
states run on **Sunday (UTC)**. The machine is UTC-7, so "Sunday UTC" fires Saturday night
local. That's why the secondary batch last ran Jul 11 night local (= Sun UTC) and the
Jul 12-local run (= Mon UTC) was primary-only. Nothing is behind schedule.

**Bill/vote scraping (the scorecard-critical path) is healthy and current:**

| Jurisdiction | Cadence | Last run | Result |
|---|---|---|---|
| US-119 (House+Senate) | nightly | Jul 12 | 641 House + 56 Senate — actively pulling |
| FL (4 sessions) | nightly | Jul 12 | 0 new (no-op; sessions quiet) |
| WA | nightly | Jul 12 | 0 new (no-op; out of session) |
| MI / UT / AZ | weekly (Sun UTC) | Jul 11 | 96 / 1021 / 896 |

Minor / gaps:
- **VA bill scrape not completing.** VA is configured (`VA_API_KEY` set) and starts a `full`
  scrape each Sunday window (Jun 27, Jul 11), but produces **no SCRAPE SUMMARY / last-run
  marker** — only a one-off manual run on Jun 29 succeeded (3955 bills). VA always runs in
  `full` mode (no incremental cutoff) → slow/heavy; appears to hang or fail silently. VA bill
  data stale since Jun 29. **Not yet diagnosed.**
- **WA** logs `ScrapeError: no objects returned from WABillScraper` every night — benign
  (incremental no-op, WA out of session), but it masks "no changes" vs "scraper actually broke."
- **MA** last completed Jun 29 (full). Secondary; not one of the broker's tracked-7.
- No dedicated `openstates-scrape` launchd plist was found; scrapes are demonstrably running
  nightly, so something schedules `run-all-scrapes.sh` (mechanism not pinned down — not urgent).

---

## 2. The `os-people` pydantic break (people/roster refresh dead since ~Jun 17)

### Symptom
Every Sunday people refresh (`os-people to-database <state>`) fails for **all** states
(fl, wa, us, va, mi, ma, ut, az, al) — e.g. Jul 12 06:00 in `logs/scraper.log`:
```
os-people to-database fl
Traceback ...
  File ".../openstates/models/committees.py", line 57, in ScrapeCommittee
  File ".../pydantic/deprecated/class_validators.py", line 240, in root_validator
pydantic.errors.PydanticUserError: If you use `@root_validator` with pre=False (the default)
you MUST specify `skip_on_failure=True`. ...
ERROR: os-people to-database fl failed (continuing)
```
It's an **import-time crash** (fails building `ScrapeCommittee` the moment `os-people` imports
`openstates.models`), so it dies before touching data — hence identical failure for every state.

### Root cause: shared Python env + a FastAPI install upgraded pydantic
- `openstates-core` 6.25.2 is written for **pydantic v1** — `pyproject.toml` pins
  `pydantic = "^1.8.2"` (`>=1.8.2,<2`), and `committees.py` uses v1 idioms (`@root_validator`,
  `@validator(..., allow_reuse=True)`).
- The environment (shared user site-packages `~/Library/Python/3.9`, no venv) now has
  **pydantic 2.13.4**. Under v2 the deprecated `@root_validator` shim raises at class-definition
  time → import crash.
- **What upgraded pydantic:** on **Jun 17**, **FastAPI 0.128.8** was installed into the same
  shared setup. FastAPI declares `Requires-Dist: pydantic>=2.7.0`, which pulled pydantic 2.13.4
  (+ pydantic_core, starlette, annotated_types) — all showing the same Jun 17 install date.
  That silently overrode openstates-core's `<2` pin. FastAPI is what the gateway / api-v3 are
  built on, so this was almost certainly a side effect of setting up / updating those services.
- The env is now in a state its own constraints forbid — two co-located declarations conflict:
  `fastapi → pydantic>=2.7.0` vs `openstates → pydantic (>=1.8.2,<2.0.0)`.
- **The fork is a red herring:** forking `openstates-scrapers` only changes code, not installed
  library versions. Scraper code is unchanged and fine.

### Impact — replica roster only; does NOT reach the broker
- **What's stale:** the tool loads legislator YAML into the **replica database**. That table has
  not refreshed since ~Jun 17 (~4 weeks). Bills/votes in the replica are unaffected (different,
  working job).
- **The broker does NOT use the broken path for legislators** (verified in ddp-broker-py
  `fetch/interfaces/OpenStates/openstates_service.py::update_representatives_for_jurisdiction`):
  - Roster (who's in office) is fetched **live from the public OpenStates API**
    (`openstates_client.OpenStates()` → hard-wired `https://v3.openstates.org`, line ~1838) —
    NOT routed to the replica (bills ARE routed to the replica via `_get_client_for_jurisdiction`,
    people are not).
  - Role start/end dates are derived from the **openstates/people git repo** (YAML → Redis index),
    refreshed by `git pull` — which still works (the failing step is `to-database`, not the pull).
  - So the stale replica roster is **not read by the broker**; scorecards are unaffected.

### Fix (APPLIED 2026-07-15)

**Step 1 — surgical unblock (done).** Downgraded pydantic to the version the toolchain requires:
```
python3 -m pip install 'pydantic>=1.8.2,<2'   # installed 1.10.26
```
- Confirmed safe: nothing declares a pydantic-≥2 dependency except FastAPI (Docker/api concern);
  the whole openstates stack pins `<2`; bill scrapes run natively on v1. Blast-radius verified —
  the only thing that *runs* from the shared 3.9 env is the `os-*` toolchain; every HTTP service
  (api-v3, broker, ddp-agents :8000, ddp-sync :8001) is isolated in Docker or its own venv.
- `import openstates.models` then imported cleanly, and the manual people backfill
  (`run-people-refresh.sh`) caught up ~4 weeks: **7/9 states imported** (fl wa us va mi ut az;
  35 person rows changed). MA and AL exit non-zero on the `--purge` safety guard (one orphaned
  executive record each — Andrea Joy Campbell / Steve Marshall), not a crash; run
  `os-people to-database ma --purge` (and `al`) to clear.

**Step 2 — durable root-cause fix (done).** Isolated the toolchain in its own virtualenv so
installing FastAPI (or anything) for another service can no longer change the scrapers' pydantic:
- Venv at `.venv/` (Python 3.9.6), built from `requirements-openstates.txt` (frozen known-good set
  minus the pydantic-v2 forcers). `activate.sh` + `run-scrape.sh` repointed to `.venv/bin`; ddp-sync
  drives both scrapes and people refresh through those scripts, so all scheduled jobs now use the venv.
- Rebuild recipe + the `pip<24.1`/textract gotcha are documented in `RUNBOOK.md` →
  "OpenStates toolchain venv". Verified: all 9 active state scrapers import + `os-people to-database az`
  runs clean under the venv.
- The shared 3.9 user-site was left at pydantic v1 (harmless; keeps the old `~/Library/Python/3.9/bin`
  path working as a fallback).

Still separate/looming: Python 3.9 is EOL (google-auth FutureWarning) — a broader interpreter upgrade
is a future task, independent of this fix.

### Evidence pointers
- `logs/scraper.log` Jul 12 06:00 — all `os-people to-database <state> failed` + full traceback.
- Installed: `pydantic 2.13.4` (site-packages dir mtime Jun 17), `openstates 6.25.2`,
  `fastapi 0.128.8` (Requires-Dist: pydantic>=2.7.0).
- `openstates-core/pyproject.toml`: `pydantic = "^1.8.2"`; `openstates-core/openstates/models/committees.py:56` `@root_validator`.
