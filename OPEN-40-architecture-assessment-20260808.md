# Architecture Assessment: OPEN-40 — Scraper staleness watchdog (PLAN-open-states §11.3)

## Architectural Question

The §11.3 design (ddp-infra/PLAN-open-states.md, scoped 2026-07-28) fully specifies the *check*
(compare each watched `logs/last-run/<key>.ts` age against its cadence, missing file = maximally
stale, sentinel de-dupe, alert via the existing Slack/CAMS paths). What it does **not** correctly
specify anymore is **where the check runs and which keys it watches** — the deployment vector it
names is dead, and two rows of its key→cadence table no longer match the live schedule. The
question is: **what should trigger `check-scrape-staleness.sh`, given that the watchdog must not
share a failure domain with the thing it watches, and what is the correct key→threshold map as of
2026-08-08?**

## Tech Stack Context

| Layer | Technology | Notes |
|-------|-----------|-------|
| Scrape runner | `run-scrape.sh` (bash 3.2, this repo) | Writes `logs/last-run/<SCRAPE_KEY>.ts` on every successful completion (normal path `run-scrape.sh:431` and incremental no-op path `finish_no_op()` at `:283`) — the signal the watchdog reads |
| Scheduler | ddp-sync APScheduler (`src/ddp_sync/pipelines/openstates_scrape.py`), system LaunchDaemon `com.ddp.ddp-sync` | Replaced the `com.ddp.openstates-scraper` launchd job 2026-06-22 (plist deleted 2026-06-24, RUNBOOK.md:88-91). Invokes `run-scrape.sh` per jurisdiction |
| Legacy runner | `run-all-scrapes.sh` (this repo) | **No longer scheduled by anything** — kept for manual runs; its header comment ("called by com.ddp.openstates-scraper launchd job") is stale |
| Existing health monitor | `ddp-agents/deployment/scripts/health-check-slack.sh`, system LaunchDaemon `com.ddp.health-monitor`, every 5 min | Independent of ddp-sync; already does Slack token lookup from `ddp-agents/.env`, boot grace, state-file de-dupe in `/var/tmp`, recovery messages; already checks CAMS (:8000) and os-api (:8002) |
| Failure alerting | `on_failure()` + `report_failure_to_cams()` in `run-scrape.sh:62-99` | Dual path: Slack `#automation-errors` + structured POST to CAMS `/api/v1/failures` (service `ddp-open-states`), both best-effort (`curl -sf … || true`) |
| Conventions catalog | `PRIMITIVES.md` | Slack alert-on-failure is a **copy-the-pattern** primitive (used by `run-scrape.sh`, `backup-openstates-db.sh`, `run-archive.sh`), not a shared sourced file |

## Ground truth vs. the §11.3 design — three material discrepancies

Verified against ddp-sync `config/sync_schedule.yaml` + `pipelines/openstates_scrape.py` (fetched
from GitHub main) and the production `logs/last-run/` directory (read-only, 2026-08-08):

1. **The design's deployment vector is dead.** §11.3 says to append the check to
   `run-all-scrapes.sh` because it "already runs daily via the existing
   `com.ddp.openstates-scraper` launchd job — no new launchd job needed." That launchd job was
   deleted 2026-06-24 (RUNBOOK.md:88-89); scheduling moved to ddp-sync's per-jurisdiction
   APScheduler jobs, none of which call `run-all-scrapes.sh`. Built as written, the watchdog
   would never execute. Worse, even when that job existed, the placement was self-defeating:
   a watchdog that runs at the end of the scrape pipeline it watches can never catch "the
   pipeline never started" — which is one of the exact failure modes the ticket names
   (ddp-sync itself was down 2026-07-04→08, RUNBOOK.md:101-107, and nothing alerted).

2. **The MA key in the design table is wrong for the live schedule.** The design watches
   `ma_session_194th`. But ddp-sync's `run_secondary_scrapes_job()` deliberately passes
   `session_arg=None` for all secondaries — a documented decision (OPEN-24,
   `openstates_scrape.py:677-683`: VA and UT each had two simultaneously-active sessions, so a
   single hardcoded session would silently drop one). With no session arg, `run-scrape.sh`
   derives `SCRAPE_KEY=ma` and writes `ma.ts`. Production confirms: `ma.ts` exists (fresh,
   2026-08-01) and `ma_session_194th.ts` does not exist at all. Watching `ma_session_194th`
   would fire a **permanent false alert** from day one and never clear. The `session=194th` fix
   in `run-all-scrapes.sh:46-47` only governs the manual path; the live key is `ma`. (Same
   reasoning applies to `va/mi/ut/az` — bare keys — which the design already has right.)

3. **FL is weekly, not daily, right now.** The design's table puts the four FL session keys in
   the Daily/48h group. ddp-sync has had `primary.fl.sync_day: sunday` since 2026-07-16
   (out-of-session; revert to daily when the 2027 session opens). Production confirms: all four
   `fl_session_2026*.ts` files are dated Sunday 2026-08-02 — already ~6 days old and perfectly
   healthy. A 48h threshold on FL would false-alarm **every Tuesday**. FL must sit in the
   weekly/228h bucket for as long as `sync_day: sunday` stands. (The ticket AC's wording —
   "48h threshold for daily jobs, 228h for weekly" — is cadence-based, so this classification
   still satisfies the AC as written; only the design table's grouping is stale.)

One operational heads-up, not a discrepancy: `mi.ts` is dated 2026-07-25 (~14 days old — MI has
missed two consecutive Sundays, consistent with the known MI WAF-block saga). The watchdog will
correctly alert on MI the first time it runs. That's a true positive and doubles as the
integration test the design asked for, but whoever deploys should expect it.

## Approaches Evaluated

### Approach A: Build the design as written — append to `run-all-scrapes.sh`

**How it works:** Add `check-scrape-staleness.sh`, call it at the end of `run-all-scrapes.sh`.

**Pros:** Matches the §11.3 text verbatim; zero cross-repo changes.

**Cons:** Does not work. `run-all-scrapes.sh` has no scheduler, so the check never runs.
Re-scheduling it just to host the watchdog would resurrect the monolithic runner ddp-sync
deliberately replaced, and still leaves the watchdog sharing fate with the scrape pipeline —
a scheduler outage (observed live, 4 days, July 2026) silences scrapes *and* watchdog together.

**Standards alignment:** Fails the basic monitoring-independence principle (Google SRE:
monitoring must not depend on the systems it monitors).

### Approach B: New ddp-sync APScheduler job

**How it works:** Add an `openstates_staleness_check` block to `sync_schedule.yaml` and a small
pipeline in ddp-sync (Python) that stats the `.ts` files daily and alerts via ddp-sync's existing
`push_health_alert` / Slack plumbing.

**Pros:** Fits the current scheduling model (everything scrape-related is an APScheduler job);
Python is easier to unit-test than bash; ddp-sync already has per-run alerting and the OPEN-22
escalation machinery nearby.

**Cons:** Common-mode failure — the single most valuable thing this watchdog can catch is
"ddp-sync silently stopped running jobs" (it wedged for 4 days in July), and a watchdog *inside*
ddp-sync is blind to exactly that. Also puts the key→cadence map a repo away from
`run-scrape.sh`, which owns key derivation; and it's a larger cross-repo implementation for a
ticket homed in ddp-open-states.

**Standards alignment:** Good 12-factor config hygiene (YAML-driven), but fails monitoring
independence — the disqualifier.

### Approach C (recommended): `check-scrape-staleness.sh` in this repo, invoked by the existing `com.ddp.health-monitor` daemon

**How it works:**
- `check-scrape-staleness.sh` lives in ddp-open-states next to `run-scrape.sh` (bash, matching
  its idioms — the design's own language choice). It owns the hardcoded key→threshold map,
  computes each watched key's `.ts` mtime age (missing file → age 999999h, alerts), keeps
  `logs/last-run/<key>.stale-alerted` sentinels for once-per-episode de-dupe with clear-on-recovery
  (the design's exact mechanism), and on a new staleness episode posts to Slack
  `#automation-errors` *and* POSTs a `ScrapeStalenessDetected` failure to CAMS
  `/api/v1/failures` — copying `on_failure()`/`report_failure_to_cams()`'s ~15-line pattern per
  the design's explicit "duplication may be simpler than a new shared-sourced file" note and
  PRIMITIVES.md's copy-the-pattern convention.
- One-line hook in `ddp-agents/deployment/scripts/health-check-slack.sh` (separate companion PR
  to ddp-agents): `bash /Users/agentsmith/Developer/repos/ddp-open-states/check-scrape-staleness.sh || true`
  — the `|| true` guarantees a watchdog bug can never break CAMS/os-api health monitoring
  (that script runs `set -uo pipefail`).
- Runs every 5 minutes with the monitor; the sentinel makes that equivalent to "alerts once per
  episode" regardless of cadence, and detection/recovery-clear latency drops from a day to
  minutes. Cost is ~12 `stat` calls per 5 minutes — negligible.

**Pros:** The only approach where the watchdog survives every failure mode it exists to catch —
job hung, job crashed silently, job never scheduled, scheduler daemon dead. Satisfies AC #5
("alerts to the existing Slack channel via the existing health-monitor plumbing") *literally* —
`com.ddp.health-monitor` **is** the health-monitor plumbing. No new launchd job (the design's own
constraint). Key map lives in the repo that defines the keys. Keeps the CAMS→Agent Smith triage
path the design wants, which the AC's Slack-only wording would otherwise drop.

**Cons:** Two-repo change (script here, one-line hook in ddp-agents). The health-monitor daemon
runs as root, so sentinel files land root-owned in `logs/last-run/` (agentsmith owns the
directory, so manual cleanup still works; alternatively sentinels can live in `/var/tmp/` beside
the monitor's other state files). §11.3 said "the scraper is a nightly job that exits, so
health-monitor doesn't apply" — but that rationale addressed *in-run failure alerting*, not a
poll-style staleness check, which is precisely the shape health-monitor already handles for CAMS
and os-api.

**Standards alignment:** Monitoring independence (Google SRE); fail-open alerting (best-effort
`curl -sf … || true`, matching every alert path in this stack); idempotent/de-duped alerting via
sentinel state (the same state-file pattern health-check-slack.sh already uses).

## Tradeoff Matrix

| Dimension | A: run-all-scrapes.sh | B: ddp-sync job | C: health-monitor hook |
|-----------|----------------------|-----------------|------------------------|
| Actually runs today | **No** | Yes | Yes |
| Catches scheduler-dead | No | **No** | Yes |
| Complexity | Low | Medium | Low |
| Time to implement | Low | Medium | Low |
| Maintainability | Low (dead host script) | Medium | Medium-high |
| Testing ease | Medium (bash) | High (pytest) | Medium (bash; MI is a live fixture) |
| Reversibility | High | Medium | High (delete one line + one file) |
| Alignment with codebase | Matches stale doc | Matches scheduler model | Matches PRIMITIVES.md + §11.3's api-v3 precedent |
| Repos touched | 1 | 2 (mostly ddp-sync) | 2 (mostly this repo) |

## Recommendation: Approach C

**Why this approach:** The ticket exists because MA failed silently for six weeks — every alert
path fired only from inside a run. The general form of that bug is "the thing that was supposed
to run, didn't," and it applies equally to ddp-sync itself (proven: 2026-07-04→08). The only
placement that detects all of scrape-hung / scrape-silently-wrong / scheduler-dead is a process
independent of both, and `com.ddp.health-monitor` is exactly that process, already deployed,
already alerting to the right Slack channel, already using the state-file de-dupe pattern the
design specifies (Google SRE monitoring-independence; fail-open alerting per the stack's
established `curl -sf || true` convention). It's also the reading that makes AC #5 true rather
than approximately true.

**Why not the alternatives:** A never executes — the launchd job §11.3 cites was deleted six
weeks before the design was scoped, and self-hosted watchdogs can't see their host die. B is a
reasonable engineering answer that fails the specific threat model: it would have been silent
during the July ddp-sync outage, the highest-value event to catch.

**Corrected key→threshold map** (supersedes the §11.3 table; verified against
`sync_schedule.yaml` and production `logs/last-run/` on 2026-08-08):

| Threshold | Keys | Basis |
|---|---|---|
| 48h (daily) | `wa`, `usa_session_119_chamber_lower`, `usa_session_119_chamber_upper` | daily at 02:30/03:00 UTC |
| 228h (weekly) | `fl_session_2026`, `fl_session_2026D`, `fl_session_2026E`, `fl_session_2026F` | **weekly while `primary.fl.sync_day: sunday`** (since 2026-07-16); move back to 48h when FL reverts to daily for the 2027 session |
| 228h (weekly) | `va`, `mi`, `ut`, `az`, `ma` | Sunday secondaries. **`ma`, not `ma_session_194th`** — ddp-sync passes no session arg (OPEN-24), so the live key is bare `ma` (`ma.ts` confirmed in production; `ma_session_194th.ts` no longer exists) |

Excluded (one-time backfills, will correctly never update): `fl_session_2023`–`fl_session_2025C`,
`usa_session_118_chamber_lower/upper` — unchanged from the design.

**Risks and mitigations:**

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| MI alerts immediately on first run (14 days stale today) | Certain | Low (true positive) | Expected — treat as the design's own suggested integration test; note it in the PR and Slack |
| Watchdog bug breaks CAMS/os-api monitoring | Low | High | Invoke with `|| true` from health-check-slack.sh; watchdog is a self-contained script |
| FL reverts to daily and nobody updates the map | Medium | Medium (7-day blind spot on FL) | Comment in the map cross-referencing `sync_schedule.yaml` `fl.sync_day`, mirroring the existing "remove sync_day to restore daily" note there |
| Root-owned sentinel files in `logs/last-run/` | Certain | Very low | Directory is agentsmith-owned so cleanup works; or keep sentinels in `/var/tmp/` like the monitor's other state |
| Key drift (new session keys, OPEN-24-style changes) | Medium | Medium | Hardcoded allowlist is a deliberate design decision (backfill keys must not be watched); document the map as the thing to touch when the schedule changes |
| ddp-agents hook lands but this repo's script path missing (or vice versa) | Low | Low | Hook is `bash <path> || true` — absent script is a silent no-op, not a monitor failure; sequence the PRs this-repo-first |

**Prerequisites:**
- Companion one-line PR to `ddp-agents` (health-check-slack.sh) — coordinate merge order
  (this repo first).
- Update the §11.3 section in `ddp-infra/PLAN-open-states.md` to record the corrected map and
  deployment vector (it's the canonical doc; leaving it stale invites rebuilding Approach A later).

**Tech debt created:** The cadence map is now hardcoded in a second place relative to
`sync_schedule.yaml` (accepted — the design explicitly chose a hardcoded allowlist over globbing,
for good reason). The FL threshold carries a scheduled future edit (2027 session). No new
runtime, no new daemon, no shared-helper abstraction added.

## Standards Checklist

| Standard | Status | Notes |
|----------|--------|-------|
| Monitoring independence (Google SRE, "monitor outside the failure domain") | Addressed | Watchdog runs in `com.ddp.health-monitor`, independent of ddp-sync and the scrape scripts |
| Fail-open alerting / graceful degradation | Addressed | `curl -sf … || true` on both Slack and CAMS posts; `|| true` on the hook invocation |
| Idempotent, de-duplicated alerting | Addressed | Sentinel file per key, once per episode, cleared on recovery (AC #4) |
| OWASP (secrets handling, injection) | Addressed | Tokens read from `ddp-agents/.env` at runtime, never logged (existing pattern); no user input reaches the JSON payload — keys are hardcoded and JSON is built via `python3 json.dumps`, matching `report_failure_to_cams()` |
| Reuse-before-reinvent / PRIMITIVES.md | Addressed | Copies the documented Slack/CAMS alert pattern (the catalog's stated convention is copy, not shared-source); reuses the `.ts` marker signal with zero new instrumentation |
| 12-Factor | N/A | No service/config surface added; single-host bash tooling by design |
| Multi-tenancy | N/A | Single-tenant operational tooling |

## Next Step

No data-model work — skip `/design-feature`. Run `/plan-ticket OPEN-40` to break this into the
implementation plan: (1) `check-scrape-staleness.sh` with the corrected map + sentinel logic in
this repo, (2) the one-line ddp-agents hook PR, (3) the ddp-infra §11.3 doc correction, (4)
verify against the live MI staleness as the integration test.
