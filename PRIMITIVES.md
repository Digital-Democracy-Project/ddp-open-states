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
- **No-op vs. unreachable (OPEN-152, 2026-08-25)** — `"no objects returned from"` alone is **not**
  enough to call a run a no-op, and treating it that way was a data-loss bug, not a cosmetic one.
  openstates-core raises that same `ScrapeError` whenever a scraper yields nothing, so it means
  both "nothing changed since the cutoff" *and* "I could not read the site". Taking the no-op path
  for the second case recorded `ok:0:0:0` as a **measurement** and advanced the watermark past a
  window that was never examined — so the bills filed in it were skipped permanently, and the run
  reported success. `run-scrape.sh` now consults
  **`scrape_output_shows_unreachable_site()`** (defined in `import-summary.sh`, so the matcher is
  testable without the script) before `finish_no_op()`; an unreachable run fails instead, leaving
  the watermark where it was so the next run re-covers the window. The matcher greps the scrape
  output for site-unreachable markers (WAF blocks, unrecognised block pages, "neither a results
  page nor a usable bill page") and first drops lines where those phrases are **negated**, so a
  future benign `no WAF block detected` diagnostic can't turn every quiet week into an alert.
  **Add a new marker to `_SCRAPE_UNREACHABLE_MARKERS`, not a second matcher** — and add a fixture
  to `test-scrape-outcome.sh` in the same change, because both failure directions here are silent.
- **Same-jurisdiction scrape lock (OPEN-154, 2026-08-25)** — `/tmp/ddp-openstates-scrape-locks/$STATE`,
  taken for the whole run and released by the `EXIT` trap. **This is not the same lock as the
  worktree lock below, and the difference has already misled a reader once.** The worktree lock is
  keyed on PID and coordinates scrapes against `apply-local-patches.sh`; it does nothing to stop
  two scrapes of the *same jurisdiction* running at once, which openstates-core makes destructive
  rather than merely wasteful — `do_scrape()` wipes `$SCRAPED_DATA_DIR/$STATE` at scrape start, so
  the second run deletes the first's collected bills mid-flight. Keyed on `$STATE` and **not** on
  `$SCRAPE_KEY`: two sessions of one state share the data directory, so keying on the session would
  let them collide. `$STATE` is validated against `*[!a-z0-9_]*` before any path is built, since it
  reaches a `rm -rf`. A lock whose holder PID is gone is reclaimed; a lock with no readable PID
  ages out after 24h. Losing the lock also sets `DO_NOT_RETRY_FLAG` — exit 90 alone does **not**
  stop `run-scrape-retrying.sh`, which decides on the flag file, so without it the wrapper would
  have spun through every attempt against a jurisdiction that was already being scraped.
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
  same marker directory**, not add its own. It protects the *code checkout*, keyed on PID — it
  says nothing about which jurisdiction is being scraped, so it never prevented two scrapes of
  the same state from running together. That is the separate lock documented above.
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
- **Branch hygiene (OPEN-99): once a PR merges, delete its fix branch, local and remote.** This
  directly prevents a recurrence of the exact failure mode the worktree-lock/freshness-guard
  bullets above exist for — a merged branch left checked out (or just left lying around) is
  how `fix/fl-floor-vote-source-url` sat stale for 2 days in 2026-07-23's incident. Only ever
  delete a branch you've personally confirmed is merged — never on the strength of a `[gone]`
  local tracking marker alone (that only means the remote ref disappeared, not that the content
  is safely in `main`; the 2026-08-21 sweep found a real counter-example, see the note below).
  Safe sequence, either repo:
  ```
  git fetch <remote> --prune
  git merge-base --is-ancestor <branch> <fork-main>   # must print nothing / exit 0
  git push origin --delete <branch>                   # remote
  git branch -d <branch>                               # local, each checkout that has it
  ```
  `<fork-main>` is `origin/main` for `openstates-scrapers`, `ddp/main` for `openstates-core`'s
  dev checkout specifically (its `origin`/`ddp` remotes are still the pre-2026-08-01 reversed
  naming — see the remote-convention bullet above; the production checkout uses `origin/main`
  for both repos). If the branch isn't yours, or you're not sure it's genuinely abandoned
  (not just merged), ask before deleting rather than sweeping it in. GitHub's own
  "automatically delete head branches" repo setting would make this automatic instead of
  manual, but as of 2026-08-21 it's off on every DDP fork checked (`openstates-core`,
  `openstates-scrapers`, `api-v3`) — worth a human turning on in each repo's Settings page.

  One-time sweep done 2026-08-21 (OPEN-99): removed 4 merged remote branches + 3 stale local
  ones from `openstates-scrapers`, 4 merged remote branches (plus the two retired
  cherry-pick-model branches, `cherry-pick-line`/`ddp-patches` — confirmed genuinely unused via
  `gh pr list --state open` on both forks, empty) + 2 stale local ones from `openstates-core`,
  across both the production checkout and this dev checkout's own nested clones. Full
  branch-by-branch audit trail (names, commits, which were deliberately left alone and why):
  `notes/open-99-branch-hygiene-sweep-20260821.md`.

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
- **`refresh-api-v3.sh`** (OPEN-101, repo root) — the repeatable pull/rebuild/redeploy cycle
  api-v3 never had one of (unlike `apply-local-patches.sh` for `openstates-core`/
  `openstates-scrapers`): `git pull origin main` in the production `api-v3` checkout, then
  `docker-compose -f deploy/docker-compose.ddp.yml build api` and `up -d --force-recreate api`
  — **always with an explicit `api` service argument**, never a bare `up -d`/`--force-recreate`.
  That distinction is the entire point: the first-ever manual redeploy (2026-07-29, PR #1/#2)
  ran a bare `--force-recreate` with no service name, which also recreated the *shared*
  dedicated Postgres (`ddp-openstates-postgres-1`, :5433 — the same DB native scrapers write
  to) and killed two live scrapes (`va`, `ut`) mid-write. Deliberately skips the worktree-lock/
  scrape-running check `apply-local-patches.sh` has — api-v3's checkout is only ever read at
  `docker build` time (baked into the image), not live by a running process the way
  `openstates-core`/`openstates-scrapers` are, so scoping every command to `api` already keeps
  the shared Postgres untouched by construction. Run manually after merging a PR to the fork's
  `main` — no cron yet, same "not worth it until deploy volume justifies it" call
  `PLAN-fork-management.md` §5.F made for drift visibility.

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
- `note_stage(note)` / `version_sort_key(note, date)` — classify a `version_note` into a
  content-based stage rank (never DB order), with `BillVersion.date` used as a same-stage
  tiebreaker when it's actually populated (only reliable for US federal, ~99.4%). A note
  matching no known stage returns `STAGE_UNKNOWN` — the caller excludes it from any diff
  lineage entirely rather than guessing a position. If you're adding a new jurisdiction or
  hitting an unrecognized note shape, extend the stage table here, don't reorder query results.
  Public, importable (OPEN-91): `openstates-core/openstates/utils/version_ordering.py`, not
  private to `text_extract.py` anymore — `archive_bill_versions()`/`recompute_bill_diff_order()`
  still use it via the same old `_note_stage`/`_version_sort_key`/`_STAGE_*` names, aliased back
  from the new module so neither call site changed.
- `os-text-extract recompute-diff-order <state|all> [--dry-run|--commit]` — recomputes
  `diff_from_previous_version` for already-archived rows from already-stored `raw_text` (no
  re-fetching), mirroring `os-text-extract archive`'s dry-run-then-commit discipline. Use this
  any time the stage table changes, or to correct existing wrong diffs after finding a new
  jurisdiction-specific ordering issue — don't hand-write a one-off correction script.
- **api-v3 has its own copy of this classifier** (`api-v3/api/version_ordering.py`, OPEN-92) —
  api-v3's bill-detail endpoint (`include=versions`) used to resolve "latest"/"previous" via a
  naive `(date, note)` sort and needed the same fix, but api-v3 installs `openstates` from PyPI
  rather than this fork, so it can't import the module above directly yet. The copy's own
  docstring says to keep it byte-for-byte identical to this one — if you're changing the stage
  table here, port the change to api-v3's copy too, not the other way around. Re-pinning api-v3's
  `openstates` dependency to this fork (so the copy can be deleted) is a known, larger follow-up,
  not yet done.

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

## Per-jurisdiction configuration: which mechanism to use (OPEN-120/OPEN-121, 2026-08-22)

Before adding a new "this jurisdiction needs different behavior" special case anywhere in
`openstates-core`/`openstates-scrapers`, check whether it fits one of the two conventions below
instead of inventing a third. A full audit (2026-08-22, `jurisdiction-config` Jira label) found
per-jurisdiction logic expressed **six different, independently-invented ways** across the whole
DDP stack — two of them (below) are the ones worth deliberately standardizing on *within these two
repos specifically*; the others (a live DB table in `ddp-broker-py`, YAML in `ddp-sync`, plain
per-state code folders) fit their own repo's different constraints and aren't being changed.

- **A plain settings file, for simple per-state text patterns.**
  `openstates-scrapers/scrapers/config/motion_classification.yaml`, loaded once by
  `classify_motion.py` (see "Motion classification tooling" above), is the template: one YAML
  block per jurisdiction holding regex lists, with a small named-function registry
  (`_PREPROCESSORS`) for the rare case plain regex data can't express — never an inline branch
  for that case either.
- **A Python dict of richer objects, when the config needs more than plain data.**
  `openstates-core/openstates/utils/resilience_profiles.py`'s `RESILIENCE_PROFILES` is the
  template: one dict entry per jurisdiction holding real objects (a `CookieProvider` instance,
  rate limits, feature flags) that YAML can't naturally hold. Turning on WAF/cookie resilience
  for a newly-blocked jurisdiction is "add a `RESILIENCE_PROFILES` entry," not another hand-wired
  branch copied from Michigan's original one-off machinery.

**Why not a database table (like `ddp-broker-py`'s `JurisdictionEligibilityConfig`) here:**
`openstates-core`/`openstates-scrapers` are forks that get merged from a public project DDP
doesn't control (see `apply-local-patches.sh` above) — every DDP-only migration added to either
repo is a standing risk of colliding with whatever the public project adds on its own next. This
already happened for real: OPEN-98's 2026-08-21 upstream merge hit a genuine Django
migration-number collision (DDP's own `0046_billversiondocument.py` vs. upstream's unrelated new
`0046_bill_indexes.py`, both descending from the same parent), resolved with a real merge
migration, not a hypothetical risk. `ddp-broker-py` doesn't have this problem — nothing else
changes its database out from under it — so its DB-table convention stays right for that repo
specifically, just not portable here.

**Per-jurisdiction settings in shell scripts and the scheduler (OPEN-124, decided 2026-08-22).**
The survey above found a seventh, unnamed mechanism outside these two repos: plain lists of state
abbreviations sitting in shell scripts (`run-scrape.sh`'s `--allow_duplicates` states,
`activate.sh`'s `ARCHIVE_ENABLED_STATES`). It falls outside the `openstates-core`/`openstates-scrapers`
decision above by construction — those files are entirely DDP's, with no upstream to collide with —
so nothing covered it. The rule now:

- **Anything a scheduler decides goes in `ddp-sync`'s `config/sync_schedule.yaml`**, as an
  `{enabled, jurisdictions}` block read by a small `_*_eligible()` helper in the relevant pipeline
  module. Which jurisdictions are enrolled in a rollout, which are opted out of retries, which get
  a fallback — all of these. `ddp-sync` is what actually invokes `run-scrape.sh`, it already
  resolves per-jurisdiction opt-ins this way (`secondary.scrapebot_fallback`, and now
  `openstates_scrape.sweep_import`), and keeping the decision there leaves the shell scripts free
  of new conditionals. **Do not add a new `$STATE` test in bash for this.**
- **Only genuine wrapper-local flags stay in the shell script** — a flag the scheduler has no
  opinion about, like `--allow_duplicates`, which is a property of a jurisdiction's data rather
  than of a rollout. Where one is needed, use the **flat comma-list** shape
  (`ARCHIVE_ENABLED_STATES="fl,ut,az,…"`) rather than a chained
  `[ "$STATE" = "mi" ] || [ "$STATE" = "fl" ] || …`. The chained form has now been extended four
  times and silently missed `ma` once (OPEN-55), which cost a completed 9,496-bill backfill its
  entire import.

**The line is semantic ownership, not which process passes the argument.** `ddp-sync` invokes
`run-scrape.sh` and could in principle set any of its arguments, so "the scheduler passes it" is
not the test. Ask instead what the setting *is*: orchestration, eligibility and timing — who is
enrolled, who is opted out, when — belong to the scheduler. A jurisdiction data-behaviour flag
that must hold **every time the wrapper runs, regardless of schedule** is wrapper-local. A setting
can arrive as a shell argument and still be scheduler-owned policy, and vice versa.

Why the split rather than consolidating everything: the two categories fail differently, and need
different visibility. A rollout gate set wrong changes *when* data lands for a live jurisdiction,
silently, and needs to be reviewable in one place. A wrapper flag set wrong fails locally and
loudly — which is *not* the same as cheaply: OPEN-55's missing `ma` entry aborted the import of a
completed 9,496-bill, ~15-hour MA scrape. Loud, localised, and expensive. Deciding both in the
same place would mean either putting scrape-time data quirks into the scheduler's config or putting
rollout state into a bash array.

`run-scrape.sh:140`'s existing `--allow_duplicates` conditional is deliberately left as-is here —
converting it inside unrelated work is how you get an unreviewable diff. It is tracked as
**OPEN-131** rather than left as an ambient inconsistency, since an unowned counter-example sitting
at exactly the spot this rule is about would read as implicit permission.

**What's still using neither convention, on purpose, pending cleanup:** bare inline
`if jurisdiction_name == "Virginia":`-style conditionals dropped directly into shared code —
found only in `openstates-core/openstates/cli/text_extract.py`'s version-diffing path (WA/MI/VA/AZ
text-cleanup dispatch, OPEN-7/9/10/11). Tracked as **OPEN-121** — migrate opportunistically
whenever that code is already being touched, not as a big-bang rewrite. Two inline checks in the
same file (an FL TLS-cipher workaround, a CA jurisdiction-ID check) are byte-for-byte identical to
the public project's own code and are deliberately *not* candidates — rewriting those would only
add diff noise against every future upstream merge for a problem DDP doesn't own.

**What's explicitly not a "per-jurisdiction config" problem, even though it looks like one:**
`version_ordering.py`'s stage-classification table (see above) knows MI writes `"(S-1)"`, WA
writes `"Second Substitute"`, etc., but it isn't jurisdiction-*keyed* — it's one shared cascade of
patterns evaluated in a fixed order regardless of which state a bill is from, by design. Forcing
it into a per-jurisdiction registry would change its semantics, not just its storage — don't.

**Per-jurisdiction credentials — the mechanism already exists, don't invent one (OPEN-126,
decided 2026-08-22).** Some jurisdictions gate their API behind a registered key. This is a
*fifth* thing that can be per-jurisdiction, and unlike the four above it is a secret, so it needs
saying where it goes. It already has an answer, and the answer is "what this repo already does":

- **The value goes in `ddp-open-states/.env`** (gitignored, `.gitignore:31`, not tracked).
- **`activate.sh:6` already loads it** — `[ -f "$SCRIPT_DIR/.env" ] && set -a && source
  "$SCRIPT_DIR/.env" && set +a`. `set -a` exports everything it sources, so anything in `.env`
  is in the scraper's environment. `run-scrape.sh:47` sources `activate.sh`, so a scrape already
  gets it. **No new loader, no new file, no code change in either fork.**
- **The variable name must be byte-for-byte the name the scraper already reads** — `DC_API_KEY`,
  `INDIANA_API_KEY`, `NEW_YORK_API_KEY` — never a DDP-invented alias.

`.env` and `activate.sh` are not competing options, which is how the ticket first framed them:
`activate.sh` is the *loader* and is committed, `.env` is the *store* and is not. That split is
already the pattern here and it is the right one — the committed file carries the mechanism, the
ignored file carries the secret. Putting a key in `activate.sh` is wrong for the obvious reason;
putting the loader in `.env` isn't a thing.

**This is not new ground: `va` already does exactly this in production.** `VA_API_KEY` sits in
`.env` today and `openstates-scrapers/scrapers/va/bills.py:79` reads it, for a jurisdiction in
the live rotation. `run-all-scrapes.sh:32` even carries the comment `# va requires VA_API_KEY in
.env`. So the convention below is a written-down version of what already works, not a proposal.

**Why not AWS Secrets Manager**, notwithstanding that the fleet uses it: there is no read path
from this machine. `~/.aws` is root-owned with no readable credentials and no `AWS_*` is set in
the shell; AWS is reachable only through the sudo-gated, root-owned S3 proxy wrappers
(`ddp-infra/Production_S3_Wrappers.md`), which do S3 objects, not secrets. More to the point, the
fleet's own Secrets Manager consumers **already fall back to `.env` on this machine by design** —
`ddp-sync/src/ddp_sync/config.py:263-276` catches the failure, logs `"Secrets Manager
unavailable"`, and calls `_load_from_env()`. So `.env` is not a downgrade from the fleet
convention; on the Mac Studio it *is* the fleet convention, and Secrets Manager is the EC2 half
of the same one. Revisit only if scrapers ever run on EC2.

Because `.env` is **sourced by a shell**, not parsed by `python-dotenv`, entries must be
shell-safe `KEY=value` lines — quote any value containing spaces, `#`, `$` or a quote, and don't
expect `dotenv`-style escaping to work. Nothing here reads `.env` from Python.

**The exact list of credentialed jurisdictions, and why only `dc` breaks at import.** Five
jurisdictions want a credential — one optionally — and the failure shape differs by *where the
lookup sits*, not by policy. **Inventory current as of `upstream/main` `9a8ec1331` (2026-08-14);**
re-derive it after a big upstream merge rather than trusting this table forever:

| Jurisdiction | Variable | Required? | Read where | Fails when |
|---|---|---|---|---|
| `va` | `VA_API_KEY` | required | `os.getenv` + explicit absence check, in a method | scrape time, with a good message |
| `usa` | `CONGRESS_GOV_API_KEY` | **optional** | `os.environ.get(..., None)` guard, in a method | never — degrades, events only |
| `in` | `INDIANA_API_KEY` | required | bare `os.environ[...]`, in `__init__`/`get_session_list` | scrape time, bare `KeyError` |
| `ny` | `NEW_YORK_API_KEY` | required | bare `os.environ[...]`, in methods | scrape time, bare `KeyError` |
| `dc` | `DC_API_KEY` | required | bare `os.environ[...]` **in a class body** (`bills.py:23`) | **import time**, bare `KeyError` |

`dc` is the only one whose lookup is a class attribute, so it evaluates at class-definition time:
`import scrapers.dc` → `__init__.py:4` → `bills.py:15` (class body) → `bills.py:23` → `KeyError`.
That is a code-shape accident, not a property of needing a credential — which is why "DC can't be
imported" and "DC needs a key" are two different facts and only the second one generalizes.
(`docker-compose.yml:19-33` also passes `AR_FTP_*` and `VIRGINIA_FTP_*` through, but no scraper
under `scrapers/` reads either name — verified by grep, stale entries, ignore them.)

**Making the absent-credential failure legible: upstream already has the template, so don't write
a DDP one.** `scrapers/va/bills.py:70-74` is the shape wanted — it names the jurisdiction, links
the registration page, warns that registration takes days, and points at a fallback scraper:

```python
if not os.getenv("VA_API_KEY"):
    self.error(
        "Virginia requires an LIS api key. Register at https://lis.virginia.gov/developers \n API key registration can take days, the csv_bills scraper works without one."
    )
    return
```

That block is **upstream's own code, untouched by DDP**. So is `dc`'s bare `KeyError`:
`scrapers/dc/bills.py` and `scrapers/dc/__init__.py` are byte-for-byte identical to
`upstream/main`, and the only DDP commit touching `scrapers/dc/` is an upstream merge. Upstream
therefore contains both the good pattern and the bad one, and DC's is upstream's inconsistency to
own. Per the same rule applied to `text_extract.py`'s FL/CA checks above, **do not rewrite it
locally** — it would add diff noise to every future upstream merge for a bug DDP didn't write. If
someone wants it fixed, the correctly-placed fix is a small **upstream PR** porting VA's guard to
`dc` (and to `in`/`ny`), which costs DDP no merge surface and helps everyone.

**For the import sweep specifically, OPEN-125 already handles it — and only that.**
`check-scraper-imports.sh` classifies an *import* failure into `MISSING MODULE` / `MISSING
CREDENTIAL` / `OTHER FAILURE` at the *caller*, by inspecting the exception — an `ENV_VAR`-shaped
`KeyError` naming something genuinely absent from `os.environ` is reported as credential-gated and
**exits 0**, while a `ModuleNotFoundError` or any other break exits 1. That is the right place for
the distinction: it lives in DDP's own script, needs no upstream change, and means a credential we
have deliberately not bought does not make the sweep noisy. **Don't duplicate that classification
anywhere else** — if a second consumer ever needs it, factor it out of that script rather than
re-deriving the heuristic.

**Be precise about what that does and does not make legible: import-time only, which today means
`dc` alone.** `in` and `ny` read their key inside a method, so they import *cleanly without a
credential* and the sweep will never flag them — then fail at scrape time with a bare `KeyError`
that OPEN-125's script never sees. A green `check-scraper-imports.sh` is therefore **not** evidence
that a jurisdiction's credential is present or working. Nothing in this repo has made a
method-time missing credential legible, and nothing here should: per the paragraph above, the fix
for `in`/`ny` belongs upstream.

**Onboarding a credentialed jurisdiction, then, depends on where its lookup sits** — check the
table before choosing how to verify:

- **Add** `<NAME>=<value>` to `.env` using the scraper's own variable name (shell-safe, quoted if
  needed).
- **Import-time gate (`dc` today):** `check-scraper-imports.sh` should stop listing it as
  credential-gated. That is a real check, and it is sufficient for this class.
- **Method-time gate (`in`, `ny`, `va` — the common case):** the import check proves nothing. The
  only thing that does is **running the scrape** — `run-scrape.sh <state>`, which sources
  `activate.sh` and so gets `.env` — and confirming it fetches instead of raising `KeyError`. Do
  this on a small/incremental run before enrolling the jurisdiction in the schedule.

The one gap left is discoverability of the *names*: this repo has no `.env.example` (four other
fleet repos do), so the set of variables `.env` is expected to hold is currently only findable by
grepping the scrapers. Worth adding when someone next touches `.env`; not worth a dedicated change
on its own.

**`dc` specifically is parked, and the gating question is scope, not the key.** DDP holds no DC
credential and nobody can self-serve one — LIMS publishes no registration page, so it needs a
human to ask DC Council. Before anyone spends that ask: `PLAN-push-button-onboarding.md` already
excludes **DC and the territories from the 50-state goal** ("noted so nobody probes them by
accident"), and the broker really does refuse DC — `ddp-broker-py`'s
`fetch/interfaces/OpenStates/openstates_util.py:71` raises `NotImplementedError("Washington, DC
districts are not currently supported.")`. That exclusion is about the broker's *congressional-
district* resolution rather than DC Council bill scraping, so it is not literally the same
question — but the documented default is "DC is out of scope," and no credential should be
requested until that is deliberately revisited. `in` is the one that makes this section urgent
anyway: it is on the pilot shortlist (`NC, GA, CO, OH, IN`) and needs `INDIANA_API_KEY`, so the
first credentialed onboarding DDP actually does is more likely Indiana than DC.

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
- **`test-*.sh` shell tests** — `bash test-<thing>.sh`, no framework, no network, no database, no
  production paths: a `mktemp -d` per run, fixtures written as text files, `ALL PASS (N
  assertions)` and exit 0 or the first failing assertion and exit 1. Five of these now exist
  (`test-import-summary.sh`, `test-check-scrape-staleness.sh`, `test-scrape-outcome.sh`,
  `test-no-op-side-effects.sh`, `test-scrape-lock.sh`) and they all share that shape — copy the
  nearest one rather than introducing a runner. Two of them drive **`run-scrape.sh` itself**
  against a stub `os-update`, which is the only way to assert what the script *does* with a
  decision rather than just what a matcher returns.
- **Testing `run-scrape.sh` requires overriding `activate.sh` (OPEN-152, 2026-08-25)** — the
  script sources `activate.sh`, which **unconditionally exports** `OS_UPDATE`,
  `SCRAPED_DATA_DIR`, `CACHE_DIR` and `SCRAPELIB_RPM`, clobbering anything the caller set and
  making the script untestable. It now captures a caller's `OS_UPDATE`/`SCRAPED_DATA_DIR`/
  `CACHE_DIR` before the `source` and restores them after, and `LOG_DIR` is overridable too. A
  test **must** set all of those plus **`SKIP_PATCHES=1`** — without the last one a test run
  git-pulls the live nested checkouts and then scrapes a real legislature site. Found the hard
  way, twice.

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
