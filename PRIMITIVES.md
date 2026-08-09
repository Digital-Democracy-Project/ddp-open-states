---
name: Existing primitives & building blocks inventory (ddp-open-states)
description: Catalog of every DDP-owned script, convention, and pattern already built on top of openstates-scrapers/openstates-core. Read this before writing new tooling — the scrape/import/backfill/patch pipeline already has answers for logging, resumability, alerting, and env isolation; don't re-derive them.
type: reference
---

# READ THIS FIRST — BEFORE WRITING NEW SCRIPTS

Everything DDP-owned in this repo lives at the root (shell scripts + a few Python tools) plus
`deploy/`. `openstates-scrapers/`, `openstates-core/`, `api-v3/`, `people/`, etc. are gitignored
upstream/fork checkouts — code changes there go through their own repos/PRs, not this file.
Before adding a new script, grep this repo's root for an existing one that already does most of
what you need — the patterns below (marker-based resumability, `log()`, Slack alert-on-failure,
`SCRAPE SUMMARY` lines, dedicated venv) recur on purpose; a new script that reinvents one of them
instead of sourcing/calling the existing script is the failure mode this file exists to prevent.

## The pipeline shape

```
run-scrape.sh <state> [session=X]      ← the one true scrape+import entrypoint
    ├─ apply-local-patches.sh          ← pulls openstates-core + openstates-scrapers fork main (skip via SKIP_PATCHES=1)
    ├─ os-update --scrape bills ...    ← from openstates-scrapers (fork main)
    └─ os-update --import ...          ← writes to the dedicated Postgres (:5433)

run-all-scrapes.sh / run-people-refresh.sh   ← nightly drivers that call run-scrape.sh per jurisdiction
backfill-fl-historical.sh                    ← one-off historical driver, same run-scrape.sh calls, resumable
```

**Scheduling note:** `run-all-scrapes.sh` and the old `com.ddp.openstates-scraper` launchd job
are legacy — scheduling moved to `ddp-sync`'s APScheduler on 2026-06-22 (see `RUNBOOK.md` →
"Services"). `run-scrape.sh` itself is still the live entrypoint either way; only what *calls*
it changed. Don't add new schedule logic here — add a job to `ddp-sync/config/sync_schedule.yaml`
instead.

## `run-scrape.sh` — the scrape+import entrypoint (repo root)

This is the one script everything else calls. It owns several primitives that a new script
should reuse rather than reimplement:

- **Incremental cutoff via marker files** — `logs/last-run/<state>_<session>.ts` (ISO timestamp,
  written on success) and the matching `.count` file (`<bills_scraped>:<mode>`). On the next run,
  if a `.ts` marker exists, it's read back, shifted 1 hour earlier as a safety margin, and passed
  as `os-update ... start=<ts>` (incremental mode). No marker → full scrape. **This is the
  resumability primitive** — `backfill-fl-historical.sh` reuses it directly (it just checks
  whether `logs/last-run/fl_session_<id>.ts` exists before calling `run-scrape.sh` at all, rather
  than duplicating cutoff logic).
- **`log()`** — `echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a logs/scraper.log`. Every DDP
  script in this repo defines its own copy of this exact pattern (`run-scrape.sh`,
  `run-all-scrapes.sh`, `run-people-refresh.sh`, `backfill-fl-historical.sh` — the last two write
  to their own log files but same shape). `start-os-api.sh`/`backup-openstates-db.sh` use a UTC
  variant (`date -u '+%Y-%m-%dT%H:%M:%SZ'`) for their own `[start-os-api]`/`[db-backup]`-prefixed
  logs. **Use one of these exact one-liners in any new script** — don't invent a third logging
  convention.
- **`=== SCRAPE SUMMARY: ... ===` line** — one clearly-`grep`-able line per run:
  `$STATE $SESSION | mode=<full|incremental> | bills_scraped=N | prev_run=<N> (<mode>)`. Also
  emits a `WARNING:` line if an incremental run's bill count drops below 20% of the previous
  incremental run (possible over-filtering). `backfill-fl-historical.sh`'s own driver log greps
  for `DONE|FAILED|complete` against its wrapper output, not this line — the two logs are
  complementary (`logs/scraper.log` has the real scrape detail; the backfill `.out`/per-session
  logs have only the wrapper's own status lines).
- **Failure retry: `--fastmode`** — on a scrape failure, retries once with `--fastmode` (reads
  `_cache/` instead of re-hitting the legislature site). Distinguishes a genuine failure from a
  benign incremental no-op (`"no objects returned from"` in the scrape output + incremental mode
  → `finish_no_op()`, which still writes the marker/count files and exits 0, not a failure).
- **Slack alert-on-failure** — `on_failure()` posts to `#automation-errors` via a bot token read
  from `ddp-agents/.env` (`SLACK_BOT_TOKEN`), fired via `trap 'on_failure' ERR`. Fails open (no
  token found → just skips the post, never blocks the scrape). **Reused verbatim in
  `backup-openstates-db.sh`** (`slack_fail()`, same token-read line, different channel message).
  **Update 2026-08-08 (OPEN-40):** the copy count reached five (`run-scrape.sh`,
  `run-archive.sh`, `backup-openstates-db.sh`, `start-os-api.sh`, `check-scrape-staleness.sh`)
  — extraction into a shared sourced helper is now tracked as **OPEN-43**; don't add a sixth
  copy, wait for (or do) that ticket instead. The watchdog may deliberately remain a copy even
  after extraction (monitoring shouldn't share code with what it monitors).
- **Worktree lock (reader side)** — drops a PID marker at `/tmp/ddp-openstates-scrapes/$$` for
  the duration of the scrape, removed via `trap ... EXIT`. `apply-local-patches.sh` checks this
  directory (writer side, see below) before touching `openstates-core`, so a patch pull can't
  clobber code a running scrape is reading. **This is a live lock protocol between two scripts —
  if you add a third script that mutates `openstates-core`'s checkout, it needs to honor this
  same marker directory**, not add its own.
- **`--allow_duplicates` states** — `mi`, `fl`, `va` pass this to `os-update --import` (pagination
  overlap produces duplicate bill JSON; see openstates-scrapers issue #5697). Check this list
  before assuming a new state needs the same flag — most don't.
- **`SKIP_PATCHES=1`** env var — skips the `apply-local-patches.sh` call entirely. Set by
  ddp-sync's scheduler (each jurisdiction's own scheduled run doesn't re-run the patch step; a
  separate `openstates_patch_refresh` cron job does it once). Also the escape hatch when
  `openstates-core` is parked on a dirty feature branch and the patch step's `git checkout main`
  would fail — see `RUNBOOK.md` → "`apply-local-patches.sh` blocker".

## `apply-local-patches.sh` — fork/patch management (repo root)

**Both repos now use the same convention** (as of 2026-08-01 — see `PLAN-fork-management.md`
§6 for why `openstates-core` moved off its older, separate model):
- Both `openstates-scrapers` (formal DDP org fork since 2026-07-03) and `openstates-core`
  (moved 2026-08-01) are **formal forks** — fork `main` IS the patched state, no cherry-picking,
  no local branch rebuild. Day-to-day: `git checkout -b feat/x` → PR to the fork's own `main`.
  This script's job for both is just `git checkout main && git pull origin main` — a freshness
  guard, not a patch-application step, so a merged fix branch left checked out (as happened to
  `openstates-scrapers` on 2026-07-23, `fix/fl-floor-vote-source-url` sitting stale for 2 days
  feeding a running scrape) doesn't silently drift off `main`.
- **Remote convention, identical for both**: `origin` = the DDP fork
  (`Digital-Democracy-Project/openstates-{core,scrapers}`), `upstream` = the real project.
  `openstates-core` previously had these reversed (`origin` = upstream, a separate `ddp` remote
  = fork) — renamed to match `openstates-scrapers`' existing convention as part of the same
  2026-08-01 change, since the mismatch was itself a contributor to at least one wrong-branch
  incident (see `RUNBOOK.md`'s `apply-local-patches.sh` section for the full history, kept as
  record — `cherry_pick()`/`local-patches`/`cherry-pick-line` are retired terms as of this date,
  you'll only see them in historical notes now).
- **Worktree lock (writer side)** — before touching anything, scans `/tmp/ddp-openstates-scrapes/`
  for live PIDs (`kill -0`) and exits 0 (skip, don't fail) if a scrape is running; stale markers
  from dead scrapes are cleaned up automatically. This is the other half of `run-scrape.sh`'s
  reader-side marker (above) — the two only make sense together.
- **The `git checkout main` step assumes `openstates-core` isn't mid-feature-work.** If it's
  parked on a branch like `phase1-bill-provenance` with uncommitted changes, this step fails and
  (via `run-scrape.sh`'s `on_failure` trap) aborts the *entire* scrape before it starts — not a
  scraper bug, a patch-step side effect. See `RUNBOOK.md` for the current instance of this and
  the `SKIP_PATCHES=1` workaround. Don't "fix" this by adding a `git stash` here — that would
  silently blow away someone's in-progress work on `openstates-core`.
- **`people` also has a formal DDP fork now** (`Digital-Democracy-Project/people`, since
  2026-07-27 — first use: openstates/people#3902, Susan Valdés's missing 2022-2024 FL House
  term). It follows `openstates-core`'s convention, not `openstates-scrapers`'s: `origin` stays
  on public upstream so `run-people-refresh.sh`'s weekly `git pull --ff-only` — the thing a real
  production WireGuard tunnel reads from — never silently drifts behind community data; `ddp` is
  purely a staging remote for pushing a local fix branch and opening a PR back upstream, never a
  pull source. See `PLAN-fork-management.md` §1 for the full reasoning.

## `check-scrape-staleness.sh` — scraper staleness watchdog (repo root, OPEN-40)

Read-only consumer of the `logs/last-run/<key>.ts` marker primitive: compares each watched
marker's mtime age against a **hardcoded key→threshold allowlist** (48h daily / 228h weekly;
missing marker = maximally stale, alerts) and alerts Slack `#automation-errors` + CAMS
`/api/v1/failures` once per staleness episode, de-duped via `logs/last-run/<key>.stale-alerted`
sentinel files (cleared on recovery, with a recovery post). Designed to be invoked every 5
minutes by the `com.ddp.health-monitor` LaunchDaemon via a one-line hook in `ddp-agents`'s
`health-check-slack.sh` — **live as of 2026-08-08**, confirmed by a real first-run alert in
`logs/staleness-check.log` (MI, the expected true positive) and its sentinel file. Placement is
deliberately outside ddp-sync and the scrape scripts, so it
survives the failure modes it exists to catch (including the scheduler daemon itself dying).
Deliberately **self-contained** — sources nothing, copies the Slack/CAMS pattern (see the
extraction note under `run-scrape.sh` above). The allowlist is the thing to touch when the
ddp-sync schedule changes (keep in sync with `sync_schedule.yaml`); backfill markers
(`fl_session_2023`…, `usa_session_118_*`) must never be added to it. `STALE_*` env vars are
test seams only — `test-check-scrape-staleness.sh` runs the whole lifecycle against a mktemp
fixture dir with no network. Full operator doc: `RUNBOOK.md` → "Scraper staleness watchdog".

## `backfill-fl-historical.sh` — historical/one-off backfill driver (repo root)

The pattern for **any future one-off historical backfill** (a different jurisdiction, a
different data type): loop a fixed, overridable list of `run-scrape.sh` calls, smallest/fastest
first, **skip anything with an existing `logs/last-run/*.ts` marker** (reuses `run-scrape.sh`'s
own resumability primitive rather than tracking its own state), log wrapper status to
`logs/backfill/<name>-historical.out` plus one per-item log under `logs/backfill/`. Meant to be
launched detached (`nohup ... &`) since a single item can run for many hours — `run_in_background`
agent tasks die on session teardown, this does not. If you add a backfill for another
jurisdiction, copy this script's shape (marker-check loop + smallest-first ordering), don't
build a new state-tracking mechanism.

## `activate.sh` — environment setup (repo root, sourced not executed)

Single source of truth for every env var the toolchain needs: `DATABASE_URL` (dedicated
Postgres, :5433), `OS_PEOPLE_DIRECTORY`, `PYTHONPATH` (scrapers dir), `SCRAPELIB_RPM`,
`SCRAPED_DATA_DIR`/`CACHE_DIR` (under `openstates-scrapers/`, passed explicitly by
`run-scrape.sh` as `--datadir`/`--cachedir` so a launchd invocation's `cwd=/` doesn't make
`os-update` fall back to a read-only `/_cache`), and the **dedicated toolchain venv**
(`OS_VENV=.venv`, prepended to `PATH`; `OS_INITDB`/`OS_UPDATE`/`OS_PEOPLE` all resolve into it).
The venv exists because `openstates-core` hard-pins `pydantic<2` and used to share the host's
user site-packages with other services — a stray `pip install` of something pydantic-2-only
(FastAPI) broke every `os-*` command at import time. **Any new tool that shells out to
`os-update`/`os-people`/`os-initdb` must `source activate.sh` first** (or otherwise land on
`.venv/bin`) — don't call the system Python's copies.

Rebuild recipe (also in `RUNBOOK.md`): `/usr/bin/python3 -m venv .venv && .venv/bin/pip install
'pip<24.1' && .venv/bin/pip install --no-deps -r requirements-openstates.txt`. The `pip<24.1`
step matters — a newer pip breaks one of the pinned deps' build.

## api-v3 / infra scripts

- **`start-os-api.sh`** — boot-time launcher for the containerized api-v3 stack
  (`docker-compose -f deploy/docker-compose.ddp.yml up -d`). Runs as a **system LaunchDaemon**
  (`com.ddp.openstates-api`, `/Library/LaunchDaemons/`), so it can start before CAMS's
  `ddp-agents_default` network/`ddp-agents-redis-1` exist — reaches Docker via the Colima socket
  directly (`DOCKER_HOST`) and bounded-waits (5s×60) for both dependencies rather than
  fail-fast-exiting. Origin: `ddp-agents`'s `PLAN-cams-hardening-isolation.md` Phase 2. **This
  wait/retry shape (docker socket → dependency network → dependency container) is the template
  for any new service that also depends on CAMS's shared Redis/network** — don't write a
  different probing loop. **Also ensures `bulk_dataexport` exists** (idempotent
  `create_all(checkfirst=True)` via `docker exec` into the api-v3 container, using api-v3's own
  `DataExport` model as schema source of truth) and then smoke-tests
  `GET /jurisdictions/{iso2}?include=legislative_sessions` for all 7 tracked jurisdictions,
  alerting to Slack on either failure. `bulk_dataexport` is part of openstates.org's own bulk-CSV-
  export Django app, not the OCD/pupa scraping schema `openstates-core`'s `os-initdb` creates —
  so it's absent from a freshly-initialized DDP database, and `JurisdictionPagination`
  (`api-v3/api/pagination.py`) always selectinloads `legislative_sessions.downloads` alongside
  `legislative_sessions`, 500ing that include for every jurisdiction until the table exists. At
  the time of this fix api-v3 was pristine/unpatched, so schema gaps like this one belonged here,
  in `start-os-api.sh`, not in a hand-edited api-v3 checkout — see
  `notes/openstates-jurisdiction-sessions-500-root-cause-20260729.md` for the full incident
  (OPEN-12) and why the ticket's original back_populates diagnosis was wrong. **That diagnosis
  mattered again a few hours later:** api-v3 became DDP's fourth formal fork the same day
  (`Digital-Democracy-Project/api-v3`), with a first patch (PR #1) that fixes the very
  back_populates mismatch this note's incident ruled out as harmless. Confirmed live 2026-07-29
  that the table fix alone is sufficient — the endpoint returns 200 in ~35ms today running the
  *original* unpatched `jurisdiction.py` (neither the local checkout nor the running image has
  picked up PR #1). Kept anyway as legitimate upstream hygiene, not reverted — see
  `PLAN-fork-management.md` §1a for the fork's status and the still-open gap between what's merged
  and what's actually deployed, and `PLAN-open-states.md` Appendix D for the full reconciliation.
- **`backup-openstates-db.sh`** — nightly `pg_dump -Fc` of the dedicated Postgres, keep-7 local
  copies (`ls -1t ... | tail -n +8 | xargs rm -f` — the same "keep-N" idiom `run-scrape.sh` uses
  for gzipped log archives). Off-host S3 push is wired but commented out (blocked on AWS creds —
  WS9). Shares the Slack-alert-on-failure pattern with `run-scrape.sh` (see above).
- **`deploy/`** — DDP-owned deploy assets for api-v3, kept **out of** the public `api-v3/`
  checkout on purpose (so that checkout stays pristine/upstream-mergeable):
  `docker-compose.ddp.yml` (live stack, build context → `../api-v3`), `Dockerfile.ddp` (adds
  `psycopg2-binary==2.9.9` for Postgres-16 SCRAM auth on arm64 — the stock pin links an old
  libpq that can't do `scram-sha-256`), `docker-compose.stopgap.yml` (pinned rollback target,
  points at the old CAMS-shared DB on :5432), `Dockerfile.ddp.dockerignore`.

## `quality_check.py` — live-vs-replica data quality diff (repo root)

Samples bills/people from the local DB, fetches the same records from both `localhost:8002`
(local api-v3) and `v3.openstates.org` (live, real API key), diffs key fields. `Report` class
gives a uniform ✓/✗/~/`-` console output — **reuse this class for any new comparison/audit
script's output** rather than hand-rolling print statements. `OCD_TO_CODE` is the canonical
OCD-jurisdiction-string → short-code mapping for the 7 non-US state jurisdictions this repo
tracks (`fl wa mi ut al ma az`) plus `us` handled separately — if a new script needs this
mapping, import/copy from here, don't re-derive it from the OCD URIs inline.

`compare_bills()`'s vote-tally-mismatch branch (OPEN-32) already does the specific-voter and
blast-radius diagnosis that OPEN-26 (VA, Bennett-Parker) and OPEN-28 (MI, mass-vote-day) both
had to do by hand — **don't write a new one-off diffing/corpus-scan script for the next
"one shared date, many bills" finding; call these instead**:
- `diff_voters(lv, rv)` / `describe_voter_diff(local_only, live_only)` — pure functions that
  diff two paired vote events' per-voter `votes[]` lists (not just the aggregate `counts[]`
  tally) and format the specific differing voter(s)/option(s). Fires automatically inside
  `compare_bills()` whenever `tally(lv) != tally(rv)`; detail is folded into that same WARN.
- `count_shared_date_signature(conn, jurisdiction_code, session, date, voter_signature,
  exclude_identifier, cache=None)` — one parameterized local-Postgres query (no live-API
  budget spent) sizing how many other local bills in the same jurisdiction/session share the
  same voter-diff signature on that date. Wired into `compare_bills()` automatically when it's
  called with `conn=`/`jurisdiction_code=`/`session=` (all 3 optional, default `None`) — see
  `main()`'s bill loop, `run_coverage_check()`, and `run_tier2_only_check()` for the call shape.
  Pass a shared `blast_radius_cache={}` dict across a whole run so a repeating signature (266
  bills in OPEN-26's case) only queries once.

## Bill-version ordering & diff backfills (`openstates-core/openstates/cli/text_extract.py`)

`archive_bill_versions()` used to walk `bill.versions.all()` directly and trust whatever order
Postgres happened to return for `diff_from_previous_version`'s lineage — `BillVersion` has no
`Meta.ordering` and no reliable timestamp. OPEN-34 (2026-08-06/07) audited every tracked
jurisdiction and found that accident is inconsistent (forward for FL/MI/AZ mostly, backward for
VA/UT/US, doesn't fit a binary model at all for WA/MI's substitute-heavy bills) — **don't assume
DB row order is chronological for any bill-version work; use these instead**:
- `_note_stage(note)` / `_version_sort_key(note, date)` — classify a `version_note` into a
  content-based stage rank (never DB order), with `BillVersion.date` used as a same-stage
  tiebreaker when it's actually populated (only reliable for US federal, ~99.4%). A note
  matching no known stage returns `_STAGE_UNKNOWN` — the caller excludes it from any diff
  lineage entirely rather than guessing a position. If you're adding a new jurisdiction or
  hitting an unrecognized note shape, extend the stage table here, don't reorder query results.
- `os-text-extract recompute-diff-order <state|all> [--dry-run|--commit]` — recomputes
  `diff_from_previous_version` for already-archived rows from already-stored `raw_text` (no
  re-fetching), mirroring `os-text-extract archive`'s dry-run-then-commit discipline. Use this
  any time the stage table changes, or to correct existing wrong diffs after finding a new
  jurisdiction-specific ordering issue — don't hand-write a one-off correction script.

## Motion classification tooling

- **`classify_motion(jurisdiction, motion_text, bill_action=None)`**
  (`openstates-scrapers/scrapers/classify_motion.py`) — the actual classification logic, **YAML-
  driven** from `openstates-scrapers/scrapers/config/motion_classification.yaml` (one block per
  jurisdiction: `not_passage`/`committee_passage`/`passage` regex lists, optional `preprocess`
  step, optional `bill_action`-based override for VA). Called live by the scrapers at scrape time.
  **This is the single source of truth for "what does this vote's motion text mean" — a new
  jurisdiction's classification rules are a new YAML block, not new Python.**
- **`backfill-motion-classification.py`** (repo root) — one-time/idempotent backfill that
  re-runs `classify_motion()` against every existing `VoteEvent` row in Postgres (for votes
  scraped before a classifier fix shipped). `JURISDICTION_MAP` here is the OCD-string→short-key
  mapping for classification purposes specifically — a *different* mapping shape than
  `quality_check.py`'s `OCD_TO_CODE` (this one also includes `va`, not present there) but the
  same idea; if you're about to write a third one of these OCD-jurisdiction maps, check whether
  one of the two existing ones can just be imported instead. `--dry-run` prints without writing.
- **`audit-motion-texts.py`** (repo root) — read-only report: every distinct `(motion_text,
  classification)` pair per jurisdiction with vote/pass/fail counts, written to
  `motion-text-audit/<jurisdiction>.md`. Use this to find motion text patterns the YAML config
  doesn't cover yet, before hand-writing new regexes.

## Cross-cutting conventions (don't reinvent these)

- **DB connection defaults** — every Python script here defaults to
  `localhost:5433 / openstates / openstates:openstates_dev` (the dedicated Postgres, not CAMS's
  shared :5432). `quality_check.py` reads `DATABASE_URL` if set; the others hardcode the same
  values or read individual `OPENSTATES_DB_*` env vars. Match whichever pattern the file you're
  editing already uses.
- **Module name is `usa`, not `us`** — the scraper module for US Congress is `usa` (jurisdiction
  short-code in the DB is still `us`). Get this wrong and `run-scrape.sh usa ...` 404s.
  **`os-text-extract archive` is subject to this too, in the opposite direction** — it takes
  the DB abbreviation (`us`), not the scraper module name, so `os-text-extract archive usa`
  raises `KeyError: 'USA'` (reads like federal isn't supported at all; it is — `archive us`
  works fine). `run-archive.sh` translates this automatically; calling `os-text-extract`
  directly, use `us`. Cost real time twice (2026-07-24, then again 2026-07-31) before this
  line existed.
- **`session=` argument shape** — `run-scrape.sh <state> "session=<id>"`, quoted as one string
  because some jurisdictions pack extra key=value pairs in there (`"session=119 chamber=lower"`
  for US House/Senate, scraped as two separate invocations).
- **Log file locations** — `logs/scraper.log` (all scrape/import activity, rotated in-script at
  50MB/keep-7 by `run-scrape.sh`'s `rotate_scraper_log()`), `logs/os-api.log` (api-v3 boot +
  backup script), `logs/last-run/` (resumability markers), `logs/backfill/` (one-off backfill
  driver output), `logs/db-backups/` (pg_dump files). A new script's logs belong under `logs/`
  in one of these shapes, not a new top-level directory.

---

## Discipline checklist for any new script in this repo

1. **Does `run-scrape.sh` already do this?** Most "scrape X" or "import X" needs are already a
   flag or a state name away from working, not a new script.
2. **Resumability?** Reuse the `logs/last-run/*.ts` marker convention (either through
   `run-scrape.sh` directly, or by checking the same marker file the way
   `backfill-fl-historical.sh` does) — don't invent a second state-tracking file format.
3. **Logging?** Copy the exact `log()` one-liner from a sibling script (bash) — pick the local-
   time variant (`run-scrape.sh` family) or the UTC variant (`start-os-api.sh` family) to match
   whichever log file you're appending to.
4. **Failure alerting?** If it needs a Slack alert, copy `on_failure()`/`slack_fail()`'s
   token-read-from-`ddp-agents/.env` + fail-open pattern — don't add a new alerting path.
5. **Touching `openstates-core`'s checkout?** Respect the worktree lock protocol
   (`/tmp/ddp-openstates-scrapes/`) both ways — check it before mutating, and if your script runs
   for a long time while reading the checkout, drop a marker in it.
6. **OCD jurisdiction string ↔ short code mapping?** Check `quality_check.py`'s `OCD_TO_CODE` and
   `backfill-motion-classification.py`'s `JURISDICTION_MAP` before writing a third one.
7. **Cross-repo?** If the work touches how `ddp-sync`, `ddp-agents`/CAMS, or `ddp-broker-py`
   consume this repo's output, check their own PLAN docs too — `RUNBOOK.md`'s "Scraper state"
   and "Services" sections list what's currently live and what depends on what.
8. **Writing or extending a bash script?** This Mac's `/bin/bash` is **3.2.57** — frozen there
   permanently (Apple won't ship a GPLv3-licensed bash newer than 3.2) — not bash 4+. `$BASHPID`
   and `declare -A` (associative arrays) both silently don't exist / error out; found the hard way
   2026-07-30 building `run-scrape.sh`'s import-as-you-go fix (`PLAN-incremental-scraping.md`,
   "Reopened 2026-07-30", implementation note). Same goes for `stat`/`find`/`date` flags — this
   machine's are BSD, not GNU (`stat -f %m`, not `stat -c %Y`). Test any new bash against `bash -n`
   *and* by actually running it here — bash 4+ syntax looks completely ordinary and gives no
   warning before failing on this specific machine.
