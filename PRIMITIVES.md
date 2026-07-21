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
    ├─ apply-local-patches.sh          ← rebuilds openstates-core's local-patches branch (skip via SKIP_PATCHES=1)
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
  If a third script needs this, extract it rather than copy-pasting a fourth time.
- **Worktree lock (reader side)** — drops a PID marker at `/tmp/ddp-openstates-scrapes/$$` for
  the duration of the scrape, removed via `trap ... EXIT`. `apply-local-patches.sh` checks this
  directory (writer side, see below) before touching `openstates-core`, so a patch rebuild can't
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

**Scrapers and core are on different conventions — know which one you're touching:**
- `openstates-scrapers` is a **formal DDP org fork** (`Digital-Democracy-Project/openstates-scrapers`,
  since 2026-07-03). Fork `main` IS the patched state — no cherry-picking, no local branch
  rebuild. Day-to-day: `git checkout -b feat/x` → PR to fork `main`. This script does **not**
  touch it anymore (that block was retired in `8cca7a2`, Phase 2 of the fork plan).
- `openstates-core` still uses the **older cherry-pick convention**: this script does
  `git checkout main && git pull && git branch -D local-patches && git checkout -b local-patches`,
  then cherry-picks a short list of DDP-only fixes not yet merged upstream (currently just
  `d6653a5`, the `CACHE_DIR`/`SCRAPED_DATA_DIR` env-var fix). `cherry_pick()` silently skips a
  commit that upstream already merged (detects the "nothing to commit"/"is now empty" cherry-pick
  states) rather than failing — **reuse this helper** if a new script ever needs to cherry-pick
  onto a rebuilt branch; don't write a second one.
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
  different probing loop.
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
