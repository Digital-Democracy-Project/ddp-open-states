---
name: Existing primitives & building blocks inventory (ddp-open-states)
description: Catalog of every DDP-owned script, convention, and pattern already built on top of openstates-scrapers/openstates-core. Read this before writing new tooling — the scrape/import/backfill/patch pipeline already has answers for logging, resumability, alerting, and env isolation; don't re-derive them.
type: reference
---

# READ THIS FIRST — BEFORE WRITING NEW SCRIPTS

> **Sibling document: `LESSONS.md`.** This file catalogs the scripts that exist and the conventions
> they share. `LESSONS.md` records **what went wrong, what it cost, and the rule that came out of
> it** — written for whoever rebuilds the scrape path somewhere else (OPEN-180/OPEN-201). If you are
> replacing code rather than adding to it, read that one first: the code is replaceable and the
> incidents behind it are not.

> **State rules (OPEN-537).** A state's data rules (action order, action and bill labels, vote names,
> version stages, text clean-up) live in the openstates-scrapers and openstates-core forks, not in
> this repo's scripts and not downstream: parsing and the motion YAML in the scrapers fork,
> normalizing in core (today `version_ordering` and the `text_extract` cleaners and readers; later
> one file per state in `openstates/ddp_states/`), and per-state values in `jurisdictions.yaml`. See
> ddp-infra `PLAN-state-specific-handling.md` §4.2 (§4.1 is the contract the data must meet).

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

run-people-refresh.sh                        ← nightly driver that calls run-scrape.sh per jurisdiction
backfill-fl-historical.sh                    ← one-off historical driver, same run-scrape.sh calls, resumable
```

**Scheduling note:** the old ad-hoc per-repo nightly runner and the old `com.ddp.openstates-scraper`
launchd job are retired (OPEN-465) — scheduling moved to `ddp-sync`'s APScheduler on 2026-06-22 (see
`RUNBOOK.md` → "Services"). `run-scrape.sh` itself is still the live entrypoint either way; only what
*calls* it changed. Don't add new schedule logic here — add a job to `ddp-sync/config/sync_schedule.yaml`
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
  than duplicating cutoff logic). **A state whose manifest says `scrape.start_filter: false` never
  gets `start=`** (OPEN-501 follow-up, 2026-11-16): when a marker exists, `run-scrape.sh` asks
  `cloud_collector.py`'s own `scraper_takes_start()` (the cloud path's rule: `usa` reads `us`, a
  state with no entry keeps `start=`) and runs `false` states full, logging why; the marker is
  still written. A manifest that does not validate stops the run before scraping. One rule for both
  paths, no state list here; `test-start-filter.sh` pins it (al, nc, va, a manifest copy, a broken one).
- **`log()`** — `echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a logs/scraper.log`. Every DDP
  script in this repo defines its own copy of this exact pattern (`run-scrape.sh`,
  `run-people-refresh.sh`, `backfill-fl-historical.sh` — the last two write
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
  **OPEN-334** added two Michigan log lines (a retried block's marker/status/path, and what a cookie warm-up
  received); `test-scrape-outcome.sh` pins both as benign, so keep new diagnostics clear of the marker phrases.
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
- **Slack alert-on-failure** — `post_slack_alert TEXT [CHANNEL] [--source S] [--dedupe-key K] [--direct]` from **`lib/slack-alert.sh`** (OPEN-325, which
  is the extraction OPEN-43 asked for), sourced by `run-scrape.sh`, `run-archive.sh`, `backup-openstates-db.sh`,
  `start-os-api.sh` and `check-replica-health.sh`. The first two call it from `on_failure()` (fired via `trap 'on_failure' ERR`), the others from
  `slack_fail()`. It posts to `#automation-errors` as **CodeBot** (not the Slack app's own name, Agent Smith), reads
  `SLACK_BOT_TOKEN` and `CODEBOT_SLACK_USERNAME` / `CODEBOT_SLACK_ICON_EMOJI` from the environment first and then
  from `ddp-agents/.env`, JSON-escapes the text, and **always returns 0**: it never blocks or fails the script that
  called it, and a post it cannot send (no token, Slack refused) goes to stderr instead of vanishing. Before
  OPEN-325 each script carried its own `curl` (four copies, none setting an identity, none escaping the text). See
  the `lib/slack-alert.sh` section below. **Not yet live-verified against Slack** (PR #264, 2026-10-05).
  Since OPEN-436 a class-A call (`run-scrape.sh`, `run-archive.sh`, `backup-openstates-db.sh`) first tries CAMS's operator-alert
  route and falls back to the direct post on anything but a 2xx; class B (`start-os-api.sh`, `check-replica-health.sh`: alerts
  about CAMS or the replica themselves) pass `--direct`. Live on the Mac since 2026-10-28: `OPERATOR_ALERT_URL` is set in `ddp-agents/.env` (where this helper reads it) and the route and the closed-port fallback were both checked there; delete that line to go back to direct posts. No script here runs on EC2.
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
- **JSON completion record on the last line of stdout (OPEN-182, 2026-08-27)** — one object
  carrying `source`, `run_id`, `mode`, `status` and, on an `ok` run, `new`/`updated`/`noop`. It is
  `PLAN-scraper-execution-contract.md` §2, and it exists so a caller that cannot keep this
  machine's log files — a cloud runner — can still report what a run did. **It is additive**: the
  `SCRAPE SUMMARY` / `IMPORT SUMMARY` lines and the `.imported` marker are unchanged and still
  have live consumers (ddp-sync's failure classifier reads the log; `run-scrape.sh` reads
  `.imported` back on the next run).
  **Emitted from the EXIT trap, not from each exit site, and that is load-bearing** — the contract
  tells callers to read a missing record as a dead runner, so an exit path that forgot to emit
  would report a working run as a crash. A new exit path therefore needs **no** emit call of its
  own; it needs to set `COMPLETION_STATUS` to one of §3's four values (`ok`, `unparsed`,
  `unreachable`, `failed`) before exiting. Leaving it unset yields `failed`, which is the right
  default. **Do not compute the status inside the emitter** — it reports the decision the run
  already made, and a second derivation of it would drift from the marker file.
- **External per-source memory (OPEN-181, 2026-08-27)** — `scraper-memory.sh`, sourced by
  `run-scrape.sh`, syncs the watermark markers and any jurisdiction's cache-resident memory
  (today only Michigan's last-action baseline) with S3 through the existing
  `ddp-prod-s3-openstates-backups` wrapper. It is `PLAN-scraper-execution-contract.md` §4.
  **Off unless `SCRAPER_MEMORY_BACKEND=s3`**, in which case `SCRAPER_MEMORY_PREFIX` is
  mandatory — there is deliberately no default, because an object key has no checkout to follow
  and OPEN-159/OPEN-172 were both "a dev run wrote production's markers".
  **Three things not to undo:** (a) `scraper_memory_fetch` returns *three* values — fetched,
  absent, and could-not-tell — and the caller refuses to run on the third; collapsing it to two
  turns an S3 blip into a ~3,900-request full walk of Michigan, which is the outage §4 warns
  about. (b) The per-jurisdiction cache entry is a **glob**, not a filename template: production
  runs MI with no session argument, so the session in `mi_last_actions_<session>.json` is the
  scraper's, and a template yields `mi_last_actions_.json`. (c) The sync lives in the runner, not
  in the scraper — `openstates-scrapers` is a fork of a public project, and an S3 client inside
  `mi/bills.py` would conflict with every future upstream merge.
  `migrate-scraper-memory.sh --prefix <ns>` moves an existing checkout's memory into the store;
  dry run unless `--commit`. **The 2.8 GB HTTP cache is deliberately not part of this** — see the
  bottom of `scraper-memory.sh` for that decision and what it costs on a first cloud run.
- **`cloud_collector.py` (OPEN-201, 2026-08-29)** — the cloud collection runner, built fresh rather
  than a `run-scrape.sh` port (Ramon's build-fresh decision). Does only what collection needs: read
  memory (`S3Memory`, the same object layout `scraper-memory.sh` computes independently in bash —
  the two must never drift), decide full vs. incremental, invoke `os-update --scrape`, classify the
  outcome via `import-summary.sh`'s own unreachable-site matcher (sourced, not reimplemented),
  publish output and a completion marker. `run-scrape.sh` is untouched and keeps running every
  jurisdiction that hasn't moved to this — the two runners coexist for the whole migration.
  **Does not import** — that is `cloud_loader.py`, a separate invocation against a separate
  exclusion mechanism. Michigan-specific: refuses without its externalised last-action baseline
  (same rule as the old script), and separately refuses without a fresh published WAF cookie
  (`_mi_waf_cookies_are_fresh()` — every cookie in the published set must have `MI_WAF_COOKIE_MIN_
  FRESHNESS_SECONDS` of life left, default 600s; a Michigan cookie is minted and published on its
  own schedule by `ddp-sync`'s `mi_cookie_publish.py` — monthly since 2026-10-07, Mac only — not by this file, which
  never mints its own; see `RUNBOOK.md` → "Michigan WAF cookie publishing". The check reads only `expires`, so it cannot
  tell a cookie the site has stopped honouring from a good one; a run now also logs the cookie's age).
  A real cookie's `expires` is about a year out, so that check cannot say how old a cookie is or whether
  the site still honours it (OPEN-232); `ddp-sync` now records `_meta.minted_at` and each Michigan run that gets past that
  check logs the cookie's age to stderr (a refused run prints its own ERROR instead) ("no minted_at recorded" for one published before that). Informational only:
  nothing refuses on age.
  **Which scrapers it asks for is read from `jurisdictions.yaml`, never a list in this file:**
  `scraper_takes_start()` (OPEN-501, `scrape.start_filter`: may `bills` be handed `start=`) and
  `scraper_has_votes()` (OPEN-592, `scrape.votes_scraper`: also run the state's SEPARATE `votes`
  scraper, the cloud twin of `run-scrape.sh`'s OPEN-50 auto-detect; Oregon's votes come only from
  one). Both go through `_manifest_scrape_entry()`: `usa` reads `us`, a state with no entry keeps
  the old behaviour (start allowed, no `votes`), and a manifest that does not validate stops the run
  before scraping. `votes` is appended **after** every `k=v` (session, `start=`): os-update hands
  each `k=v` to the scraper named just before it, so `votes` then gets its own `session=<s>` when
  the run has one (only that: never `start=`, never e.g. `chamber=`). os-update runs `bills` first
  and stops at the first scraper that returns nothing, so the OPEN-244 no-op ("no objects returned
  from") applies only when no bill/vote file was written (the jurisdiction/organization files
  os-update always writes do not count); bills written and then an empty `votes` is a **failed**
  run (watermark kept, bills re-collected next run). Massachusetts registers a votes scraper but is
  `false` on purpose (its votes come from `ma/bills.py`; Ramon, 2026-11-16: stays off). Add a
  third per-state scrape fact the same way; do not hard-code a state list here.
  **A scraper's catch-up record (OPEN-609, 2026-11-17)** is carried the way Michigan's baseline is, by
  `_catchup_glob(source)` = `<source>_catchup_*.json` in the cache directory: fetched before the scrape, saved
  only after a successful one and **last**, after the watermark and the completion marker (review 21038: a failed
  save leaves the older record, so the next run reads more bills, never fewer; the run stands). Unlike the baseline it is optional: a store that cannot be
  read logs a WARNING and the scrape runs without it, and a scraper without its record reads every bill. Today only
  `ma/bills.py` keeps one (`ma/catchup.py`: the last whole run's bill and hearing lists, the date of its last full
  walk, and the bills it could not read). No state list: the file's name is the opt-in. The Mac's
  `run-scrape.sh` path needs nothing, because its `_cache` directory stays on disk between runs.
- **`cloud_loader.py` (OPEN-190, 2026-08-29)** — the on-prem load half of the split. Consumes
  **one** cloud collection run, identified by its manifest (never bare object presence): fetches
  every object the manifest names into a staging directory, refuses on an absent/unparsable/
  identity-mismatched manifest or a partial fetch, then `os-update --datadir <staging> --import`.
  **Path-containment is checked explicitly**, not assumed from `startswith()` alone — a manifest
  key with a `../` component, a doubled slash, or an empty/`.`/`..`-only relative path is refused
  before ever being resolved against the staging directory, because the failure mode of getting
  this wrong is writing outside it.
- **The cross-machine locks (OPEN-187/OPEN-203, 2026-08-29)** — `SourceLock`
  (`cloud_collector.py`) and its bash mirror, `scraper_memory_acquire_lock`/`_release_lock`
  (`scraper-memory.sh`), replace the old `/tmp`-local `mkdir` locks (OPEN-154's scrape lock, and
  the local-only import lock) with S3 conditional writes (`IfNoneMatch`/`IfMatch`) — a Mac run and
  a cloud run can now see the same lock. Age-based expiry only (24h TTL, matching the old dead-
  holder threshold): there is no pid to check across machines, so a lock is reclaimed on its own
  stated expiry, never on a liveness probe. **The import lock is a second, independently-tracked
  instance/variable-pair, not the scrape lock reused** — `run-scrape.sh`'s real call pattern holds
  the scrape lock for the whole run and the import lock later in the same process, and sharing
  tracking state between them reproduces the exact cross-key clobbering bug three `/pm-review`
  rounds found and fixed in this exact mechanism. **What this does not yet cover**: sequential
  duplicate delivery (the same run loaded twice, an hour apart) — a lock only ever prevents
  *concurrent* access and was never going to help here; that is still open (OPEN-203's own AC).
  **Setup is a separate operator action**: `OPEN-187-scraper-lock-wrapper-setup.md` has the exact
  sudo-gated wrapper recipe for the Mac side, not yet installed as of this writing — until it is,
  `scraper_memory_check_config()` refuses to enable the S3 memory backend at all rather than run
  without the lock.
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
- **`people` is a formal DDP fork too** (`Digital-Democracy-Project/people`, since 2026-07-27;
  carried-fix model from OPEN-336, `PLAN-fork-management.md` §8). Fork `main` = upstream + our
  fixes, like the other forks. **Remote convention (switched on the Mac 2026-10-13 and on production 2026-10-14):** `origin` = the
  fork, `upstream` = the public project, identical to core/scrapers/api-v3. **A fix does not wait
  for upstream:** it enters fork `main` through a PR in the fork with a green `Lint YAML`, and its
  commit message carries `Upstream-PR: owner/repo#N` and `Source: <url>` trailers (blank line
  before them), so the weekly drift report can show which carried files upstream has merged or
  declined. Never put "fix", "close" or "resolve" (or fixes, fixed, closes, closed, resolves,
  resolved) directly before an upstream reference in a PR body or commit message: GitHub reads that
  as an instruction to close the upstream PR when ours merges. A fix upstream rejects but our
  source supports stays carried. When upstream merges the same change, the next catch-up shows no
  difference for it. `run-people-refresh.sh` and ddp-sync's `people-pull` just
  `git pull --ff-only` from `origin`. The `people-pull` job registers independently of `OPENSTATES_SCRAPE_ENABLED` since ddp-sync PR 217; before 2026-10-13 it never started on the Mac.
- **Keeping all four forks current: one daily ddp-sync job, then a catch-up PR by hand**
  (decided 2026-10-12; replaces the GitHub-hosted standing-PR design, plan §8). `fork_upstream_check`
  (ddp-sync PR #211; 01:30 UTC; Mac instance only; off unless `FORK_UPSTREAM_CHECK_ENABLED=true`; independent of `OPENSTATES_SCRAPE_ENABLED` since ddp-sync PR #213; live on the Mac from 2026-10-13)
  fetches the public repositories with no credentials into its own cache folder and writes
  `logs/fork-upstream-status.json` (per fork: commits behind, age of the oldest, titles, whether
  `.github` or migrations changed). It posts to #automation-errors when a fork lacks an upstream
  commit older than 3 days (again at 7 and 14 days, then weekly) or a fetch fails. It never merges,
  pushes or opens a PR. **The dev-side agent reads the status file, prepares and tests a catch-up PR
  (branch `catchup-<fork>-<date>`; real merge commit; daytime; after the smoke test in plan §5.B)
  and Ramon reviews before it is merged;** the limit is one week from the day the check first
  reports the fork behind, and the Monday report flags an overdue one. **A person approves before
  anything reaches fork `main`** ("review before import", decided 2026-10-11; this is procedure,
  since `main` has no branch protection on these forks). Nothing on a host cron-merges or writes to
  git; the hosts only fast-forward. On a `catchup-*` or `sync/upstream` branch a dead link in
  upstream's own data warns instead of failing the `people` link check; our own fix PRs still fail
  on one. The role-date check still blocks: upstream's nine missing start dates are carried in the
  first `people` catch-up (fork PR 14) as fixes for upstream PRs 4155 to 4160. The upstream-owned
  workflows that need secrets we lack or that we do not use (`Update Database` on people; `Scout
  Scrape` and both Docker workflows on scrapers; the Docker and `Release Steps` workflows on core;
  the Docker workflow on api-v3) were switched off on 2026-10-11; `Lint YAML`, `Lint Python` and
  `Test Python` stay on. No sync tokens, `ddp-sync` Environment or Slack webhook are used (dropped
  2026-10-12). See `RUNBOOK.md` → "Scraper state" for the commands.
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

## `check-scrape-staleness.sh` — RETIRED (OPEN-324, 2026-10-05)

Removed, along with `test-check-scrape-staleness.sh` and its `ddp-agents` hook. It was broken
(its YAML watchlist failed on `import yaml` under the daemon, so it watched nothing from
2026-08-23) and obsolete (the
`logs/last-run/*.ts` markers it read stopped updating on 2026-09-01 when scraping moved to the cloud
path). Don't resurrect it to cover "a scheduled scrape never started" -- that belongs next to the
scheduler in ddp-sync, not on this Mac. Full account: `RUNBOOK.md` → "Scraper staleness watchdog --
RETIRED", and `LESSONS.md` §6.

## `lib/slack-alert.sh` — shared Slack alert helper (OPEN-325, extraction requested by OPEN-43)
Source it, don't run it: `source "$SCRIPT_DIR/lib/slack-alert.sh"`, then `post_slack_alert "text" ["#channel"] [--source S] [--dedupe-key K] [--direct]`
(channel defaults to `#automation-errors` for the direct post; the route picks its own from CAMS's channel map unless one is given). It owns the token lookup, the 10s timeout, the CodeBot sender identity
(defaults `CodeBot` / `:robot_face:`; an empty setting means the default; a multi-word name is kept whole), JSON
escaping, and the stderr line when Slack answers anything but `"ok":true`. Needs the `chat:write.customize` scope;
without it Slack ignores the name and icon and the post still succeeds under the default name.
- **Route first, direct second (OPEN-436, plan `PLAN-cams-operator-alerts` §4.9).** With `OPERATOR_ALERT_URL` and `CAMS_API_TOKEN` set
  (environment, then `ddp-agents/.env`) and `OPERATOR_ALERT_VIA_CAMS` not `false`, the alert is POSTed to CAMS (5 s, Bearer token, body
  `{v:1, source, text[, channel][, dedupe_key]}`). **Any answer but 2xx, a timeout or a connection error falls back to the direct
  CodeBot post**, and a 4xx is reported on stderr as a sender bug. A 2xx counts as delivered, including the route's `duplicate` and
  `dropped_rate_limited` answers. `--direct` is for alerts about CAMS, Docker or the replica, which must work when CAMS is down.
  `--source` is `<service>/<job>` (callers pass `ddp-open-states/run-scrape` etc.). **Mirror of** `ddp-agents/deployment/scripts/lib/operator-alert.sh`:
  same variable names and the same attempt and fallback; change both. `report_failure_to_cams` (`/api/v1/failures`, code triage) stays separate.
- **Always returns 0.** An alert is best-effort and must never change a caller's exit status or trip its `set -e`.
- **Source it only if readable:** every caller uses `[ -r "$SCRIPT_DIR/lib/slack-alert.sh" ] && source ... || post_slack_alert() { ...stderr...; return 0; }`.
  Under `set -e`, macOS's bash 3.2 exits the whole script when `source` hits a missing file *even with a `||`
  fallback*, and a scrape that dies because its alert helper is missing is worse than a missing alert.
- **bash 3.2:** it is written for macOS's `/bin/bash` (no `${!var}`, no associative arrays) and safe under
  `set -euo pipefail`.
- **Tests:** `test-slack-alert.sh` (fake `curl` on `PATH`, `SLACK_ALERT_ENV_FILE` pointing at a throwaway env
  file; no network). Its last block **fails if any other shell script contains `chat.postMessage`**, so a new alert
  cannot copy the old two-key payload and post as Agent Smith. There are no exemptions (OPEN-435 removed the last).
- **Delivery flag:** after each call `OPERATOR_ALERT_DELIVERED` is `1` only when CAMS answered 2xx or Slack answered `"ok":true`, else `0`,
  and `OPERATOR_ALERT_REASON` is `ok` / `no-token` / `refused` (the names ddp-agents' `operator-alert.sh` uses). The
  call still returns 0; a caller that keeps state about alerts it sent (`check-replica-health.sh`) reads the flag.
- **Mirrors:** `ddp-sync` has the same idea in Python (`ddp_sync/slack_alerts.py::post_alert`) and `ddp-agents` owns
  the persona registry (`cams/slack_identity.py`); all three read the same `CODEBOT_SLACK_*` variables.
- Mac only (none of these scripts are in the Docker image). No test here has run against live Slack.

## `check-replica-health.sh` — RDS→Mac replica health + alerting (repo root, OPEN-312)

The scheduled, alerting wrapper for the logical replica LegBot reads. **Reuses, does not reimplement:**
`ops/postgres-replica/local/replica-status.sh` (worker state, lag, retained WAL, CAMS heartbeat) and
`compare-schema.sh` (published-vs-subscribed table set + column agreement) do all the assessing; this
script only runs them, keeps a two-strikes alert state per check in `logs/last-run/replica-health.*.state`,
and posts one Slack message (plus recovery) to `#automation-errors`. Credential-free checks run every
time (and, since OPEN-314, stage 3 runs `sync-structure.sh` whenever its credential file exists); the RDS-side and schema stages run only when `RDS_MONITORING_DATABASE_URL` /
`RDS_HOST`+`RDS_REPLICATION_PASSWORD` are in the environment. Same invocation model as
the retired `check-scrape-staleness.sh` (one-line hook in `ddp-agents`' `health-check-slack.sh`; always exits 0).
Sets `DOCKER_HOST` to Colima itself when run as a root daemon (copied from `start-os-api.sh`).
**It posts through `post_slack_alert`** (OPEN-435), as CodeBot, direct to Slack and never via CAMS (CodeBot triage
cannot act on a network outage, and the monitor must work when CAMS is the problem). It keeps its own
state machine and "advance state only when Slack answered `ok:true`" rule, now reading `OPERATOR_ALERT_DELIVERED`.
It runs with `HOME` unset and a minimal `PATH`; the helper needs neither. (A monitor may reasonably stay
self-contained, as OPEN-43 noted for the retired staleness watchdog: it should not break because the thing it
watches did. The helper depends on nothing but `curl` and `/usr/bin`.) Test seams: `REPLICA_*` env vars, see
`test-replica-monitoring.sh`. Operator doc: `ops/postgres-replica/local/README.md` → "OPEN-312".

## `ops/postgres-replica/local/sync-structure.sh` — the Mac replica follows RDS's table structure by itself (OPEN-314)

Logical replication never carries structure, so a new column on a published table used to stall the Mac's apply worker
until a person added it by hand, in order. This script does the safe additive part: it adds a missing nullable column or one with a plain-constant default (all
of a table's additions in one transaction, none if any of its columns is refused), creates a published table that is
missing locally (columns, primary key, other indexes; no foreign keys) and refreshes the subscription only when **every**
pending published table is ready (exists locally and `ddp_local_replication` can `SELECT` it), and **refuses** (a `FAIL:` line)
a `NOT NULL` column with no default, an identity/generated column, a function default (it would be evaluated again on
the Mac and give existing rows different values), a changed type, a table with a generated column, or a table with no primary key. It reads RDS only
(no publication or grant changes: those stay the prod agent's), never touches local-only tables, the locally built
`ddp_bill_search` or the foreign keys the Mac dropped, and reports a new RDS table the publication does not carry only
after `--seed-known-unpublished`. One run at a time (lock), bounded run time (watchdog kills the whole process tree),
idempotent, `--dry-run`. Credential: the existing read-only replication login from a mode-600 file
(`STRUCTURE_SYNC_ENV_FILE`) or the environment, never printed. **Reuses, does not reimplement:** the column read is
`compare-schema.sh`'s `pg_attribute`/`format_type()` query (extended with default and identity), the table list is the
publication's own (OPEN-312), and the scheduling and alerting are `check-replica-health.sh` stage 3 (its two-strikes
state, `logs/last-run/replica-health.structure.state`, one Slack message, recovery). **Do not** add a second scheduler,
a second alert path or an RDS write to this; if a case is not additive, the answer is the break-glass procedure
(README) or a rebuild. Tests: `test-structure-sync.sh` (real throwaway Postgres pair) and `test-replica-monitoring.sh`.
Operator doc: `ops/postgres-replica/local/README.md` → "OPEN-314".

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

## `fix-*.py` — one-off `personvote` repair scripts (`archive/person-matching-fixes/` and repo root)

These are a family, not unrelated scripts. All of them repair `opencivicdata_personvote` in the
replica, and all share the same shape — **copy the nearest one rather than starting from psycopg2**.

**Six of the person-matching ones are archived (OPEN-553, 2026-11-16) in
`archive/person-matching-fixes/`.** Each case was re-checked read-only against the production
replica (`openstates_rds_repl_20260911`) on 2026-11-16: no stored row is still wrong or blank for
these cases except the few listed below, and rows written by imports after each rule existed come
out right, so none is a recurring chore any more. The rule that replaced each script lives at the
source, not in a script:

| Script (archived) | Case | Where the rule lives now |
|---|---|---|
| `fix-open110-fl-smith-*`, `fix-open115-fl-smith-senate-*` | FL "Smith", House/Senate crossed | core `resolve_person()` cache key includes the chamber (OPEN-112) |
| `fix-open113-wa-cortes-valdez-*` | WA Senate "Cortes"/"Valdez" on House members | same OPEN-112 chamber cache key |
| `fix-open114-mi-outman-*` | MI Senate "Outman" on Pat Outman | same OPEN-112 chamber cache key |
| `fix-open116-blank-voter-id-*` | FL "Garcia", WA "Hunt", MI "Greene" left blank | chamber-scoped name match + current-role tie-break in `resolve_person()` |
| `fix-open174-mi-myers-phillips-*` | MI House "Myers-Phillips" left blank | people fork `other_names: Myers-Phillips` (data/mi, 2026-08-26) |

Archived means "not needed for new imports", not "no stored row is still wrong": on 2026-11-16, 9
Michigan "Myers-Phillips" rows were still blank (vote events last imported before the name reached
the database), and the choice between a re-import and a script run is Ramon's under the scorecard
gate. Completion records of the real runs stay at the root:
`vote-misattribution-backfills-completed-20260819.md`,
`OPEN-174-mi-myers-phillips-backfill-completed-20260827.md`. **A new person-matching case goes to
the source first** — a people `other_names` entry or identifier (as OPEN-474 and OPEN-526 did), or a
scraper name rule — and only the rows already stored get a script, copied from the archive.

**`fix-grijalva-vote-misattribution.py` stays at the root: its case is not settled.** Core's
`resolve_person()` matches the bioguide id first (OPEN-2) and today resolves G000551 to Raúl
Grijalva, but when that lookup finds no one it falls back to the bare surname, and the
current-role tie-break then picks Adelita Grijalva for any 119th-Congress "Grijalva" row. On
2026-11-16, 52 Raúl votes (Jan–Mar 2025) were on Adelita, 5 of them from vote events created by a
2026-09-16 import; why the id lookup missed then is not known.

`open304-add-lis-identifiers.py` stays at the repo root although its case is also covered now
(the people fork carries the 14 `lis` ids since 2026-09-22): the Fargate image copies it and
ddp-sync's `/trigger/open304-lis-identifiers` launches it, so retiring it is a change in both repos.
On 2026-11-16, 198 US Senate rows for those 14 senators were still blank (vote events last imported
on or before 2026-10-07; later imports resolve them). `backfill-vote-person-resolution.py` (US, fills
blank voters by bioguide/lis id) is the general tool for that, not a one-off, and stays.

**`relink-blank-voters.py` (OPEN-611) is the state-side twin:** it fills blank state roll-call voters that a
new import would now link (the person or alias reached the database after the votes), only where exactly one person
matching the name (name, other name or family name, as core's `resolve_person()` matches) held a seat in that
chamber on the vote's own date, and never twice on one roll call. Dry run by default; `--commit` needs `--list`
(the per-vote record the scorecard gate reviews; it takes its name only after the commit). Its cases are a list at
the top of the script (OPEN-611: wa "Hunt" 673, ma "Garcia" 8, mi "Myers-Phillips" 9 of 11, fl "Garcia" 469
after people #27 loads); a new case goes to the source first (people or scraper), then a line there, not a new
script. Each state's commit is under the scorecard gate.

Still at the repo root:

- **Stale rows the scraper no longer writes** (a different family: this one deletes whole vote events, not
  `personvote` fields): `fix-open433-az-stale-empty-vote-events.py` removes the empty Arizona events that the
  pre-2026-07-11 scraper stored for procedural motions (0 counts, no voters, azleg floor-action source). The
  same conventions apply, plus three guards the others did not need because they only filled a column:
  `--session` (named, so nothing outside the validated session is touched), `--expect-events` (the dry run's
  count, so a changed table aborts before any write) and `--save-dir` (the deleted rows and each bill's old
  `updated_at` as CSV, the revert). It bumps the touched bills' `updated_at` because the broker's incremental sync
  selects by it and a deleted event can no longer match `vote_updated_since`.

The conventions every one of them follows, and a new one must:

- **`--dry-run` that actually rehearses the write**, printing the exact counts the real run will
  report. The established collaboration pattern for a production write is dry-run → agree the
  real numbers → commit, so a dry run that does not produce the final numbers is not useful.
- **Re-derive the correct person per row, date-anchored, from `opencivicdata_membership`** — who
  held a matching-chamber seat in this jurisdiction *on that vote's own date*. Never
  `resolve_person()`'s opinion, never "currently seated". `fix-open116`'s
  `find_unambiguous_person()` is the reference implementation; `fix-open174` adds an assertion
  that the single candidate found is a specific expected `ocd-person` id, which is worth copying
  whenever the target identity is known in advance.
- **Fill only the provably unambiguous rows.** Anything with 0 or 2+ candidates on its date is
  left alone and reported, never guessed.
- **Idempotent by predicate**, not by bookkeeping: match on `voter_id IS NULL` (or the specific
  wrong id) and re-check that condition in the `UPDATE`'s own `WHERE`, so a second run is a
  no-op without needing to remember it already ran.
- **Abort without committing if the rows actually updated ≠ the rows expected.** `autocommit =
  False`, one transaction, `conn.rollback()` and `SystemExit` on mismatch.
- **Write a dated completion record at the repo root** when it runs for real — what changed, the
  before/after verification numbers, and the revert statement. Capture the affected row ids to a
  file *before* writing, so the revert is a paste rather than a reconstruction.

**Two duplicate checks are needed, not one — found the hard way on 2026-08-27 (OPEN-174).** The
obvious check asks whether the target vote event *already* has a row for this person, which is
what `fix-open116` does. That is necessary and not sufficient: if one roll call carries **two**
blank rows for the same voter, the check passes for both and filling both makes the roll call
count that legislator twice. The first OPEN-174 production run did exactly this to three Michigan
roll calls before it was caught and reverted. So also **track `(vote_event_id, person_id)` pairs
already queued within the run** and skip repeats — `fix-open174`'s `queued` set. A backfill whose
whole purpose is correct attribution must not be the thing that double-counts a vote.

Worth knowing before reaching for one of these at all: **a re-import would also repair these
rows**, since `PersonVote` sits on `_update_related()`'s wipe-and-recreate path
(`openstates-core/openstates/importers/base.py`) and `items_differ()` sees a resolved id against
a stored NULL. It is usually not available in practice — `do_scrape()` wipes
`$SCRAPED_DATA_DIR/$STATE` at the start of every run, so only the last run's bills are on disk,
and covering a whole session means a full re-scrape. Check how much is in `_data/<state>` before
concluding a backfill is the only option.

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

Rebuild recipe (also in `RUNBOOK.md`; Python 3.13 since OPEN-515): `"$(uv python find 3.13)" -m venv .venv && .venv/bin/pip install
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
  `GET /jurisdictions/{iso2}?include=legislative_sessions` for every jurisdiction in
  `jurisdictions.yaml`, alerting to Slack on either failure. `bulk_dataexport` is part of
  openstates.org's own bulk-CSV-export Django app, not the OCD/pupa scraping schema
  `openstates-core`'s `os-initdb` creates —
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
  WS9). Alerts through the shared `post_slack_alert` (see Slack alert-on-failure above).
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
  **It does not run `ensure` for the bill-search table (OPEN-457, 2026-10-30).** When a merged api-v3 change adds a column to
  `ddp_bill_search` (OPEN-457 added `alt_titles`), the table must get it **before** the new container serves, because
  `ensure` runs only on `refresh`, never at boot: build the image, run
  `cd deploy && docker-compose -f docker-compose.ddp.yml run --rm --no-deps api python -m api.search_projection ensure`
  from the new image, then `./refresh-api-v3.sh`, then `docker exec ddp-openstates-api-1 python -m api.search_projection refresh --full`.
  Running the script first leaves every `/ddp/search` call answering 500 until `ensure` is run. Full order, rollback and
  the 2026-10-30 dev results: api-v3 `docs/runbook/ddp-bill-search.md` section 8.

- **`check-core-pin-drift.py`** (OPEN-579, repo root; test `test_check_core_pin_drift.py`) — the one check that api-v3
  and the scrapers image run the **same openstates-core commit** (PLAN-state-specific-handling §4.4). **There is no pin
  file** (OPEN-586, Ramon 2026-11-16: core, scrapers and api-v3 ship together; `ddp-openstates-core.txt` is gone): the
  scrapers image takes core's main at build, and api-v3 is built at that image's commit. The check confirms it: it compares, as
  full 40-character SHAs, the core the live scrapers image was built from with the core installed in each api-v3
  container. Exit 0 agree, 1 drift (each line names both commits),
  2 a source could not be read (never a pass), the same contract as `check-jurisdiction-drift.py`.
  * **The image's record:** the `Dockerfile` writes `git rev-parse HEAD` of the core clone to
    `/opt/openstates-core/DDP_CORE_COMMIT` before it deletes `.git`; `deploy-scrapers-image.sh` reads it back, stops if it
    is missing, and prints it. Images v60 and older have no record (their `.git` was deleted unrecorded): pass
    `--image-core <sha>`. `--image <ref>` reads the record with `docker run`, so the image must be on the host (the Mac).
  * **The container's core:** pip's `direct_url.json` for `openstates` (the archive URL carries the SHA). The build both
    api-v3 copies use (`deploy/Dockerfile.ddp`) installs the fork archive **at `DDP_CORE_SHA`, the live scrapers image's
    core** (OPEN-586 follow-up, 2026-11-17), so pip records it and api-v3 always matches the image. There is no default:
    a build without a full 40-character commit stops. `refresh-api-v3.sh` fills it from `SCRAPERS_IMAGE` /
    `SCRAPERS_IMAGE_CORE` with `check-core-pin-drift.py --print-image-core` (the same reader the check uses; do not add a
    second one) before it builds; on EC2 the prod agent sets `DDP_CORE_SHA=<sha>` for `docker-compose build api`. The
    build no longer asks GitHub which commit main is (that unauthenticated lookup hit GitHub's 60-an-hour limit on the
    Mac on 2026-11-17 and stopped a release). api-v3's own `Dockerfile` and CI still take main's commit (they test
    against main; neither is deployed). Do not install `archive/main.tar.gz`: it records no commit and the check would
    call it drift. The version
    string is useless here (fork and PyPI both say 6.26.5); a container with no fork archive URL is drift.
  * **Which image is live is the caller's to say** (`--image`/`--image-core`), like `check-jurisdiction-drift.py --live`;
    the script makes no AWS call and needs no new permission.
  * **Where it runs:** last step of `refresh-api-v3.sh` (`SCRAPERS_IMAGE` or `SCRAPERS_IMAGE_CORE`; neither is exit 2),
    by the prod agent after each EC2 api-v3 rebuild, and after each scrapers image release. **Do not** compare version
    strings or add a second copy of this comparison elsewhere. No schedule yet (follow-up).
  * **Release order:** scrapers image first (then any stored recompute), then the api-v3 rebuild on both hosts, each built
    at the new image's core. A core merge without a new image changes nothing in api-v3: a rebuild still takes the live
    image's core. **Rollback:** retag a `ddp-openstates-api:pre-*` image as `:local` and recreate `api` only; rebuilding
    an older api-v3 commit also works now, at the image's core.
  * **First run (Mac, 2026-11-16):** the Mac container ran `96445eb26` (the old pin) and v61 carries `bcde78e2c`, so the
    check reports drift until both api-v3 copies are rebuilt from main (OPEN-586; a test build of api-v3 from main on
    2026-11-16 installed `bcde78e2c` and passed the check against v61).

- **The "current session" rule lives in api-v3, once (OPEN-467, 2026-10-31).** `api-v3/api/current_session.py`
  (`session_flags`) decides which legislative sessions are current and previous, and
  `GET /jurisdictions/{id}?include=legislative_sessions` publishes the answer as `is_current` and `is_previous` on every
  session (api-v3 PR #42). **Do not add a second rule** in ddp-sync, a scraper script, the broker or the website: read
  the flag. Rule: a session that has not started is never flagged; current = every active session (a special session
  counts, Ramon 2026-10-31) plus, when no regular session is active, the newest started regular one; previous = the
  regular session before the current regular one. Virginia and Washington leave `classification` blank, so the rule
  reads their special sessions from the identifier (`2026S1`, `2018specialI`). Consumers are their own tickets:
  SYNC-139, BROKER-369, NEXT-109. (OPEN-468 was a consumer too, for the hard-coded `194th` in `run-all-scrapes.sh`.
  OPEN-465 deleted that script, so its acceptance lines no longer apply; they were not met, they have no target.
  Today no scraper entry point in this repo names a current session: ddp-sync passes none for MA, and `os-update`
  scrapes every session its scraper metadata marks `active` (`openstates-scrapers/scrapers/<state>/__init__.py`;
  MA marks the 194th). That list is upstream's, so a new MA session (the 195th, January 2027) reaches the scrape only
  when the fork takes that metadata change. Not verified that it will in time; check it before January. The
  session logic that ddp-sync itself uses is SYNC-139's. Do not add a flag reader to `run-scrape.sh`.) No schema change, so no `ensure` or refresh on deploy; it needs a
  new api image on both hosts (the Mac :8002 and the EC2 host).

- **Newest-action order for the bill list lives in api-v3's `GET /bills`, once (OPEN-469, 2026-10-31).** `sort=latest_action_desc`
  (`api-v3/api/bills.py`, api-v3 PR #43) lists newest action first, bills with no action date last, and bills that share a day
  by bill id (so paging an unchanged list is stable). It is the **only** sort that works with no `jurisdiction` and no `q`
  (every other order still answers 400 without one, and `session` still needs a `jurisdiction`), so a browse list over all
  jurisdictions asks for it. `latest_action_date` is free text (date-only for MA, full timestamps for UT and US; of the
  77,688 bills 73 have none and every other one starts with an ISO date), so the order is exact to the day. **Do not add a second ordered-list route
  or a sort on `ddp_bill_search`:** measured on the
  Mac, 20 a page: 103 ms for page 1, 168 ms at the deepest page, one state 27 to 92 ms (EC2 page 1 613 ms, prod agent
  report `2a588e6`, about six times slower). **Correction (OPEN-484, 2026-11-03):** this entry first said the table's index
  (`opencivicdata_bill_latest_action_idx`) serves this order. It does not: that index is ascending and has no `id`, so Postgres
  reads and sorts every bill for each page (`EXPLAIN ANALYZE` on the production-copy database: page query 39 ms, 43 ms more for the
  page's total count). An index that matches the order (`latest_action_date DESC NULLS LAST, id`) takes the page query to
  0.17 ms; it is made only by `python -m api.search_projection ensure --bill-list-index` (api-v3 PR #47, merged 2026-11-04 as `16c5168b`;
  runbook `docs/runbook/ddp-bill-search.md` section 9). A second cost sat in the shared pagination: the page's total count kept its
  `ORDER BY` inside the subquery, sorting every row to count it (about **480 ms on production**, 77 ms on the Mac; api-v3 PR #48,
  merged 2026-11-04 as `14433582`; OPEN-489). **Both are live on production and measured (prod agent, `notes/ops-handoff` `9a4db24`,
  2026-11-04 19:24 to 19:31 UTC; image `5247cecb337c`, index created 19:29 UTC):** page 1 **642 ms to 231 ms with the count fix alone to
  87 ms with the index**, page 500 906 to 107 ms, US page 1 348 to 55 ms, the same first-20 bill ids and total at every stage; the
  website's path through the broker 1,595 to 297 ms. The Mac api was recreated the same way (`./refresh-api-v3.sh`, same day) and
  carries the index in its database copy. What is left inside the endpoint is the count (about 62 ms of 86). Rollback on the host:
  image `ddp-openstates-api:pre-open484`, `DROP INDEX opencivicdata_bill_latest_action_desc_idx`. The endpoint itself needed no schema change, so no `ensure`
  or refresh; it needed a new api image on both hosts. **Live on both:** the Mac (refreshed 2026-10-31 23:20 UTC) and the EC2 host (23:31 UTC, prod agent
  report `2a588e6`). The broker's Explore list is the consumer (BROKER-373).

- **The bill list's page size lives in api-v3's pagination, once (OPEN-493, 2026-11-04; api-v3 PR #51, merged 2026-11-05 as `b7adb9a3`; **live on production since 2026-11-05 00:58 UTC and measured** (prod agent, `notes/ops-handoff` `1f0e965`): one call of 50 is about 110 ms against about 263 ms for three of 20, the same 50 ids, total 87,489).**
  `GET /bills` (`api/bills.py`, `BillPagination`) allows up to **50 bills a page when the request has no `include=`** and keeps **20 with an
  `include=`** (the heavier answers stay bounded); the default `per_page` stays 10, and committees (20), events (20), people (50), person votes (50)
  and jurisdictions (52) keep their own limits. The limit is checked in one place, `Pagination.paginate` (`api/pagination.py`), through the
  optional class attribute `max_per_page_without_includes` (`None`: one limit with or without `include=`); a 400 shows the range that
  applies (`must be in [1, 50]` or `[1, 20]`). **Why:** the broker's website page is 50 rows and api-v3 refused more than 20, so one page was
  three calls at once, each also counting all matching bills (production: three at once 247 ms against 90 ms for one, prod agent,
  `notes/ops-handoff` `a4b65f52`); on the Mac copy one call of 50 is 62 ms against 105 ms for three of 20. **Do not** make a caller loop over
  20-bill chunks to build a page, and do not add a second per-list rule: set the attribute. Callers read in the code: ddp-sync hard-codes
  20, `quality_check` sends 20, VoteBot's roster reads use `/people`; the broker sends 20 until BROKER-431 changes it **after** this is live (a
  request for 50 before then is a 400). No schema change, no `ensure`; it needs a new api image on each host (the prod agent recreates api-v3).

- **Which bill labels are real bill types lives in api-v3, once (OPEN-519, 2026-11-10; api-v3 PR #55, not merged).**
  `api-v3/api/bill_types.py` holds `BILL_TYPES` (bill, proposed bill, resolution, joint/concurrent resolution, memorial,
  joint/concurrent memorial, constitutional amendment) and `NOT_BILL_TYPES` (report, communication, order, study
  request). Ramon (2026-11-10, NEXT-182): only bill types are listed and counted as bills. An item is a bill type when
  any of its labels is on the list, or it has none (fail open).
  * **The option:** `bill_types_only=true` on `GET /bills`, `/ddp/search`, `/ddp/search/suggest` and
    `/ddp/search/hydrate`. Off by default, so LegBot, VoteBot, ddp-sync and scripts see no change. Hydrate also returns
    each bill's `classification`.
  * **The label is read live** from `opencivicdata_bill`, never copied into `ddp_bill_search`. The OPEN-517 relabel
    does not move `updated_at`, so a copied label would never be refreshed.
  * **Unknown labels:** `python -m api.bill_types check` (read-only) exits 1 and names any label on neither list. Run it
    after a state's first scrape or a new labelling rule.
  * **Do not** copy the list into the broker or the website: they pass the option (BROKER-460).
  * **Release:** no schema change, so no `ensure` or refresh; it needs a new api image on each host.

- **One person's votes live in api-v3's `GET /people/{person_id}/votes`, once (OPEN-481, 2026-11-02; api-v3 PR #44, merged `b3148ac`;
  live on the EC2 api-v3 per the prod agent's note of 2026-11-02 20:40 UTC).** `person_id` is the full `ocd-person/<uuid>`; the route is `api-v3/api/person_votes.py`. It lists the votes that person
  cast, newest `start_date` first (ties by vote event id, so paging is stable), paged (max 50), with the person's own option, the
  vote event with its totals, and a compact bill (absent for a vote with no bill); page 1 carries `summary.counts` over all pages.
  Optional `jurisdiction` and `session` filters. **Do not fetch every bill with `?include=votes` to build a "how did they vote"
  view, and do not add a second per-person votes route in the broker or the website that reads the database.** Completeness is
  bounded by attribution quality: a vote with a NULL `voter_id` (a name never matched to a legislator; MA 16%, VA 7.8%, OPEN-474,
  OPEN-473) is returned for nobody, and nothing matches on `voter_name` (OPEN-141). No schema change, no index (it uses the existing
  `voter_id` index; page of 50 about 6 ms on the Mac replica); it needs a new api image on both hosts. The broker route is BROKER-410.

- **`deploy-scrapers-image.sh`** (repo root) — the **one command a human operator runs** to ship
  scraper changes to Fargate: build `ddp-scrapers:vN` on the Mac, smoke-test it, push to ECR, and
  register a new task-definition revision. `RUNBOOK.md` → "Deploying a Fargate image change" is the
  process; this is its implementation, so **don't re-assemble those steps by hand or write a second
  deploy script**. It loads the AWS IAM credentials and the GitHub token from the dev checkout's `.env`
  itself (no `aws login`), picks the next unused tag from ECR, and fails before pushing if the image
  can't import the scrapers or scrape one Utah bill end to end, or carries no record of its core commit (OPEN-579:
  `/opt/openstates-core/DDP_CORE_COMMIT`, printed at the end for `check-core-pin-drift.py`). Registering the revision is the
  cutover: `ddp-sync` launches the family name, so the next launched task uses it. Deliberately
  outside the discipline checklist's resumability/logging/Slack-alert items: it is an operator-run,
  foreground, run-once script whose output *is* the log, and a failure is seen by the person running it.

## `quality_check.py` — live-vs-replica data quality diff (repo root)

Samples bills/people from the local DB, fetches the same records from both `localhost:8002`
(local api-v3) and `v3.openstates.org` (live, real API key), diffs key fields. `Report` class
gives a uniform ✓/✗/~/`-` console output — **reuse this class for any new comparison/audit
script's output** rather than hand-rolling print statements. `OCD_TO_CODE` is the canonical
OCD-jurisdiction-string → short-code mapping, derived from every entry in `jurisdictions.yaml`
(OPEN-327, not hand-typed) — `us` uses a different OCD-id format than the states but is included
in the same mapping — if a new script needs this mapping, import/copy from here, don't re-derive
it from the OCD URIs inline.

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

## `check-va-roll-members.py` — do stored Virginia roll calls list the same members as LIS? (repo root, OPEN-429)

Read-only audit: for every stored Virginia vote it fetches LIS's current roll by VoteID and sorts each
difference into `dropped` (stored, LIS no longer lists them), `no-response` (LIS lists them without a
response; the scraper skips these on purpose, so a rescrape changes nothing), `added` and `option`.
Use it before a Virginia rescrape to see what the rescrape would change in member rows, instead of
sampling by hand. `VA_API_KEY` from the environment, paced, stops at the first 403/429, `--cache-dir`
makes reruns free, `--bill` limits it. First result (2026-10-26): of 5,527 stored 2026 House votes,
283 lack Del. Barry Knight (died 2026-02-19; LIS dropped him from the 02-17 and 02-19 rolls), 513 differ
only by a no-response member, nothing else. Not a repair script: the repair is a rescrape.

## Bill-version ordering & diff backfills (`openstates-core/openstates/cli/text_extract.py`)

`archive_bill_versions()` used to walk `bill.versions.all()` directly and trust whatever order
Postgres happened to return for `diff_from_previous_version`'s lineage — `BillVersion` has no
`Meta.ordering` and no reliable timestamp. OPEN-34 (2026-08-06/07) audited every tracked
jurisdiction and found that accident is inconsistent (forward for FL/MI/AZ mostly, backward for
VA/UT/US, doesn't fit a binary model at all for WA/MI's substitute-heavy bills) — **don't assume
DB row order is chronological for any bill-version work; use these instead**:
- `note_stage(note)` / `version_sort_key(note, date, urls=(), origin=None, jurisdiction_name=None)` — classify a
  `version_note` into a content-based stage rank (never DB order), with `BillVersion.date` used
  as a same-stage tiebreaker when it's actually populated (only reliable for US federal, ~99.4%).
  **Updated 2026-10-16 (OPEN-368/379/382, Arizona only):** pass the version's link URLs and the
  bill's origin chamber (`origin=origin_chamber(bill.identifier)`, i.e. "house"/"senate", not the identifier) -- Arizona's tied committee/floor-action
  documents are ordered by the site's `GetDocumentPdf/<id>` number, and its House/Senate Engrossed
  Versions are placed among them by origin chamber; every other note is unaffected. Arizona's
  failed floor amendments (`... failed`) are excluded from the lineage via
  `is_procedural_document()`. `recomputed_diffs_for_documents()` now takes `bill_identifier` as a
  required keyword for the same reason it requires `jurisdiction_name`. A note
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
- **api-v3 imports this module; it keeps no copy** (OPEN-538 removed `api-v3/api/version_ordering.py`, OPEN-92's
  copy). api-v3 installs this fork (`--no-deps --ignore-requires-python`) from core's **main at build time** (OPEN-586,
  no pin file), so a stage-table change reaches api-v3 at its next rebuild; release it after the scrapers image and
  confirm with `check-core-pin-drift.py`.

**Updated 2026-08-31 (OPEN-217/OPEN-107/OPEN-219):** three further fixes to the same two
functions, layered on top of the ordering work above rather than changing it.

- **OPEN-217 — one diff baseline per media type, not per version.** `archive_bill_versions()`
  used to pick a single "preferred" media type (XML over PDF) per version and diff every other
  media type against *that one* instead of its own predecessor — a real one-line edit read as a
  whole-document rewrite for whichever type lost the preference. Fixed by keeping
  `prior_by_media: dict[str, str]`, one baseline per media type, matching what
  `recomputed_diffs_for_documents()` already did since OPEN-211. Known, accepted side effect:
  Massachusetts pairs a PDF "Bill Text" with an HTML "Chapter Law Text" — genuinely different
  documents — so it now produces **no** changelog for that pair instead of a wrong one.
  **Superseded for Massachusetts by OPEN-223** (below): that pair is the bill as filed against the
  law as signed, and Massachusetts alone compares them again.
- **OPEN-107 — a benign cross-archiver race no longer fails the whole run.** Two archivers racing
  on the same natural key used to have the loser's `IntegrityError` counted as a real conflict,
  `sys.exit(1)`-ing the entire run over a document that was, in fact, safely archived by the
  winner. The handler now re-queries by natural key inside its own `transaction.atomic()`
  savepoint (needed because a failed INSERT otherwise leaves the connection needing rollback,
  so the recovery `SELECT` couldn't run at all): a row already there is a benign
  `concurrent_writes` count, feeding this version's diff baseline from the *winner's* stored
  text rather than this run's own fetch; no row at all is still a real `conflicts` failure.
- **OPEN-219 — the WA/MI/VA/AZ text-cleanup dispatch is now one call site, not two.**
  `archive_bill_versions()` and `recomputed_diffs_for_documents()` each used to inline their own
  copy of the same four per-jurisdiction cleaners (OPEN-7/9/10/11) — they had silently
  diverged (the recompute path applied none of them), so a bill's diff differed depending on
  which path computed it, with nothing to say which one you had. Both now call one shared
  `apply_prediff_cleaning(prior_text, raw_text, *, jurisdiction_name, is_bill, prior_media_type,
  cur_media_type)`. **This is not the OPEN-121 registry migration below** — the dispatch is
  still the same `if jurisdiction_name == "Washington": ...` conditional chain, just
  consolidated into one function instead of duplicated across two; see that section's note.

- **OPEN-487 — an archive file name is capped at 200 bytes, and every document the run could not save is named.**
  `_archive_path()` builds `<date>-<note>-<url hash>.<ext>`; the readable note part is the only thing trimmed, and only when
  the whole name would pass `_MAX_ARCHIVE_FILE_NAME_BYTES` (200, under the common 255-byte file-name limit), so every name that
  fit before is unchanged and the full URL hash always stays (names stay unique). It was Nebraska's amendment AM2748: the note
  was long enough to give `[Errno 36] File name too long`, the document was fetched and silently not saved, and the run exited
  0 with `persist_errors=1`. `archive_bill_versions(bill, unsaved_documents=None)` now collects `(url, reason)` for each
  persist failure and `archive` prints `<state>: not saved: <address> (<reason>)` after the summary line. **Do not** shorten the
  hash or the date to fit, and do not make a persist failure exit non-zero without Ramon's decision: it exits 0 on purpose
  (OPEN-263: retried next run; blocked and extract errors do not alert either). Merged 2026-11-04 (openstates-core #75
  `f0a34de5`, lint fix #78 `4c88d2bd`); **not deployed** (needs a scrapers image, then one Nebraska archive task).
- **OPEN-486 — Nebraska's amendment papers are left out of the comparisons, and its text is cleaned before comparing.**
  Two pieces in openstates-core, both Nebraska-only: the procedural-document table in `utils/version_ordering.py` gets a
  `"Nebraska"` pattern for `<name> AM<N>`, `<name> FA<N>` and `Enrollment and Review ER<N>` (the number is required; the real
  versions Introduced, Final Reading and Slip Law never match), and `_clean_ne_text()` in `cli/text_extract.py` (the
  `apply_prediff_cleaning` chain; manifest `quality.diff_cleaner: clean_ne_text`) drops whole header lines (running
  `LB### LB###` header, the year line, `LEGISLATIVE BILL N`, Became law, Approved by the Governor, Introduced by, `-N-`) and puts
  one sentence on each line. **Do not** rewrap to a fixed width (168 pairs got worse) and do not add a header shape without
  checking it against real text; a line is dropped only if the whole line is the shape. Merged 2026-11-04 (openstates-core
  #76 `da0236ff`, #77 `236a4e3f`; ddp-open-states #333 `ea266110`); **not deployed and not recomputed**: it needs a scrapers
  image, then `recompute-diff-order ne` on RDS by the prod agent (dry run first, Ramon's go). The measured effect (Final
  Reading to Slip Law whole-document comparisons 360 to 2) is the author's, from real Nebraska text; not re-measured by the
  reviewer.
- **OPEN-495 — Pennsylvania's text is cleaned before comparing versions.** `_clean_pa_text()` in openstates-core's
  `cli/text_extract.py` (the `apply_prediff_cleaning` chain; manifest `quality.diff_cleaner: clean_pa_text`) drops the
  `PRINTER'S NO. N` line, removes the trailing `<--` change bar, collapses runs of spaces and lower-cases each line, so a
  case-only or spacing-only difference is no change. Line structure is kept (no reflow). Struck-out words cannot be told from
  the PDF's text and are left alone; **from OPEN-516 (below) Pennsylvania's text comes from its OpenDocument printing, which
  leaves them out**, and the cleaner also drops `PRIOR PRINTER'S NO(S). ...` lines. Do not add a shape without checking it
  against real text. The stored text is untouched, but the
  stored comparison becomes lower-case. Measured on the replica over all 921 Pennsylvania comparisons: changed lines 201,965 to
  148,828, comparisons with `<--` 909 to 0, worse 0 (openstates-core PR for OPEN-495). **Changes nothing until** a scrapers
  image carries it and `recompute-diff-order pa` is run on RDS (dry run first, Ramon's go).
- **OPEN-496 — Louisiana's "Page N of M" footer lines are dropped before comparing.** `_clean_louisiana_text()` in openstates-core
  `cli/text_extract.py` (the `apply_prediff_cleaning` chain; manifest `quality.diff_cleaner: clean_louisiana_text`) drops a line only
  when the whole line is `Page N of M`. It calls the one shared footer routine `_drop_page_footer_lines()` that Massachusetts'
  cleaner also uses (OPEN-400): **do not write a second footer routine**; a new state with a footer shape adds a pattern and
  calls that helper. Not deployed and not recomputed: it needs a scrapers image, then `recompute-diff-order la` on RDS (dry run
  first, Ramon's go).
- **OPEN-510 — Louisiana's Engrossed, Reengrossed and Re-Reengrossed versions are ordered by name.** `note_stage()` in
  openstates-core `utils/version_ordering.py` gives the exact shapes `<bill> Engrossed` / `<bill> Reengrossed` /
  `<bill> Re-Reengrossed` (e.g. `SB217 Reengrossed`) ordinals 0, 1, 2 in the chamber-passage stage; the generic "engross" rule
  gave all three 0, and Louisiana versions have no date, so they kept storage order (often reversed). Louisiana's full order is
  Original < Engrossed < Reengrossed < Re-Reengrossed < Enrolled < Act. Only Louisiana's notes match (checked over every distinct
  stored note, 2026-11-08; Virginia's bare "Reengrossed" does not). Measured on the Mac replica: 505 of the 2,908 non-empty
  Louisiana comparisons ran backwards and 1,405 change predecessor; every other state 0. Same change in api-v3's copy. **Not
  deployed and not recomputed** (openstates-core #87, api-v3 #52): a scrapers image, then `recompute-diff-order la` on RDS (dry
  run first, Ramon's go); this blocks Louisiana's switch-on (OPEN-480).
- **OPEN-497 — Nebraska's stored comparisons were already cleaned; the cleaner itself left one kind of re-wrapping behind.**
  `recompute-diff-order` does re-diff the text, not only the order and flags: `recomputed_diffs_for_documents()` runs
  `apply_prediff_cleaning()` on every pair and `--commit` saves the new `diff_from_previous_version`. Read on the Mac replica
  (2026-11-06), all 745 Nebraska pairs recomputed with the real cleaner equal what is stored, so the data is not stale. What
  was left: a line wrap right after a hyphen or slash ("non-" / "Participating") or between two bracketed labels
  ("(3)(c)" / "(i)") joins to "non- Participating" in one printing and "non-Participating" in the other; 158 of the 494
  stored Nebraska comparisons (21% of a random 300) were only that. `_clean_ne_text()` now drops that one space on both
  sides, wherever it sits (comparison text only). Same replica pairs: 158 to 0 whitespace-only, no pair worse, 52,739 to 49,417 changed lines.
  **Do not** add a case-folding or other rule here without measuring it the same way. **Production step (not done, Ramon's go):**
  a scrapers image carrying the cleaner, then `os-text-extract recompute-diff-order ne` (dry run first; expect about 376 of
  the stored comparisons rewritten, 158 of them to empty) and then `--commit`. Nothing changes until then.

## Motion classification tooling

- **OPEN-492 — each saved bill document records, once, whether it is a real bill version.** `BillVersionDocument.is_bill_version`
  in openstates-core (`ddp_bill_version_document`, a nullable true/false column, migration `0049`; empty means "not decided yet").
  `is_bill_version(jurisdiction_name, note)` in `utils/version_ordering.py` is `not is_procedural_document(...)`: **the one
  definition** of "is it a real bill version". The archiver writes it on every new row; `recompute-diff-order <state>` sets it
  for rows already saved (dry run prints `is_bill_version: set=N changed=N not_a_version=N`; `--commit` saves). The archiver's
  skip path does not touch an old row on purpose. api-v3 reads the flag (OPEN-422) instead of keeping a list, so **do not add
  a second list of procedural notes anywhere else** (api-v3, ddp-sync, LegBot): add the state's rule to the table in
  `version_ordering.py` and recompute that state. The flag says nothing about the stage (a version `note_stage()` cannot place
  is still true here; readers keep handling that). **Release order matters:** the column must exist on the Mac replica
  (`ddp_legbot_subscription` does not replicate structure changes), then on RDS, **before** any scrapers image with this code
  runs; then the image, then the recompute per state (each with Ramon's go), then api-v3. Built 2026-11-04 (openstates-core
  PR #80, not merged, not deployed; measured on the replica: Nebraska 790, Louisiana 3,328, Virginia 1,828, Utah 3,170,
  Arizona 16, North Carolina 54, Alabama 45 flagged "not a version", every state without rules 0).
- **OPEN-422 — api-v3 reads that flag and never offers a procedural paper as a bill's latest or previous version.**
  `api-v3/api/bill_version_flag.py` (`flag_column_present()`: does the database have `is_bill_version` yet, re-asked every five
  minutes) and the `unplaced()` test in `BillPagination.postprocess_includes`: a version whose saved documents include one flagged
  False is handled exactly like a version `note_stage()` cannot place (returned and labelled `version_stage: "unknown"`, listed first,
  never `versions[-1]`/`[-2]`, no link `raw_text` or diff; `archived_document_id` and `archived_raw_text` stay, so ddp-sync's
  knowledge-base hook indexes it as "unknown"). `search_projection._refresh_one` skips the same documents when picking the indexed
  text. Empty ("not decided yet") or no column at all behaves as before; the model column is `deferred` so no ordinary query selects
  it. **Do not** add a list or a rule to api-v3 (the rule lives in core's `is_bill_version()`), and do not give a flagged version a new
  label: ddp-sync treats any label other than `"unknown"` as part of the lineage. One constant extra query per single-bill detail with
  versions. Built 2026-11-04 (api-v3 PR #49, not merged, not deployed; the test workflow was also red on every PR until #50 pins
  `ubuntu-24.04`). **Deploy after OPEN-492's column exists and a state has been recomputed**, on the Mac and EC2 (prod agent); after a
  recompute the bill search index may need a `--full` refresh, because the flag change does not touch `updated_at`.
- **OPEN-498 — Massachusetts: the bill's title decides whether a document is a real bill version, because the note cannot.**
  Massachusetts files agency reports and letters (HD/SD numbers), study, extension and "Order relative to ..." orders, amendment
  papers, messages and rules under the same kind of bill number as real bills, and every one has the note "Bill Text", so the
  (jurisdiction, note) rule cannot see them (about 25 to 28% of the 194th session's documents: 3,267 of 11,872 in the ticket, 2,880 of 11,674 on the Mac copy on 2026-11-07, 3,200 on RDS by the prod agent's dry run of 2026-11-07; the archive grows, so the counts differ by snapshot). openstates-core
  `utils/version_ordering.py`: `_REAL_MEASURE_TITLE_PATTERNS` (one entry, "Massachusetts": a title must open with An Act, Resolve(s),
  A Resolve, Resolutions, Joint Resolution or Proposal) and `is_bill_version(jurisdiction_name, note, bill_title=None)`. The archiver
  and `recompute-diff-order` pass `bill.title`; a missing or blank title never excludes a document; `is_procedural_document` and the
  diff lineage are untouched. **Do not** add a title list to api-v3, ddp-sync or LegBot: add a state with the same problem to that
  table and recompute it. A flagged document gets no `raw_text` from api-v3 (OPEN-422), so ddp-sync's archived-text lookup skips the
  bill and LegBot never sees it; the knowledge-base hook still indexes it as "unknown". Merged: the title rule is openstates-core PR #84 (`250de777`, scrapers image v46); a `--flags-only` switch on
  `recompute-diff-order` is PR #85 (`138fa3df`, image v48, task-definition revision 50). **Always run the Massachusetts recompute
  with `--flags-only`:** without it the command also recomputes diffs, and because the diff code compares only documents of the
  same file type, every Massachusetts bill with a PDF ("Bill Text") plus an HTML page ("Chapter Law Text (Enacted)") would have
  its stored diff nulled (`nulled=291` on the prod agent's dry run of 2026-11-07); those stored diffs are the only record of which
  bill became which law (OPEN-370, Ramon 2026-10-15; OPEN-396 hold). `--flags-only` sets and corrects only `is_bill_version`,
  prints `diffs untouched (--flags-only)` instead of the `unchanged= corrected= nulled=` counts, and never names the diff column in
  an UPDATE (a test checks the SQL). **Do not** add a second way to mark a document. **Release state (2026-11-07):** the prod
  agent's read-only dry run on RDS (note `ed0908a`) was clean (`set=12113 changed=20 not_a_version=3200`, the 291 stored diffs
  identical before and after); Ramon's GO for `ma --commit --flags-only` is posted; **the commit is not reported yet**, and its
  verification (SD 4329 hidden end to end; H 3188 and SD 3237 still real) and a Massachusetts LegBot sweep are still open. After the
  recompute the bill search index may need a `--full` refresh, as for OPEN-422; rollback is reverting the rule and rerunning with
  the switch. Decision and sample: OPEN-498.
- **OPEN-525: Alabama's floor-motion papers are not bill versions.**
  * **What they are:** the Alabama scraper adds the amendment or substitute paper behind each floor motion as a version named after the action ("Orr motion to Table - Adopted Voice Vote", "Motion to Adopt - Adopted Roll Call 407").
  * **The rule:** one Alabama-only pattern, `_AL_FLOOR_MOTION_PAPER` in `utils/version_ordering.py`. It is part of Alabama's entry in `_PROCEDURAL_DOCUMENT_NOTE_PATTERNS`, so `is_bill_version` is false for these papers, and `note_stage` ranks them as amendment papers.
  * **Substitutes are taken out too.** 197 of the 453 papers are full substitute texts, and the note cannot tell them from amendments. 181 of the 185 adopted substitutes have at least 90% of their phrases in one of the bill's real versions; HB 306's is the one real loss. The documents stay archived.
  * **Released:** openstates-core PR #92 (`a7a2a861`), scrapers image v54 (task-definition revision 57). `recompute-diff-order al --commit --flags-only` committed on RDS 2026-11-10 17:15 UTC (45 → 498 not a version; comparisons unchanged at 918). Alabama's Stage 3 version-stage gate now passes: 0 of 2,922 without a stage.
  * **Do not** add a second Alabama list anywhere else. A new Alabama paper shape goes in the same pattern, then a recompute.
- **OPEN-569: Alabama's versions carry dates and are ordered by them; only adopted papers are versions.**
  * **Scraper** (`scrapers/al/bills.py`): every version gets the date of the history row that carries it
    (`version_dates()` for Introduced / Engrossed / Enrolled; a paper's first `amdSubFileUrl` row). An amendment or
    substitute paper is a version only if it was adopted (`paper_is_version()`: a carrying row, or the adoption row right
    after it, is "Motion to Adopt ... Adopted", read with OPEN-566's `AMENDMENT_ADOPTION` and OPEN-563's `VOTE_OUTCOME`);
    offered on the floor and never adopted, it is a bill document; a paper only a committee acted on stays a version.
  * **Core:** `version_sort_key(..., jurisdiction_name)` puts the date first for a state in
    `_DATE_ORDERED_JURISDICTIONS` (Alabama only); the stage breaks a same-day tie (0 of 21 same-day pairs disagree with
    the action order). `recompute-diff-order` keeps an Alabama stored document whose (note, date) is no longer a version
    out of the lineage (`_current_version_keys`, parity with the archive). api-v3's copy has the same rule.
  * **Measured offline (Mac replica, 2026-11-16):** 0 undated versions; 56 papers (13 substitutes) become documents;
    300 stored comparisons change, 92 grow (each explained), 0 against a later version.
  * **Release:** scrapers image with core #104 + scrapers #100, Alabama full scrape, archive, then
    `recompute-diff-order al` (gate `corrected=0 nulled=1116`), `remove-stale-documents al` (gate `removed=2867
    kept_last_copy=56`), a final recompute dry run 0/0; api-v3 #62 before Alabama LegBot. Ramon's go for each.
  * **Do not** order Alabama versions by name again or add a second Alabama adoption rule; a new date-ordered state
    goes in `_DATE_ORDERED_JURISDICTIONS` (core and api-v3) once its scraper dates every version.
- **OPEN-602: Georgia's version names have stages, its papers are not versions, and its versions are ordered by the site's document number.**
  * **Stages** (`note_stage()` in openstates-core `utils/version_ordering.py`, exact shapes, last in the function): "LC n n/a"
    introduced; House substitutes "LC n nS/hs", "/hcs", "/hss", "/hrcs", "/rcs" and Senate committee substitutes "Sen Ctee Sub LC ...",
    "Committee Sub LC ..." amendment; "SCSFA to HB n", "SFA to HB n", "Adopted Senate", "Read and adopted LC ..." chamber passage;
    "HB n/AP*" final passage. Spaces are collapsed first (Georgia types names by hand). 278 of 303 names had no stage, now 0.
  * **Not versions** (Georgia's entry in `_PROCEDURAL_DOCUMENT_NOTE_PATTERNS`, so `is_bill_version` is false): "Local Ad" (the
    newspaper notice of intent to introduce a local bill), floor amendment papers ("Floor Amend 1 AM 47 0219", "Sen Floor Amend
    1A"), fiscal notes, auditor's certifications.
  * **Order:** `version_sort_key(..., "Georgia")` puts the site's document number (from the link URL, `document_number()`) first
    (`_DOCUMENT_ORDERED_JURISDICTIONS`); the stage breaks a tie. Georgia's own `Version` field (`_version_id`) is not an order.
  * **Where:** openstates-core PR #115. api-v3 imports these rules (OPEN-538), so it follows when its core pin moves.
  * **Do not** order Georgia by stage or by `_version_id`, or add a second Georgia list; a new Georgia name goes in the same shapes.
- **OPEN-593: Virginia's substitutes are ordered by LIS file number** (openstates-core #113, not yet live).
  * **Core:** `document_number()` in `utils/version_ordering.py` also reads Virginia's LIS file number
    (`lis.blob.core.windows.net/files/<n>.PDF`, the **largest** of a version's files) as `version_sort_key`'s last
    tiebreaker, the slot Arizona's (OPEN-368) and Georgia's (OPEN-602) numbers use, but the largest file rather than the smallest; and for Virginia an amendment-stage version's ordinal is 0
    ("Subcommittee #3" and "Secondary" were read as ordinals). The stage still leads.
  * **Measured (Mac replica, 2026-11-16):** 565 Virginia bills change order (528 in 2026, 37 in 2027), 141 change their
    latest version; a recompute would correct 4,763 stored comparisons in those 565 bills. Checked against the bills'
    own action dates: 2026 pairs 462 agree, 1 contradicts; the 2027 carried-over session's re-published files only mostly
    (23 / 7).
  * **Release:** image, api-v3 rebuild on both hosts, `recompute-diff-order va` (dry run expects corrected=4,763), then
    the broker's `refresh_bill_version_order --jurisdiction VA`.
  * **Do not** add a second Virginia ordering rule or read an ordinal from a Virginia substitute's name. Other states'
    remaining same-key ties (Florida `pb`/`Filed`, Michigan House/Senate pairs) come out right in today's walk order
    and are not covered by a rule.
- **OPEN-529: Alabama's pre-diff cleaner also drops the Enrolled signature and certification block, the front header (bill number, tracking code, sponsor, "RFD:", "First Read:") and spacing inside a line.**
  * **Where:** the same `_clean_al_text` (OPEN-372) in openstates-core `cli/text_extract.py`, through the one `apply_prediff_cleaning` chain. The cut points are found on the text as printed, before the older rules.
  * **Effect on all 917 comparisons:** changed lines 45,968 → 33,416; comparisons 95%+ noise 364 → 1; none gets more changed lines; 409 Enrolled comparisons become empty. Every cleaned document is a continuous slice of the old cleaned text (checked over all 2,923).
  * **Released:** core PR #93 (`a7d3a8fe`). It needs an image and `recompute-diff-order al` **without** `--flags-only`, because the comparisons change.
  * **Do not** add a second Alabama cleaner.
- **OPEN-223: Massachusetts compares the law as signed with the bill as filed again, and cleans both first.**
  * **Where:** openstates-core `cli/text_extract.py`. `_diff_baseline()` picks the text each document is compared with, for both diff paths: the previous version's document of the same media type (OPEN-217), except that a Massachusetts HTML document (the "Chapter Law Text (Enacted)") with no HTML before it is compared with the previous version's PDF ("Bill Text"). `_clean_massachusetts_text()` (OPEN-400's cleaner, extended) drops the page-footer tail (through the shared `_drop_page_footer_lines`) and puts one clause per line (breaks after `. ; : ,` and `:-`); across the two renderings only (`cross_media`, PDF against HTML) it also drops the title line, the enacting clause and the "Approved, <date>." line and removes double quotes, because each exists in one rendering only. Two documents of the same rendering keep all four.
  * **Effect on the 291 stored comparisons (replica, 2026-11-13):** no unchanged line 193 → 7; changed words 1,221,228 → 591,483; none worse; the title, enacting clause and "Approved" lines no longer appear as additions; H 5555 and H 4240 are no longer larger than their documents. The 73 Massachusetts chapter laws archived after OPEN-217 get a comparison too. Every other state is unchanged (a 12-state sample of 2,620 documents compared byte for byte).
  * **Released:** not yet (openstates-core PR #96). It needs a scrapers image, then `recompute-diff-order ma` **without** `--flags-only` (dry run first: expect 364 corrected, 0 nulled), Ramon's go; PLAN-state-specific-handling puts stored-data changes after launch, so the timing is his call.
  * **Do not** add a second Massachusetts cleaner or a second cross-media rule: a new exception goes in `_diff_baseline`. Massachusetts' cross-bill lineage (a new bill number for each amended version) is OPEN-108/OPEN-109, not this.
- **OPEN-530: Alabama PDFs are read without their struck-out words.**
  * **Where:** `openstates/fulltext/al.py` (`handle_alabama_pdf`, the `"al"` PDF entry). It finds thin drawn rules at mid-line height over a character, removes those characters from a copy of the PDF, and reads the copy through the unchanged pdftotext path.
  * A PDF with no strike reads exactly as before. A PDF PyMuPDF cannot open is an extraction error, with no fallback that would bring the struck words back.
  * **Scope:** 984 of 2,923 documents (514 bills). SB 292 now reads "Class D felony".
  * **Released:** core PR #94 (`a89dd31c`); `pymupdf` is declared in core's pyproject. It needs an image and `os-text-extract refresh-extraction al` (dry run first).
  * **Do not** add a text-level "struck words" cleaner for Alabama: the strike is only in the drawing.
- **OPEN-560: Louisiana, Nebraska and Washington PDFs are read without their struck-out words, by the same reader (since joined by North Carolina, Georgia and Nevada).**
  * **Where:** `read_without_struck_text(extract)` in openstates-core `fulltext/al.py` wraps each state's own PDF extractor (`extract_sometimes_numbered_pdf` for la and ne, `extract_line_numbered_pdf` for wa) in `CONVERSION_FUNCTIONS`, so the extractor reads the copy with struck characters removed by OPEN-530's `without_struck_text`. Washington's HTML reader and the empty "(( ))" marks: see OPEN-580 below.
  * **Only left-to-right text is measured.** The whole-archive comparison found Louisiana's redistricting maps (pages turned 90 degrees) losing parish labels to the parish borders; text in any other direction is read as before.
  * **Whole-archive comparison (2026-11-15, the Mac's archive copy):** LA 10,468 PDFs, 3,391 change; NE 3,383, 1,691; WA 5,818, 3,677. No document gains a character apart from 18 WA documents where the old reader had dropped a printed line. `scripts/open560_compare_struck_text.py` in core repeats it (read-only).
  * **Released:** not yet (openstates-core PR #99). It needs a scrapers image, then `os-text-extract refresh-extraction <state>` for la, ne and wa (dry run first, Ramon's go).
  * **States wrapped since (all on core main, 2026-11-16), each with `extract_sometimes_numbered_pdf`:** nc (OPEN-584, core #109), ga (OPEN-601, core #112), nv (OPEN-591, core #111). The strike-reader states are now la, ne, wa, nc, ga and nv; a core test pins that exact set. Each needs the same release: a scrapers image, then `os-text-extract refresh-extraction <state>` (dry run first, Ramon's go). For nc, `refresh-extraction` already recomputes the comparisons it rewrites, so a separate `recompute-diff-order nc` is redundant (harmless).
  * **Do not** add a second strike reader or a text-level "struck words" cleaner for these states: add a state by wrapping its extractor with `read_without_struck_text`.
- **OPEN-580: Washington's HTML printings are read without struck-out words or their "((" "))" marks, and the empty marks the PDF reader leaves are taken out.**
  * **Where:** openstates-core `fulltext/wa.py`. `handle_washington_html` (the `"wa"` `text/html` entry) reads `//html` as OPEN-212 did, after taking out every element styled `text-decoration:line-through` (Washington's strike markup), then `drop_deletion_marks` takes out each "((" "))" pair left holding only the removed strikes, spacing and dot or dash leaders. `without_deletion_marks` wraps the WA PDF reader (OPEN-560) and takes out the pairs that hold only spacing. So both printings of a version read "two-year, four-year", with no "((or))" and no "(( ))".
  * **Measured (2026-11-16):** 3,677 of 5,818 WA HTML printings have struck text (102,227 struck spans, every one an inline-styled `span`; no `<s>`, `<strike>` or `<del>`). Washington marks every deletion both ways: strike markup inside "((" "))". "((" also occurs in formulas, chemical names and bill-draft codes, so a pair is taken out only around a real strike, or with nothing at all inside.
  * **Whole-archive comparison (Mac archive copy):** 3,677 HTML documents change; none gains a character, and each loses exactly its struck characters plus marks and leaders. `scripts/open580_compare_wa_html.py` in core repeats it (read-only). On the replica's WA PDF text, 86,793 empty pairs go to 0 with no character gained.
  * **Released:** not yet (openstates-core PR #107). It needs a scrapers image, then `os-text-extract refresh-extraction wa` (dry run first, Ramon's go).
  * **Do not** add a text-level "((...))" cleaner that ignores the strike markup: it would eat formulas and chemical names.
- **OPEN-600: Oregon PDFs are read without the [bracketed] words a bill deletes.**
  * **Where:** openstates-core `fulltext/oregon.py`. `without_bracketed_text(extract_sometimes_numbered_pdf)` is Oregon's `"or"` PDF entry: it takes out every `[ ... ]` span Oregon prints in italic (its deletion mark) and tidies the spacing. A bracket printed upright is kept (a chemical name such as "benzo[c]chromen", a "[,]" in a quotation, fill-in blanks "[ ___ ]"). Amendment papers lose their bracketed words too, so they read as the text would. One space is added where a new word is printed against the closing bracket ("agencies[.]and of", SB 1534), so the words do not run together. Oregon draws no strike line, so Alabama's reader does not apply.
  * **Measured (2026R1, govbot's copy):** 664 version PDFs, 360 change; 419 amendment papers, 163 change; nothing outside a bracket span removed, no word added. `scripts/open600_compare_or_brackets.py` in core repeats it (read-only).
  * **Released:** not yet (openstates-core #114, merged 2026-11-16). It needs a scrapers image, then Oregon's archive; Oregon has no stored text, so nothing to re-extract.
  * **Do not** add a text-level bracket cleaner elsewhere for Oregon.
- **OPEN-511 — Louisiana: Conference Committee Reports are not bill versions either.** Louisiana's entry in
  `_PROCEDURAL_DOCUMENT_NOTE_PATTERNS` (openstates-core `utils/version_ordering.py`, the table OPEN-491 used for its amendment
  papers) also matches `Conference Committee Report, #<N>, House <Adopted|Proposed|Rejected|Withdrawn>, Senate <same>`. The
  report is the conferees' letter listing amendments, not a reprinted bill, so it gets `is_bill_version` False, no diff,
  and is no longer a baseline; the Enrolled bill diffs against the last real version. Measured on the Mac replica (2026-11-08):
  55 documents, Louisiana only; on the 51 affected bills the real recompute changes 103 comparisons (55 report diffs dropped,
  48 Enrolled diffs rebaselined, all smaller). Stage and version order are untouched (that is OPEN-510). **Do not** add a
  conference-report list anywhere else. Not merged, not deployed (openstates-core PR #86): it needs a scrapers image and
  `recompute-diff-order la` (dry run first, Ramon's go), which can be the same Louisiana recompute as OPEN-496 and OPEN-510;
  it blocks Louisiana's switch-on (OPEN-480).
- **OPEN-516: Pennsylvania's text comes from its OpenDocument ("DOC") printing, struck-out words left out.**
  `handle_pennsylvania_odt()` in openstates-core `fulltext/pa.py`. Pennsylvania's DOC link is an OpenDocument zip served as
  `application/msword`, and strike-through is a style there.
  * **What it does:** removes `draw:frame` drawings (change bars, "◄Corrective Reprint" notes) and blanks struck text by
    each piece's effective style (family and name, parent styles, `styles.xml`; a not-struck span inside a struck paragraph
    stays). It then turns ODF space elements into spaces, unwraps inline elements, and serializes with the federal
    `xml_tree_to_lines` (OPEN-210).
  * **Do not** write a second serializer or a regex reader: a regex over `<text:p>` stops at the empty paragraph inside a
    change bar and drops text.
  * **Archiver:** `_sniffed_media_type()` in `cli/text_extract.py` treats an msword-labelled file whose bytes are
    OpenDocument as `application/vnd.oasis.opendocument.text`. That type is used for the magic-byte check, the extension,
    the diff lineage and the stored row. It is the one place a site's wrong label is corrected; add a case there, not a
    second sniffer.
  * **Pennsylvania's PDF is `DoNotDownload`.** The 6,198 PDF documents archived before stay, and api-v3's
    `_archived_row_for` prefers XML, then OpenDocument, then PDF (api-v3 #53).
  * **Measured on 36 real printings:** 0 PDF words lost apart from struck ones; 3,808 struck words removed in 15 printings.
  * **Status:** not merged, not deployed (openstates-core #88, api-v3 #53). After a scrapers image, PA's next nightly
    archive fetches every DOC once (about 6,200); no recompute is needed for the new rows. Already-written LegBot
    artifacts are not regenerated by this.
- **OPEN-517: Massachusetts papers stored as bills get a label that says what they are.** Ramon (2026-11-09): relabel,
  never delete, one label per kind, undoable.
  * **The rule:** `non_bill_kind(jurisdiction_name, bill_title, action_descriptions)` in openstates-core
    `utils/version_ordering.py`, next to the OPEN-498 title rule. It answers only for a bill that rule already calls
    not-a-bill, so a real measure never gets a kind. The answer is `communication`, `study request`, `order` or `report`
    (whatever matches nothing). A committee study order titled only by its subject ("Golf Carts") is known by its
    action "Order reported favorably by committee". `report` and `communication` are new in `BILL_CLASSIFICATION_CHOICES`.
  * **The command:** `os-text-extract relabel-non-bills <state> [--session S] [--dry-run|--commit] [--undo] [--expect N]
    [--list FILE]`.
    * Dry run by default; `--list` writes the per-bill CSV for review.
    * `--commit` keeps the old label in `Bill.extras["ddp_open517_original_classification"]`; `--undo --commit` puts it
      back.
    * Each write requires the row to be unchanged since it was read; otherwise the whole run rolls back.
    * The write does not move `updated_at` on purpose: the broker stores no bill label, and the website reads it live
      from api-v3.
  * **Left alone:** amendment papers (the scraper still yields them and would overwrite the label; OPEN-509) and any
    bill with a recorded vote (the 8 rules items, Ramon 2026-11-08).
  * Its write and summary code is shared with `relabel` (OPEN-546), the general per-state re-label pass; use that for
    any new label rule.
  * **Do not** add a second "is this a bill" list: extend the title table and `_NON_BILL_KIND_RULES`. The website's
    filter for these labels is NEXT-182.
  * **Measured on the Mac replica (194th, 2026-11-10):** 3,132 to relabel (report 1,538, communication 998, study request
    332, order 264), 157 amendment papers and 8 voted items left alone.
  * **Status:** merged (openstates-core #90, dab94675), not run. The run on RDS is a prod-agent step after a scrapers
    image, on Ramon's go.
- **OPEN-518: the Massachusetts scraper saves those papers, labelled, instead of skipping them** (replaces OPEN-508's
  skip; Ramon 2026-11-09: "i don't want anything removed from our data").
  * **The scraper:** `MABillScraper.label_non_bill` (openstates-scrapers `scrapers/ma/bills.py`) calls `non_bill_kind`
    above, with the page's own title and the scraped actions, and sets the classification. It has no title list of
    its own. A blank or missing title, an amendment paper, or a core without `non_bill_kind` gives an ordinary bill;
    nothing is skipped. Voted papers are labelled too (Ramon 2026-11-10: the eight voted items are rules and orders,
    not bills).
  * **The import keeps the saved label:** `BaseImporter.keep_extras_keys` (openstates-core `importers/base.py`) names
    extras keys a re-import copies over from the stored row when the scraper did not send them. `BillImporter` keeps
    only `ORIGINAL_CLASSIFICATION_KEY` (now defined in `utils/version_ordering.py`). Without it, a re-scrape replaces
    extras wholesale and `relabel-non-bills --undo` loses its saved label. **Do not** write a DDP value into a scraped
    row's extras without adding its key here.
  * **Status:** not merged (openstates-scrapers #85, openstates-core #91). Same image as OPEN-517, after its relabel
    run.
- **OPEN-509/OPEN-512: Massachusetts amendment papers are labelled `amendment` and listed on their real bill**
  (Ramon 2026-11-15).
  * **The pre-pass:** `MABillScraper.scrape_amendment_papers` (openstates-scrapers `scrapers/ma/bills.py`) runs before
    any bill is scraped. It fetches the pages of list rows with no docket number (every amendment paper has none) and
    keeps those that core's `non_bill_kind` calls an amendment paper. From each paper's history it reads the bills it
    links to and any "Substituted ... for X" line. `resolve_paper_parents` then follows paper-to-paper links to the
    real bill; a paper that reaches no bill, or two, is not linked. The fetched pages are reused by `scrape_bill`.
  * **On the real bill:** a draft the chamber substituted becomes a version noted `Substituted text (S3178)` (core's
    `note_stage` ranks it between `Bill Text` and the enacted law); every other paper becomes a `BillDocument`.
  * **The label:** `amendment` (added to `BILL_CLASSIFICATION_CHOICES` in openstates-core and to api-v3's
    `NOT_BILL_TYPES`). `label_non_bill` now saves `ORIGINAL_CLASSIFICATION_KEY` for every kind it sets. `page_titles`
    reads the h1 as the title when there is no h2, except for the "Bill <number>" placeholder.
  * **Do not** read a paper's parent from the Documents list (its Title is not the page title), and do not add a
    second amendment-title rule: core's `_NON_BILL_KIND_RULES` decides.
  * **OPEN-568: a paper's roll calls are recorded on its real bill.** `MABillScraper.paper_vote_event` (both the
    House and Senate branches build their vote through it) names the parent the pre-pass stored in
    `self.paper_parents`, only when this run scrapes both (`self.group_of`), and keeps the paper's number in
    `extras["ddp_amendment_paper"]`. The H-or-S check is in `paper_vote_event` itself (any other number leaves the
    vote on the paper). The **dedupe key still uses the paper's number**, so the import moves the stored row instead of adding a second one: **do not** "fix" the key
    to the parent's.
    * **The pair rule:** the import deletes a bill's stored votes that the run did not bring again (RUNBOOK,
      "A targeted `bill_no=` rescrape is not additive"), and a real bill's votes now come from its own history and
      its papers'. So `scrape()` always scrapes a paper and its real bill together (`with_paper_pairs`: a
      `bill_no=`, one-chamber or chunk run adds the rest of the group, and records the run's groups). Every bill
      of a group holds its votes back until the whole group is scraped (`group_member_done`). If any member's page
      or any page of its history failed, **none of the group's votes is sent** that run, so the import deletes
      none of them (the bills that were read are still saved; a member whose page failed is not, as for any
      bill). Otherwise they all go out, and a roll call cited twice
      (by the real bill and a paper, or by two papers) goes out once, the real bill's own first. A paper whose real
      bill is not in the list is in no group: its votes stay on it, as before.
    * **This holds only on the bills-only path.** The cloud collector runs Massachusetts with `--scrape bills`
      only (`cloud_collector.py`, `scrape.votes_scraper: false`), which is how MA runs today (`cloud_path: true`).
      `run-scrape.sh` also runs MA's separate `votes` scraper (OPEN-50 auto-detect): its journal votes would bring
      votes for a held-back real bill, and the import would then delete the votes already moved to it. If MA ever
      goes back to `run-scrape.sh`, that run does not have this protection.
    * **The cases it cannot cover:** a paper whose page failed in the pre-pass *and* again in the run is not
      known to be a paper, and a paper whose history page 1 failed in the pre-pass *and* again in the run names no
      real bill ("OPEN-509: amendment paper ... names no single bill; not linked"). Either way it is in no group; the real bill's votes go out, and the import deletes the votes
      already moved from that paper until the next run brings them back (new row ids). If only the pre-pass fetch
      (of the page or of history page 1) failed, the paper is read in the run, is not linked, and its stored votes
      move back to it for that run (nothing deleted).
    * 81 of the 87 paper votes of the 194th move (Mac replica, 2026-11-16); the other 6 (H 4271, H 5349, H 61) are
      2026-08-23 `votes.py` copies of roll calls already on the real bill. `votes.py` is not changed: mapping it
      too would duplicate them.
    * **Status:** openstates-scrapers #107, merged 2026-11-16; needs an image and a Massachusetts run.
  * **Status (OPEN-509/512):** merged 2026-11-16 (openstates-scrapers #99, openstates-core #103, api-v3 #61).
    Release: a scrapers image with both, api-v3 on both instances, then Massachusetts' next run (the import
    relabels and links; no separate step). Which image first carries them is not recorded here.
- **OPEN-609: Massachusetts catch-up runs** (`ma/bills.py` `scrape()`/`catch_up()`, `ma/catchup.py`; design and
  measurements in `notes/ma-journal-change-signal-20261117.md`). A whole run given `start=` reads only the bills named
  in the House and Senate journals dated from 21 days before `start=`, signed on the Session Laws page in that time,
  on hearings posted since the last run, new in the Documents list since the last run, or left unread by the last run.
  It reads every bill instead when there is no record of the last run (`ma_catchup_<session>.json`, carried by
  `cloud_collector.py`), when the last full walk is 28 days old (`catchup.FULL_WALK_EVERY`, the periodic backstop),
  or when any source fails or answers empty: never a partial run. A quiet run raises `EmptyScrape`. The journal
  listing (`JOURNAL_MONTH_URL`, `JOURNAL_PDF_LINKS`, `journal_date`) lives in `ma/votes.py`, shared with its
  (still off) votes scraper: **do not add a second journal reader.** Partial runs (`chamber=`, `bill_no=`, chunk)
  and runs without `start=` are unchanged and neither read nor write the record. The OPEN-568 paper groups still
  hold: `with_paper_pairs` runs on the selected bills, and the amendment pre-pass still reads every paper (about
  1,390 bill pages a run, the largest part of a catch-up run's requests).
  * **Status:** openstates-scrapers #119 and the collector half here (not merged); MA's
    `scrape.start_filter` stays `false` until both are in a live image (a separate manifest PR, Ramon's go).
- **OPEN-541: `os-text-extract reverse-action-order <state>` reverses a state's stored bill action order** (plan
  PLAN-state-specific-handling §6 Phase 2). A scraper order fix (LA OPEN-534, NE OPEN-535) changes only bills it
  re-scrapes. This pass reverses the stored history in one **silent window**, so one state never holds both orders.
  * **Done for every state that needed it:** la and ne (2026-11-16 02:47-02:48 UTC: LA 2,609 and NE 1,847), nc
    (OPEN-543, 2026-11-16) and **us (OPEN-542, 2026-11-17 ~02:11 UTC: 39,263 bills; 31,441 latest actions changed;
    the 03:00 run on v62 clean, prod agent `28de4d6`, `0c96e78`)**. `validate_bill_stages` on the Mac replica
    (2025 onward, all 16 states, 2026-11-17) finds no state storing actions newest first. **Never al.** A state
    onboarded later that stores newest first is fixed in its scraper first, then this pass.
  * **Decided 2026-11-17 (Ramon, "Remove it"):** the manifest check below goes (OPEN-544); the per-bill mark already
    stops a second reversal. Until that core change is in the live image, the override is needed for any state.
  * **The command:** `os-text-extract reverse-action-order <state> [--session S] [--dry-run|--commit] [--undo]
    [--expect N] [--list FILE] [--manifest PATH] [--even-if-manifest-says-oldest-first]`. It has the same shape as
    `relabel-non-bills`.
    * Dry run by default (`reversed=N actions=M skipped_...`, plus how the dates run: `newest_first`, `same_day`,
      `mixed`).
    * `--commit` needs `--list`. The CSV (bill, old and new order as action ids, old and new dates) is the audit
      record. It only takes its name after the database commit; a refused or rolled-back run leaves none.
      `--expect N` aborts before writing unless exactly N bills would change.
    * It refuses unless the manifest (`--manifest`, default `$DDP_JURISDICTIONS_MANIFEST` or `./jurisdictions.yaml`)
      says `actions.newest_first: true`, unless `--even-if-manifest-says-oldest-first` is passed.
      **After OPEN-544** the manifest has no `actions` block, so the command reports the label `missing` and refuses
      unless `--even-if-manifest-says-oldest-first` is passed: a later state's reversal passes the override, with the
      dry run's date-direction counts as the evidence.
    * A reversed bill gets `extras["ddp_open541_actions_reversed"]`. A second run skips it, and the bill import keeps
      the key (`keep_extras_keys`, as OPEN-518). Bills whose dates already run oldest first, and one-action bills,
      are skipped.
    * The first and latest action fields are recomputed with the importer's `update_bill_fields`, so a bill whose
      latest action changes moves its `updated_at`.
    * `--undo --commit` reverses the marked bills again. It is the rollback inside the same window (scrape paused),
      not for use after a re-scrape.
  * **Pause the state before the new image scrapes it.** The state's scrape and the broker's bill-event task must be
    paused before the first run of the new scrapers image for that state. If the state is scraped once on the fixed
    image before the pass, bills whose actions are all on one day or run in mixed directions cannot be told apart
    from old ones, and the pass would flip them back to newest first (and mark them).
  * **On a host or container:** pass `--manifest <path to a state list that has #370>` (the image carries the list
    it was built with), and write `--list` to a lasting path, not inside a throwaway container.
  * **`updated_at` moves** on changed bills, so ddp-sync's `updated_since` reads see them as updated. Keep the run
    inside the silent window and check ddp-sync's reaction.
  * **Run order (LA, then NE):**
    1. Merge #370, openstates-scrapers #91/#92 and this entry's PR (#369); build the scrapers image.
    2. Pause the state's scrape and the broker's bill-event task before the image's first run for that state, and
       rule out a signalled check (no run of the state in flight, no check queued or running, `recheck_requested`
       false; see OPEN-546 below).
    3. Dry run with `--manifest`.
    4. On Ramon's go: `--commit --expect N --list <lasting path>`.
    5. Set the state's label back to `actions.newest_first: false` (before OPEN-544; since 2026-11-17 there is no label to set).
    6. Silent broker re-bootstrap; confirm 0 events went out.
    7. Resume the scrape.
- **OPEN-546: `os-text-extract relabel <state>` re-applies a state's label rules to its stored actions and bills**
  (plan PLAN-state-specific-handling §6 Phase 3). When a state's action or bill rule moves from the broker into the
  ETL, the scraper applies it only to bills it re-scrapes. This pass applies the same rule to the stored history, in
  the state's **silent window**, before the broker reader is deleted.
  * **The rule:** `classify_action(*, description, classification, chamber, date)` and
    `classify_bill(*, identifier, title, classification)` in openstates-core `openstates/ddp_states/<state>.py`. Each
    returns the whole label list and must give the same answer on its own output; `state_rule(state, name)` in
    `openstates/ddp_states/__init__.py` finds it. **No state module exists yet** (OPEN-545, OPEN-547 to 552 add them);
    a state without one is refused. **Do not** put a state's label rule anywhere else (a second table, the broker, a
    script).
  * **No scraper calls `ddp_states` yet (2026-11-17, OPEN-615).** The scraper is meant to call the same function on
    what it parses; wiring the state's scraper is an acceptance line of each state's ticket. A state relabelled before
    its scraper is wired gets the old labels back on its next re-scrape, so wire the scraper first (same image).
  * **The command:** `os-text-extract relabel <state> [--session S] [--dry-run|--commit] [--expect N] [--list FILE]
    [--undo LIST]`. Same shape as `reverse-action-order`.
    * Dry run by default: `actions changed=N unchanged=M | bills changed=N unchanged=M`, then old -> new counts.
    * `--list` writes one CSV row per changed action or bill (kind, id, bill, identifier, session, order, date,
      chamber, text, old, new). `--commit` needs it, and the committed list is the audit record (no second label is
      stored). It takes its name only after the database commit; an existing list is never overwritten. `--expect N`
      counts bills and actions together.
    * Only `classification` is written, never text, date, order or chamber. Each item is written only if its labels
      and the rule's inputs are unchanged since the read; otherwise the whole run rolls back. A rule that would move
      again on its own output is refused, so a second run changes 0.
    * A bill whose action labels change has its computed fields recomputed by the importer's `update_bill_fields`
      and its `updated_at` moved (as a re-import would). `latest_passage_date` is the one a label moves; the other
      three (`first_action_date`, `latest_action_date`, `latest_action_description`) are rewritten too if an older
      import left them stale. **Both the dry run and the commit print how many bills each of the four changes on**
      (`bills whose computed fields would change: ...`; OPEN-615); the dry run counts with the same function on
      in-memory copies and writes nothing.
    * A bill whose own label changes and none of whose actions' labels do is written without moving `updated_at`
      (as `relabel-non-bills`); with an action change too, `updated_at` moves as above. **That label is stored
      downstream:** ddp-sync copies a bill's `classification` into its knowledge-base text ("Type:",
      `ingestion/sources/openstates.py`) and metadata (`ingestion/metadata.py`), and finds changed bills through
      `updated_since`, so it keeps the old type until the bill's next real update. A state ticket that changes bill
      labels (Virginia, OPEN-545: 1,579 HR/SR/HJ/SJ) says how that copy is refreshed.
    * `--undo LIST --commit` puts back the old labels from a committed list (the window's rollback), only for items
      that still hold the new labels.
  * **Scorecards (Ramon, 2026-11-16):** a re-label never touches vote events, but the broker reads action labels for
    which votes count (`motion_eligibility.py`, `openstates_service.py`), for stages and bill events (`bill_stage.py`,
    `bill_events.py`), and stores `latest_passage_date`. So each state's run needs the silent window, the four
    scorecard checks on its ticket (OPEN-546 comment), and Ramon's go per state.
  * **Silent window: switching off the broker's scheduled bill-event task is not enough (OPEN-615).** ddp-sync's
    end-of-scrape signal (BROKER-300, `POST /api/openstates-bill-events/check/`) queues a check for one state directly,
    whether or not the scheduled task is on, and a signal that could not be queued stays recorded
    (`JurisdictionEventWatermark.recheck_requested`) for the next run to pick up.
    Before the change, in this order: (1) the state's scrape is paused **and no run of it is in flight** (a run
    already going sends its signal when it ends: wait for it to finish); (2) no check for the state is queued or
    running; (3) its `recheck_requested` is false. If it is true with no check queued or running (the signal could
    not be queued), the prod agent runs one check for that state by hand (`check_openstates_bill_events("<st>")`)
    and lets it finish **before** the window opens, so it publishes only on the old data; then re-check (2) and (3).
    This applies to every silent window (`reverse-action-order` too).
  * **`relabel-non-bills` (OPEN-517)** shares this command's guarded write and summary code and keeps its own
    Massachusetts rule. A new label rule uses `relabel`, not a new command.
  * **Massachusetts stays on its own path for now:** `relabel-non-bills` and `non_bill_kind` (OPEN-517). OPEN-551
    moves its action rule here, so there is one home in the end.
  * **Status:** openstates-core #110 merged (`53a7ce03`), in v62 (core `44c3b8dc`); not run on any state. OPEN-615's
    review fixes (core, this entry) come before the first state's run. Each run is a prod-agent step.
- **OPEN-564: `os-text-extract remove-stale-documents <state>` removes saved documents whose version note is gone.**
  The archiver keys a saved document on `(bill, version_note, version_date, source_url)`. When a scraper renames a
  version, the next archive saves the same file again under the new note, and the old row stays behind, matching no
  version. Alabama, 2026-11-15: OPEN-528 reversed Alabama's action order, and Alabama names each amendment or
  substitute paper after the action that carries it, so 456 papers were saved a second time.
  * **The rule:** a row is stale when its note is not a version note of its bill any more. It is removed only when a
    row that is **not** stale keeps the same file (same bill, address and `sha256_hash`). The last saved copy of a
    file is never removed: no copy, a different file at the same address, or two stale rows that only have each
    other are kept and counted (`kept_last_copy`, `kept_no_file_hash`). The S3 archive copy is not touched.
  * **The command:** `os-text-extract remove-stale-documents <state> [--session S] [--dry-run|--commit] [--expect N]
    [--list FILE]`. Same shape as `reverse-action-order`: dry run by default; `--commit` needs `--list` (one CSV row
    per removed row, with the row that stays), the list takes its name only after the commit, `--expect N` aborts
    unless exactly N rows would go. The commit locks the state's documents and plans again inside the transaction;
    any change since the read rolls everything back. No `--undo`: the file stays in the kept row and in S3.
  * **Output:** `documents=N stale=N removed=N kept_last_copy=N kept_no_file_hash=N`, then
    `after: documents=N distinct (bill, address)=N removed_versions=N`. Mac replica, 2026-11-15: al
    `documents=3379 stale=456 removed=456 kept_last_copy=0`, after `2923 = 2923`; la and ne `stale=0`.
  * **Afterwards** run `recompute-diff-order <state>` (dry run, then commit on a go), so the kept rows' diffs and flags
    are recomputed against their real neighbours.
  * **Which states can do this again:** a state whose version notes come from action text. Alabama does
    (`add_version_link(row["matter"], ..., on_duplicate="ignore")` in the action loop, so the first action naming a
    file names it). Louisiana and Nebraska do not: their notes are the document links' own text, so their action
    order flip (OPEN-541) does not rename versions. Louisiana's amendment notes do carry a status ("..., House
    Proposed, Senate Adopted"), so a status change would rename one the same way: this command is the clean-up then.
  * **OPEN-569: the note and the date.** From OPEN-569 a row is stale when its (note, **date**) is not a version of
    its bill: Alabama's scraper dates its versions, so the next archive saves each file again under its date and the
    undated copy is stale (0 rows change in any other state on the replica, 2026-11-16).
  * **Also OPEN-564: Alabama line-edit amendments are not-a-version by their text.** `is_amendment_text()` in
    `utils/version_ordering.py` (per-state `_AMENDMENT_TEXT_OPENING`, Alabama only): text that opens with an edit
    instruction ("Replace line 54 on page 2 with the following:") and has no enacting clause. `is_bill_version()`
    takes an optional `raw_text` and is false for such a text; the archiver and `recompute-diff-order` pass the text,
    and both leave such a document out of the diff lineage (no diff, not a baseline). Full substitutes stay versions
    (Ramon, 2026-11-15). **Do not** add a second flag for this; extend `_AMENDMENT_TEXT_OPENING` for another state.
  * **Check afterwards:** a second dry run with the override shows `reversed=0`; spot-check LA HB 1 and NE LB 1,
    LB 1105 and LR 384; run `validate_bill_stages`; keep the change-list file.
  * **Do not** reverse action order by hand or in a one-off script. A new order fix uses this pass in its silent
    window.
  * **Measured on the Mac replica (2026-11-15):** LA 2,590 of 2,616 bills newest first, NE 1,845 of 1,847, 0 oldest
    first in either.
  * **Status:** merged (openstates-core #100, `7ed499b9`), not run. The run is a prod-agent step on Ramon's go, per
    state, after launch.
- **OPEN-539: each stored comparison names the document it was made against (`diff_baseline_id`).** PLAN-state-specific-handling
  §4.4, "the one new stored value".
  * **The column:** `ddp_bill_version_document.diff_baseline_id` in openstates-core (integer, nullable, migration `0051`, no
    backfill; no foreign key, no index). It is the `id` of the row of the same bill whose text `diff_from_previous_version`
    was computed against. Null = no stored comparison, or a comparison stored before the column existed and not stamped yet.
  * **Who writes it:**
    * The archiver writes it in the same `create()` as the comparison.
    * `recompute-diff-order` (full mode) and `refresh-extraction --commit` write it with every comparison they leave stored.
      `--flags-only` never touches it.
    * The archiver's retry path and `remove-stale-documents` clear the ids that named a row they delete.
  * **The stamping pass:** `os-text-extract recompute-diff-order <state> --baseline-only [--session S] [--dry-run|--commit]
    [--expect N] [--list FILE]`.
    * It has the shape of `remove-stale-documents`.
    * It writes only the id, never the comparison or `updated_at`, and only where the recompute reproduces the stored
      comparison.
    * `--commit` refuses a state where any stored comparison would change (`not_stamped_comparison_would_change` above 0).
      For such a state the full recompute is the step; it stamps as it writes.
    * After a commit it prints `after: comparisons_without_baseline=N`. A state is stamped when N is 0.
  * **Do not** compute "which version a comparison is against" again downstream (ddp-sync `_diff_baseline_index`, the
    LegBot sample script, ddp-next `isFullText`). Read this column through api-v3 (OPEN-540) once the state's count is 0.
  * **Measured on the Mac replica (2026-11-16):** 67,628 stored comparisons, 67,517 to stamp; Alabama has 111 that the
    OPEN-569 recompute will rewrite.
    * Against ddp-sync's rule (over the Mac api-v3), 1,266 comparisons differ: va 774, az 358, mi 19, al 115; every other
      state 0. In each one the stamped document reproduces the stored comparison byte for byte.
    * va and az: a version with two or more PDFs. The recompute keeps the last by row id; the archiver and api-v3 keep the
      last by URL.
    * List: `notes/open539-baseline-differences-20261116.csv`. Repeat with openstates-core
      `scripts/open539_compare_baselines.py` (read-only).
  * **Status:** openstates-core #105, not merged, not deployed.
  * **Release:** migration `0051` on RDS (the Mac replica's structure sync adds the column), then a scrapers image, then per
    state a `--baseline-only` dry run and, on Ramon's go, `--commit --expect N --list <lasting path>`.
- **OPEN-578: one rule for which document of a version is the baseline (`_version_document_order`).** openstates-core
  `cli/text_extract.py`.
  * **The rule:** a version's documents are walked in (media type, source_url) order; the last of each media type is that
    type's baseline for the next version. Within a type that is the last source_url, the rule api-v3's
    `preferred_document` (`api/document_choice.py`) uses within a type.
  * **Who calls it:** the archiver (its link walk) and `recomputed_diffs_for_documents` (so `recompute-diff-order`,
    `--baseline-only` and `refresh-extraction`). The recompute used to walk stored rows by row id.
  * **The change list:** `recompute-diff-order <state> --list FILE` now also works without `--baseline-only`: one row per
    document whose stored comparison or `diff_baseline_id` would change, with the stored id, the document(s) whose text
    reproduces the stored comparison (`old_comparison_made_against`) and the new baseline.
  * **Measured on the Mac replica (2026-11-16, read-only):** va 1,742 baselines move (829 stored comparisons change,
    913 keep the same text), az 355 (47 change, 308 same), mi 3 (same text), al 1 (the new rule reproduces it); every
    other state 0. All 774 va and the 343 az "same version, other document" rows of the OPEN-539 list are among them. List:
    `notes/open578-baseline-moves-20261116.csv`.
  * **Do not** pick a version's document by row id anywhere else; call this function.
  * **Status:** openstates-core #108, not merged, not deployed.
  * **Release:** a scrapers image, then per state (va, az) export first, `recompute-diff-order <state> --dry-run --list`
    (expect corrected=829 for va, 47 for az, plus whatever else is pending), `--commit --list <lasting path>` on Ramon's
    go, then the OPEN-539 `--baseline-only` pass (expect `not_stamped_comparison_would_change=0`).
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
  `quality_check.py`'s `OCD_TO_CODE` (built from `jurisdictions.yaml` since OPEN-327) but the
  same idea; if you're about to write a third one of these OCD-jurisdiction maps, check whether
  one of the two existing ones can just be imported instead. `--dry-run` prints without writing.
- **`audit-motion-texts.py`** (repo root) — read-only report: every distinct `(motion_text,
  classification)` pair per jurisdiction with vote/pass/fail counts, written to
  `motion-text-audit/<jurisdiction>.md`. Use this to find motion text patterns the YAML config
  doesn't cover yet, before hand-writing new regexes.

- **`check-mi-vote-tallies.py`** (repo root, OPEN-424) — read-only: compares each stored Michigan
  roll call's yes/no voter rows with the YEAS/NAYS printed in its own motion text and reports
  `ok` / `no-yea` / `nays-high` / `other`. Needs no outside data, so it is the before/after check
  for any Michigan journal-parser fix and rescrape (`--bills FILE`, `--expect-clean`). Not a
  repair: the repair is a rescrape (`notes/plan-open424-mi-journal-rescrape-20261026.md`).

- **`check-wa-chapter-citations.py`** (repo root, OPEN-432) — read-only: per Washington session, how many
  bills have a "Chapter N, YYYY Laws" action but no stored `chapter` citation; `--bill-list FILE` writes them
  as a `bill_no=` list for a targeted rescrape, `--verify` is the after-check (exit 1 while any remain). Not a
  repair: the citation comes from the legislature's service, so the repair is a rescrape
  (`notes/plan-open432-wa-chapter-citation-rescrape-20261026.md`). Uses `quality_check.Report` for its output.

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

### WAF decision catalog, and OPEN-419's by-design note extended (OPEN-464, 2026-10-30)

Which jurisdiction gets WAF handling, and how, is decided in several places; this is where each one
lives and what should drive it. `jurisdictions.yaml`'s `waf.profile` says WHICH WAF implementation
applies (compared against `RESILIENCE_PROFILES`'s keys by `check-jurisdiction-drift.py
--openstates-core-root`, OPEN-464). `waf.fargate_safe` is a separate question: whether that
implementation's cookie can be produced from an arbitrary cloud IP. `mi` and `fl` share
`waf.profile: cookie_provider` but answer `fargate_safe` differently -- see `jurisdictions.yaml`'s
own header comment for why (mi's cookie can only be minted by the Mac; fl's warm-up runs wherever
the scraper does).

| Where | What | Driven by |
|-------|------|-----------|
| `openstates-core/openstates/utils/resilience_profiles.py` | `RESILIENCE_PROFILES` -- which jurisdictions get WAF/cookie resilience machinery at all | `waf.profile != "none"`, compared by the drift check (OPEN-464) |
| `openstates-core/openstates/utils/mi_cookies.py`, `fl_cookies.py` | the actual cookie-acquisition mechanism per jurisdiction (the leaf implementations `RESILIENCE_PROFILES` points at) | not separately manifest-driven -- genuinely code, one per WAF vendor |
| `ddp-open-states/cloud_collector.py` (~line 626, `if source == "mi"`), `cloud_archiver.py` (~line 274, `if state == "mi"`) | the published-cookie gate: refuses a bare run with no fresh Mac-minted cookie (OPEN-188) | genuinely code, by design -- see below |
| `ddp-open-states/verify-jurisdiction` (`fargate_refusal()`), `ddp-open-states/probe-on-fargate` (`refused_states()`) | refuses to run the onboarding probe on Fargate for a state whose cookie needs the Mac's mint | `waf.fargate_safe` (OPEN-464; previously two independent hard-coded `{"mi"}` sets, one per script) |
| `ddp-agents/config/scrapebot_jurisdictions.yaml` (MI only) | ScrapeBot/CAMS's own per-jurisdiction cookie-mint-and-publish schedule | a different repo/deployable -- see below |
| `ddp-sync/mi_cookie_publish.py` | the daily job that mints and publishes MI's cookie for `cloud_collector.py`/`cloud_archiver.py` to read | a different repo/deployable -- see below |

**Why `cloud_collector.py`/`cloud_archiver.py`'s MI gate stays hard-coded:** this is "genuinely
code" behaviour in OPEN-318's own scoping sense -- its note explicitly excludes "per-state
behaviour that is genuinely code (MI-specific archiver path, `RESILIENCE_PROFILES`, per-state
eligibility rules, timeouts)" from the drift check. It is not "which WAF profile applies" (that
question is `waf.profile`, now compared); it is "how this one profile's cookie actually gets
produced for a real scrape," the same question `waf.fargate_safe` answers for the onboarding
probe above -- but here the two code paths already read `cloud_collector.py`'s own memory-store
cookie directly rather than branching on a manifest field, and OPEN-188's own acceptance criterion
("a bare run... must be impossible by construction, not convention") is already satisfied without
one.

**Why `ddp-agents` and `ddp-sync`'s copies stay hard-coded, by design (extends OPEN-419):**
OPEN-419 (2026-10-22) already found and recorded this exact shape of gap for a sibling list,
`ddp-sync`'s `scrapebot_fallback`: *"The manifest's existing `waf.profile` does not predict it (FL
has the same profile and is not on the list), so it cannot be derived."* The same reasoning applies
here, for the same reason: `waf.profile: cookie_provider` is true for both `mi` and `fl`, so it
cannot distinguish `ddp-agents`' MI-only `scrapebot_jurisdictions.yaml` entry or `ddp-sync`'s
`mi_cookie_publish.py` job from a hypothetical future FL-shaped equivalent. Unlike the probe's
Fargate refusal (this repo's own onboarding-safety gate, closed above with `waf.fargate_safe`),
these two live in a different repo and a different deployable each -- `ddp-open-states` has no
runtime access to either one's code or config, and building a second local copy of
`waf.fargate_safe` just to describe them would be exactly the kind of duplicate-source-of-truth
list OPEN-318 exists to retire, not close. They stay hard-coded, same as `scrapebot_fallback`,
until `ddp-agents`/`ddp-sync` are wired to read this manifest directly (OPEN-328/OPEN-329 track
that, repo by repo).

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
  resolves per-jurisdiction opt-ins this way (`scrapebot_fallback`, under `secondary` until SYNC-152, and now
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

*Still true after OPEN-521 (2026-11-10, plan "One pipeline per state"):* **who** is enrolled is now the
manifest's (`jurisdictions.yaml` `status`: scraped unless `probing` or `paused`; `archive.enabled`: the archive
follows the scrape), and ddp-sync reads it instead of keeping its own list. **When** (nightly or weekly, day,
start time) stays the scheduler's: ddp-sync's `openstates_scrape.timing`, timing only, never membership. That is
why the manifest has no `tier` and no `archive.scheduled` any more, and why the drift check only checks that the
timing map names no state the manifest does not scrape.

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

**Still open after OPEN-219 (2026-08-31, see "Bill-version ordering & diff backfills" above)** —
that ticket consolidated the dispatch from two duplicated inline copies into one shared
`apply_prediff_cleaning()` function, closing the divergence risk, but deliberately didn't do the
registry migration itself (its own scope was *where* this runs, not *how* it's expressed). OPEN-121
is still open, now against one call site instead of two — a smaller, not harder, version of the
same opportunistic migration.

**Still open after OPEN-462 (2026-10-30, see `jurisdictions.yaml`'s `quality.diff_cleaner` bullet
above)** — `check-jurisdiction-drift.py` now parses this exact if-chain shape (an AST walk of
`apply_prediff_cleaning()`) to enforce the manifest against it, which makes this chain a second
reason to update that checker in the same change if OPEN-121 ever lands: the extractor is
deliberately written to fail loudly (`SourceError`) on a dispatch shape it doesn't recognize
rather than silently produce an empty table, so a registry migration will surface there immediately
rather than being discovered later as an unenforced manifest.

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
the live rotation; the now-retired nightly runner used to carry an inline comment noting the same
requirement. So the convention below is a written-down version of what already works, not a proposal.

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

## `jurisdictions.yaml` — the jurisdiction manifest, v0 (repo root, OPEN-221, 2026-08-31)

An **eighth** mechanism, added after the six-mechanisms survey above — deliberately not folded
into it, because it isn't a replacement for any of the seven: it's a new, narrowly-scoped
per-jurisdiction manifest (name/status/scrape/archive/waf/quality/api_keys/onboarding
fields, schema in `ddp-infra/PLAN-push-button-onboarding.md` §4.1) consumed **only** by this
repo's own scripts (`activate.sh`, `run-scrape.sh`, `run-people-refresh.sh`, `start-os-api.sh`,
`quality_check.py`) and the onboarding probe below. `ddp-sync`/`ddp-broker-py`/`ddp-next`/votebot
deliberately stay on their own existing jurisdiction lists as documentation-of-record until a
later phase — **do not wire this file into another repo without checking §4.1 first**, that
scope line was deliberate, not an oversight.

- **`validate_jurisdictions.py`** — the checked-in schema validator (has its own test suite,
  `test_validate_jurisdictions.py`). Catches duplicate YAML keys explicitly — plain PyYAML
  silently lets a later duplicate key win, which would otherwise make a manifest entry disagree
  with itself with no error.
- **`jurisdiction-field.sh`** — the bash-3.2-safe read helper (this Mac's bash is frozen at
  3.2.57, see the discipline checklist below) other scripts and the probe read a field through,
  rather than each hand-rolling its own YAML parsing. Rejects a request for a block-shaped path
  (a whole sub-mapping, not a leaf value) with a real error instead of printing Python's `repr()`
  of the block. `test-jurisdiction-field.sh` runs the whole thing under real bash 3.2.57.
- **Failure mode, since OPEN-327: fail closed, loudly.** This section first said an unreadable
  manifest should make consuming scripts "keep their pre-manifest behavior"; once the hand-typed
  lists were deleted there is no such behavior to keep (and a stale copy is the drift this exists to
  stop), so each consumer now does the safe thing for its own job and says so: `activate.sh` leaves
  `ARCHIVE_ENABLED_STATES` **empty** with a stderr WARNING (archiving skips every jurisdiction with its
  normal "not enabled" message); `run-people-refresh.sh` and `run-scrape.sh` exit 1 with an ERROR (the
  scheduler's failure alert fires; a guessed list would refresh nobody, or fail a later import less
  clearly); `start-os-api.sh` skips its boot smoke test **with a Slack alert** rather than failing the
  boot (the stack is already up); `quality_check.py` stops with the validator's messages.
- **`jurisdiction_codes <dotted.bool.field>` (OPEN-327)** in `jurisdiction-field.sh`: prints the codes
  whose boolean field is true, comma-joined, in manifest order (`./jurisdiction-field.sh --codes
  archive.enabled`). The field must be a boolean on EVERY jurisdiction; a missing or non-boolean value is
  exit 4, never a silent skip. Use it instead of typing a list: `states=$(jurisdiction_codes
  enrollment.people_refresh) || exit 1`. Source it only after `OS_VENV` is set (activate.sh does) so
  PyYAML is available, and test `-r` before sourcing under `set -e` (bash 3.2).
- **No `tier`, no `archive.scheduled` (OPEN-521, 2026-11-10).** Both were removed with ddp-sync's "one pipeline per
  state" (SYNC-152/153): ddp-sync reads only `status` (scraped = not `probing`/`paused`) and `archive.enabled` (the
  archive runs after each of that state's scrapes, then LegBot, search refresh and embedding). Scrape timing is
  ddp-sync's `openstates_scrape.timing` (OPEN-124 above). `validate_jurisdictions.py` rejects either field as unknown
  and says it was removed (`REMOVED_FIELDS`); `new-jurisdiction` no longer writes them and `advance-jurisdiction live`
  sets only the status. **Do not add a scheduling field back to the manifest**: timing belongs to ddp-sync. The
  history below (OPEN-418) is kept for what it explains.
- **`archive.enabled` vs `archive.scheduled` (OPEN-418, 2026-10-22; superseded by OPEN-521).** Until then one flag, `archive.enabled`, was both
  the Stage 4 gate for a manual validation run and (once the drift check made it equal to ddp-sync's list) the
  recurring schedule, so a state could not be validated without being scheduled. Now `enabled` = may be archived
  (feeds `ARCHIVE_ENABLED_STATES`; the manual run), `scheduled` = on ddp-sync's recurring `openstates_archive` list
  and schedule (compared by the drift check). `validate_jurisdictions.py` enforces, in one place: `scheduled: true`
  requires `enabled: true` and a `status` of `live` or `paused`. A state mid-pilot is therefore `enabled: true,
  scheduled: false` until a human sets `live`. ddp-sync's dual-read and daily host check read `archive.scheduled`
  for the same list. (The api-v3 `/ddp/enrollment` route still serves `archive` = `archive.enabled`; nothing reads it.)
- **ddp-sync's per-state behaviour (SYNC-157, 2026-11-12).** Seven fields ddp-sync kept as per-state lists in its own
  `sync_schedule.yaml` live here, required on every entry, with the values ddp-sync had: `scrape.sweep_import` (va, mi, fl,
  ma), `scrape.full_walk` (mi; still off by ddp-sync's global switch), `scrape.retry` (ma; **the validator refuses `retry:
  true` for a state whose `waf.profile` is not `none`**, which replaces ddp-sync's `jurisdictions_excluded: [mi]`, OPEN-53),
  `scrape.cadence_escalation` (true everywhere), `scrape.fargate_max_wait_s` (ma 86400, else null = ddp-sync's shared 12 h),
  `waf.scrapebot_fallback` (mi; ddp-sync's scrape and archive both read it) and `enrollment.broker_bill_event_signal` (none).
  ddp-sync also reads `scrape.timeout_s` / `archive.timeout_s` here now (it deleted `SCRAPE_TIMEOUT_S` / `ARCHIVE_TIMEOUT_S`),
  and the `cloud_path`, `embedding`, `search_refresh` and `legbot_replica` enrollments with no copy of its own.
  `new-jurisdiction` writes the opt-ins false, `cadence_escalation: true` and a null wait. The drift check compares these
  with ddp-sync's old lists while ddp-sync main still has them and skips each once deleted. **Release order: this file
  first (on both hosts' checkouts), then ddp-sync**: a ddp-sync whose manifest lacks the fields treats every state as not
  enrolled (MI loses its ScrapeBot fallback, MA its retry and 24 h wait) and its daily drift check alerts "unverifiable".
- **No `actions` block (OPEN-544; was `actions.newest_first`, BROKER-368); no `voatz` block (BROKER-482, BROKER-494).**
  `actions.newest_first` said a state's stored bill actions were newest first. Every state now stores them oldest
  first, fixed in its scraper (la and ne OPEN-534/535, nc OPEN-543, us OPEN-542), so the label was false everywhere
  and is gone: the validator rejects an `actions` block with the reason (`REMOVED_FIELDS`), `new-jurisdiction` doesn't
  write one, the drift `--matrix` has no column for it, api-v3's `GET /ddp/enrollment` ignores a stray one, and the
  broker replays actions in stored order with no reversal. **A state found storing its actions newest first is fixed
  in its scraper (and its stored history reversed with OPEN-541's command, above), never labelled here.**
  Release order (OPEN-544): the broker first (it stops reading the field), then api-v3 and this file in either order.
  **Nothing Voatz is here** (Ramon,
  2026-11-13: "api-v3 should only be serving up the ddp-open-states data. it's the responsibility of the broker to bring
  together data from openstates, voatz, legbot, etc."): a state's Voatz test precinct (BROKER-494) and its private poll
  creator id (BROKER-482) live in its Voatz entry in AWS Secrets Manager, read by the broker through
  `common/voatz_credentials.py`. The validator rejects a `voatz` block (any content, even empty; `REMOVED_FIELDS` says
  why), `new-jurisdiction` doesn't write one, and a test fails if a 9-prefixed nine-digit id appears anywhere in
  `jurisdictions.yaml`. **Never add Voatz data to this repo or api-v3.** Release order (BROKER-494): the broker first
  (it stops reading `voatz` from api-v3), then this file and api-v3 in either order (api-v3 already serves an entry
  without a `voatz` block).
- **`enrollment:` block and `check-jurisdiction-drift.py` (OPEN-318, 2026-10-05).** The manifest now
  also records which per-feature lists each jurisdiction is on (`enrollment.people_refresh`,
  `search_refresh`, `embedding`, `cloud_path`, `api_smoke_test`, `qa_sweep`, alongside `archive.enabled`),
  seeded from the lists' real values, and **`check-jurisdiction-drift.py` compares every list
  it knows about to the manifest and fails on any disagreement**: `activate.sh`, `run-people-refresh.sh`,
  `start-os-api.sh`, `quality_check.py`, `run-scrape.sh` (derivation checked, see below), and (with `--ddp-sync-root`) ddp-sync's
  `sync_schedule.yaml` lists (embedding, search refresh, cloud path) and its `SCRAPE_TIMEOUT_S` / `ARCHIVE_TIMEOUT_S` tables.
  **Since OPEN-521 there is no scrape or archive list to compare**: ddp-sync derives both from the manifest (`status` not
  `probing`/`paused`, `UNSCHEDULED_STATUSES`, the same rule as its `jurisdiction_enrollment.py`; and `archive.enabled`). What is
  left is `openstates_scrape.timing`, which must name only states the manifest scrapes (a timing entry for a paused,
  probing or unknown state is drift); a ddp-sync with no `timing` map is an error (exit 2), not a pass. Run in CI against
  ddp-sync's `main`. A source it cannot parse is an error (exit 2), never a pass. `--matrix` prints
  who is enrolled in what. **OPEN-331 (2026-10-21) resolved the gaps it first showed:** NC now refreshes its people, is in the boot smoke test and the QA sweep (it had been missing from all three because the hand-kept lists predated it); MA joined the smoke test. What is still off is **deliberate and written beside the flag in `jurisdictions.yaml`**: NC `embedding` (waits for its knowledge-base backfill), MA `search_refresh` and `embedding` (MA is not routed to the replica yet, BROKER-16), and AL's search, embedding, cloud path and smoke test (paused).
  For this repo's own scripts that is no longer a comparison (OPEN-327): `activate.sh`,
  `run-people-refresh.sh`, `start-os-api.sh`, `run-scrape.sh` and `quality_check.py` **derive** their lists
  from the manifest, and the drift check's job for them is to fail (exit 2) if one stops deriving or grows a
  hand-typed list again. The old retired nightly runner that used to carry its own stale, hand-typed
  lists was deleted outright instead (OPEN-465), rather than converted. The "do not wire this file into another repo" rule above still stands for
  other repos' consumers: ddp-sync's own lists stay where they are until the dual-read migration the plan's
  §4.1 requires (OPEN-328). Written by hitting two real
  stale manifest values on its first run (`ma` allow_duplicates, MI's archive timeout), which the
  hand-written spot checks in `test_validate_jurisdictions.py` had pinned wrong. **OPEN-330** added the two
  env-var lists (`enrollment.replica_routing` = `DDP_OPENSTATES_JURISDICTIONS`, `enrollment.legbot_replica` =
  `LEGBOT_RDS_REPLICA_JURISDICTION_ALLOWLIST`) and `--live LABEL:NAME=a,b,c`, which compares a value read from a
  host's real environment with the manifest (the caller reads it; nothing here can see another host's `.env`).
  `replica_routing` is a rollout state, not a `status` question: MA is `live` but not routed (BROKER-16). **Not yet covered** (each a
  follow-up under OPEN-318): ddp-sync's in-code fallbacks and manual-trigger allow-list (SYNC-57), the
  `DDP_OPENSTATES_JURISDICTIONS` / `LEGBOT_RDS_REPLICA_JURISDICTION_ALLOWLIST` env values, ddp-broker-py,
  votebot, ddp-agents, and the per-feature opt-in lists (`sweep_import`, `scrape_retry`, `full_walk`).
- **`quality.diff_cleaner` (OPEN-462, 2026-10-30).** Names the jurisdiction-specific function
  `openstates-core/openstates/cli/text_extract.py`'s `apply_prediff_cleaning()` selects for that
  jurisdiction before diffing a bill version against its predecessor (never the stored `raw_text`) —
  the function's own name with its leading underscore removed (`_clean_nc_text` -> `clean_nc_text`).
  `none` means no `if jurisdiction_name == "..."` branch exists for it in that dispatch, not merely
  "untried" — FL's own `none` is a verified side effect of its extractor, not a gap (see FL's own
  comment in `jurisdictions.yaml`). Found stale for MA, NC and AL (manifest said `none`, the code
  already cleaned all three) and corrected as part of OPEN-462, which also taught
  `check-jurisdiction-drift.py --openstates-core-root <path>` (`OPENSTATES_CORE_ROOT`,
  `--require-openstates-core` — same optional-then-required pattern as `--ddp-sync-root`) to parse
  that dispatch directly, an AST walk of `apply_prediff_cleaning()` rather than a second hand-kept
  table, and fail when a manifest value disagrees with it in either direction. CI's `validate` job
  now checks out `openstates-core` and passes `--require-openstates-core`, same as it already does
  for `ddp-sync`. **Coupled to the current if-chain shape on purpose** (see "Per-jurisdiction
  configuration" -> OPEN-121 below): if that dispatch is ever migrated to a registry, this
  extractor needs updating in the same change, not quietly left to pass by checking nothing. **Not
  yet extended** to the procedural-document stage table in `utils/version_ordering.py` (also keyed
  on the jurisdiction's display name, with a second copy in api-v3) — survey row B6, a related but
  separate gap, left for a follow-up decision rather than folded in here.
  **Nebraska (OPEN-486, 2026-11-04):** `clean_ne_text` (header lines dropped, one sentence per line);
  its amendment papers (`AM<N>`, `FA<N>`, `ER<N>`) are excluded in that same procedural-document table
  (a separate openstates-core change). The cleaner has to be in openstates-core's `main` before this
  value can pass the drift check.

## `verify-jurisdiction <state>` — the onboarding probe (repo root, OPEN-222, 2026-08-31)

Read-only diagnostic answering "what will onboarding this state actually cost?" in ~30 minutes,
before anyone commits to it. Reads and writes an entry in `jurisdictions.yaml` above per its
schema. Runs nine gates, six of them (A/B/C/D/H/I) **blocking** and three (E/F/G) **advisory-only**
— an advisory gate can never turn a green verdict red, only add a note:

- **A** session list check, **B** scraper module shape (votes scraper? `start=` supported?
  required API keys present, per the credentials table above?), **C** `CONVERSION_FUNCTIONS`
  coverage for every upstream `media_type`, **D** a bounded, timed dry scrape with a
  nonzero-objects assertion, **H** `BillVersionLink` rows actually exist (not a stale snapshot)
  — all blocking. With `--import`, H first refuses a state with no people loaded (OPEN-446), then
  writes the jurisdiction/session objects and imports the sample, and lists the state's
  `LegislativeSession` rows afterwards (OPEN-456). **I** (OPEN-456, blocking) dry-scrapes up to two
  other active sessions and fails when a vote `dedupe_key` repeats across sessions or bills (the
  OPEN-397 collision; a bounded sample, so a pass means none repeated in it).
  **Trap fixed in OPEN-456:** `os-update --datadir X` sets the *base* directory and its import reads
  `X/<module>`, so the probe's `--import` had been reading an empty directory and loading nothing;
  `stage_import_dir()` now lays the files out where `os-update` looks. Reuse it, do not pass a
  scrape directory straight to `--datadir`.
- **E** `motion_classification.yaml` coverage, **F** version-walk direction, **G** people
  data/broker fixture shape — all advisory.

**Probing many states at once (OPEN-460).** `probe-on-fargate <state> ...` (or `--all`: every jurisdiction with a bills
scraper, not Michigan) launches one `verify-jurisdiction --fargate` task per state in waves, records the task ids in
`launched.json`, and `--status` reads the exit codes back. Reuse it; do not assemble `aws ecs run-task` by hand for a
batch. It only launches and describes tasks (the scraper login cannot read the probe logs or the bucket); the prod
agent reads the reports. It refuses Michigan and a `prod` memory prefix, and passes the OPEN-459 limits, so it needs
an image built after OPEN-459 (an older one stops with exit 2, "unknown option").

**One crashing gate never means no report (OPEN-470).** `main()` runs every gate through `guarded()`: if a gate
raises (Vermont's scraper returns a generator, California's needs a MySQL driver), that gate is reported as failed
with the error and the report and `result.json` are still written. Do not call a `run_gate_*` bare in `main()`.

**Gate J and state ids (OPEN-472).** Gate J (advisory, the Mac half: do the sampled votes' voters resolve to people)
reports `skip` when no session was found for the state, instead of crashing on a `None` in its session list (Illinois,
Indiana, New York and the Virgin Islands crashed it before). `qa_primitives.ocd_jurisdiction_id()` is the one place that
turns a state code into a jurisdiction id; it maps `dc` to `district:dc` and `as`, `gu`, `mp`, `pr`, `vi` to
`territory:<code>`, so the people check counts them. Do not build an id with `state:` + code anywhere else.

**What the image must carry for a scraper to run (OPEN-471).** New Mexico's scraper calls `mdb-export`, so the runtime
stage of the `Dockerfile` installs `mdbtools` (a guard test reads the `apt-get install` lines). California's needs a
MySQL driver and a loaded `capublic` database the cloud task does not have; Ramon left it out of the probe (2026-10-31).

**Two places to run it (OPEN-458).** `verify-jurisdiction <st> --fargate` runs as a task in the same
`ddp-scrapers` definition the scrapes use (`RUNNER_SCRIPT=verify-jurisdiction`; the file is in the Dockerfile's
`COPY` line), so a state's website sees a cloud IP, not the Mac's. There it has no database: G and H are skipped
(a RED is final, a YELLOW provisional), `--import`, Michigan and a `prod` `MEMORY_PREFIX` are refused
(`fargate_refusal()`; it also removes `DATABASE_URL` from the environment), and `report.md`, the bounded sample and, last,
`result.json` (with a hash of every sample file, `sample_manifest()`) are uploaded under
`<MEMORY_PREFIX>/probe/<state>/<run id>/` (`upload_probe_output()`). `verify-jurisdiction <st> --from-dir <folder>`
finishes that run on the Mac: gates A, B and D are read from `result.json` (refused unless the folder's sample
matches the hashes in it), the others run against the downloaded sample (`run_gate_i_from_dir()` and the live gate share `compare_vote_keys()`). The cap lives in the probe
(`--sample-bills`): **do not add a `limit` parameter to `cloud_collector.py` for probes**, and do not write a second
uploader or a second vote-key verdict. See RUNBOOK.md "Running the onboarding probe on Fargate".

**The sample limit counts bills (OPEN-459).** `--sample-bills N` stops the dry scrape after N *bills*, each with its
vote events; `--max-objects M` (default 300) is a separate cap on everything the scraper returns. The cap bounds what
is **pulled** from the scraper, not only what is kept, because every vote event is a request to the state's website:
the scraper is never asked for more than M objects plus one. Scrapers yield a bill's votes first and the bill last
(`yield from self.scrape_votes(bill); yield bill`), so `cap_scrape_output()` holds objects until their bill arrives
and passes them on together: a bill's votes are never kept without the bill. When the cap is reached the group being
held is dropped; a bill whose votes alone pass the cap is not sampled, and gate D then **warns** (yellow, not red)
and says to raise `--max-objects`. A scraper that yields votes after their bill or apart from it loses them (Florida's
come after all its bills, so its sample has none). Gate D's details say how many bills and votes the sample held and
what stopped it. **Do not put `itertools.islice` on a scraper's output again:** it counts objects, and Colorado's
"20" was 1 bill and 19 votes (2026-10-30).

Output is a scored green/yellow/red report, checked into `notes/` (e.g.
`notes/fl-onboarding-probe-20260831.md`). **A real bug caught in review, worth knowing if you
touch this script:** the scoring originally could report GREEN when a blocking gate had only
warned or been skipped, not actually confirmed passing — fixed so GREEN requires every blocking
gate to have genuinely passed. Calibrated by running it against an already-onboarded, healthy
state (FL) and confirming GREEN — proving the gates recognize a healthy state correctly, not just
that they can reject a broken one, which is the easier half to get right by accident.

## `deploy/sync-manifest.sh` — keep api-v3's copy of the state list current after a pull (OPEN-483)

`GET /ddp/enrollment` (api-v3) serves the shared state list and re-reads it when the file's modification time changes
(`api/ddp_enrollment.py`). It could not see a `git pull`: the old single-file bind mount keeps the file's OLD inode when git
replaces it (proven with a real container on native Linux Docker, 2026-11-03), so every pull needed an api recreate. Both
compose files now mount **only the directory `deploy/manifest/`** (never the checkout: it holds `.env` files) and set
`DDP_JURISDICTIONS_MANIFEST=/app/manifest/jurisdictions.yaml`; `bash deploy/sync-manifest.sh` copies `../jurisdictions.yaml`
into it atomically (temp file, rename, source's modification time kept; an empty or missing source leaves the copy alone).
`--check` changes nothing and exits 1 when the copy differs. Do not add a second way to hand the file to the container, and
do not go back to a single-file mount. One recreate switches a running container to the new mount (RUNBOOK.md).
**It validates the list first** (`validate_jurisdictions.py`, next to it in the repo) and copies nothing the validator rejects, leaving the existing copy serving, so a boot or a refresh after a pull whose validation failed cannot serve an unvalidated list (OPEN-488; it validates a snapshot and installs that same snapshot; a validator that cannot run, e.g. PyYAML missing for the host's `python3` when there is no `.venv`, is reported as the host's Python, not as a bad list, and also copies nothing; `--check` only compares; no switch turns the validation off, `MANIFEST_PYTHON` only picks the interpreter). `start-os-api.sh` (boot) and `refresh-api-v3.sh` call it before any `docker-compose` call and stop when it fails (tests: `test_api_boot_scripts_sync_manifest.py`). api-v3's loader behaviour it relies on (re-read by modification time alone) is pinned in api-v3's `api/tests/test_ddp_enrollment.py`.

## `deploy/rollout-manifest.sh --host mac|ec2 --ddp-sync-root PATH` — one command to roll a merged state-list change out on a host (OPEN-483)

Replaces the hand steps every state needed on each host (each of them its own request note to the prod agent in pilot #2):
gates, pull, record the revision, validate, drift check, refresh api-v3's copy, read the values back. It stops at the first
failed gate or check and prints a value for every step; `--dry-run` changes nothing in the checkout, the copy or any container
(it still runs `git fetch`, which moves only `origin/main`, and it validates the INCOMING file read from `origin/main`
**with the INCOMING validator and drift check**: it unpacks `origin/main` into a temp folder and runs them from there, then
removes it. So a merge that changes the list and its validator together, such as OPEN-521 or BROKER-494, passes the dry run the
way it passes the real one, which pulls first; until OPEN-532 the dry run judged it with the old validator and stopped, and the
rollout had to be finished by hand with "pull first, then the script" on 11-10, 11-13 and 11-14).
- **Gates:** the branch is `main` and no tracked file is modified; **no commit that is not on `origin/main`**; **no real
  `run-scrape.sh`, `run-scrape-retrying.sh`, `run-archive.sh` or `run-people-refresh.sh` process** (all of them read this
  checkout, and `run-scrape-retrying.sh` stays alive while it sleeps up to 900 s between attempts with no `run-scrape.sh` running;
  the listing is parsed by field: the job itself, a shell whose first non-option argument is the job (`bash -o pipefail run-scrape.sh`), or a
  known wrapper (`nohup`, `caffeinate`, `time`, `sudo`, `env`, `nice`, `ionice`, `timeout`, `setsid`, `stdbuf`, `arch`, `doas`) whose command (after its options and their values, e.g. `sudo -u git`) is the job or a shell on it counts (OPEN-488); a shell that only contains the text (`bash -c`), a grep, an editor or an echo (also behind a wrapper) or this script never counts; a plain
  `ps | grep run-scrape` matched its own shell on 2026-11-03; tests: `test_rollout_manifest.py`); no cloud scrape tasks (`aws ecs list-tasks`; if it cannot be listed
  the gate stops unless you say `--skip-ecs-check`); not within 10 minutes of the 02:00, 02:30 and 03:00 UTC jobs.
- **Order, so a bad list is never served:** fast-forward pull (`--ff-only`, never a merge or a reset) -> `validate_jurisdictions.py`
  and the combined drift check on the pulled file -> only then `deploy/sync-manifest.sh` (the copy api-v3 reads) -> the api
  container. **A failed check after the pull leaves the pulled checkout in place but api-v3's copy unchanged** (it keeps
  serving the previous list); fix the list on `main`, pull again, rerun.
- **Container:** a bounded wait for `healthy` (it fails the run if not), the container's checksum of `/app/manifest/jurisdictions.yaml`
  must be non-empty and equal the checkout's, then the list's states by status (`--state XX` adds that state's flags).
- **`--ddp-sync-root` is required for a real run** (a repo-only check is not the combined check); a dry run without it prints
  the check as UNCHECKED.
- **Never:** restarts anything, touches ddp-sync, the broker, the database container or any `.env`. The only docker command it can
  run is `up -d --no-build --no-deps --force-recreate api`, and only with `--recreate` (the one-time switch from the old single-file
  mount; exit code 3 until then). ddp-sync is restarted only on a person's word, when the drift check says its own lists changed.
- Do not add a second hand-run copy of these steps to a request note; run this and paste its output.

## `new-jurisdiction <state> --from-probe <result.json-or-folder>` — the manifest entry from a probe result (repo root, OPEN-461)

Stage 0 of the onboarding plan ends with "manifest entry with `status: probing`", which was always
hand-typed — OPEN-318 made `jurisdictions.yaml` the one place a state is declared, so that entry was
the one hand edit left at the start of every onboarding. This generates it instead, from the
probe's own `result.json` (the Fargate run's upload, or a `--from-dir` finish — see "the onboarding
probe" above and RUNBOOK.md "Running the onboarding probe on Fargate"):

```
new-jurisdiction co --from-probe notes/probe-co-20261030/        # a folder (reads result.json inside it)
new-jurisdiction co --from-probe notes/probe-co-20261030/result.json --dry-run   # or the file directly
```

- **What it writes:** `status: probing`, every `enrollment.*` field `false` (enrolling a state
  anywhere stays a deliberate, later, gated step — §5.1, out of scope here), `scrape.votes_scraper` /
  `scrape.start_filter` / `api_keys` parsed from probe gate B's recorded facts, and the platform's
  documented no-override timeouts (`scrape.timeout_s` 21600, `archive.timeout_s` 14400 —
  `check-jurisdiction-drift.py`'s required default for a code with no ddp-sync-specific entry).
  **Never** inferred from gate D's dry-scrape wall-clock/per-bill latency, which measures something
  else entirely (an open question for a future, explicitly-named measured-timeout probe field).
- **Never guesses `waf.profile` or `quality.diff_cleaner`** — these are always written as
  safe placeholders (`none` / `none`) and printed as needing a human, exactly because
  a probe-derived guess here is the mistake the diff_cleaner survey already found wrong for MA, NC
  and AL. Fill them in by hand after reviewing the probe's own report. (It wrote a `tier: secondary`
  placeholder too until OPEN-521 removed the field; there is no scheduling decision to make in the manifest.)
- **Fails closed on gate B:** verify-jurisdiction's gate B has no structured output, only fixed
  detail strings (`"votes scraper registered: ..."`, `"bills scraper accepts start=: ..."`,
  `"credential env-var references found in source: ..."` / `"no credential env-var references
  found..."`). Missing or unrecognized wording refuses to write rather than guessing.
- **Validated before any write:** the full candidate manifest (existing text plus the new block) is
  parsed and run through `validate_jurisdictions.py`'s own `validate()` — a rejected candidate
  leaves `jurisdictions.yaml` byte-for-byte unchanged.
- **Append-only, never a full YAML load+dump:** a round-trip through PyYAML's dumper would strip or
  reflow every hand-written comment in the file (see the file's own header). This only ever appends
  text for a brand-new state, so it can never touch another state's bytes.
- **Idempotent, never a silent overwrite:** an already-present state that matches is a no-op; one
  that differs (including a human's own edit to `quality.diff_cleaner`/`waf.profile`) prints
  the exact field-level differences and still writes nothing.
- Does **not** enroll a jurisdiction anywhere, touch ddp-sync, or run any gate itself — it only
  reads a probe's already-produced `result.json`. Wired into
  `.github/workflows/validate-jurisdictions.yml` alongside the validator and drift check.

## `advance-jurisdiction <state> <scraping|live>` — move a state forward and set the flags that status needs (repo root, 2026-11-03)

Pilot #2's first scrapes loaded with 0 legislators because `enrollment.people_refresh` was still false when the
state went to `scraping`: the rule was in the runbook, nobody owned it, and the manifest let the state advance
without it. Two pieces make that impossible now:

- **`validate_jurisdictions.py` refuses** a state at `scraping`, `validating`, `archived` or `live` whose
  `enrollment.people_refresh` or `archive.enabled` is false. (A `live` state also needed `archive.scheduled` until
  OPEN-521 removed it: the archive now follows every scrape.)
  `probing` and `paused` are exempt. It runs in CI (`.github/workflows/validate-jurisdictions.yml`), so the miss is caught
  in review instead of three days later.
- **`advance-jurisdiction`** sets them, in one step: `scraping` (from `probing`) sets `status`, `people_refresh`,
  `archive.enabled` and `enrollment.cloud_path` (left alone with a warning when `waf.fargate_safe` is false); `live`
  (from `scraping`, `validating`, `archived` or `paused`) sets the status and the same flags (nothing more since OPEN-521). `--dry-run` prints the
  lines it would change.
- **Never touches** `legbot_replica`, `embedding`, `replica_routing`, `search_refresh`, `qa_sweep`,
  `api_smoke_test`, `waf` or `quality.diff_cleaner`. LegBot stays the one switch a human flips (Ramon, 2026-11-03: it
  depends on the data being good); embedding and routing stay behind their own gates (backfill, parity check).
- Same safety shape as `new-jurisdiction`: line-for-line edits of one state's block (comments and every other state's bytes
  survive), the result is validated before anything is written, and a re-run changes nothing. It does **not** edit ddp-sync's
  yaml lists or any host; those are separate rows of the 2026-11-03 friction audit (OPEN-328, SYNC-142).
- Do not hand-edit those flags in a status flip any more; run this and commit the diff.

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
- **A scraper's `VoteEvent.dedupe_key` must be unique across every session AND every bill within its jurisdiction (OPEN-252, OPEN-397)** —
  as `openstates-core` stands today, the vote importer (`vote_events.py`, `get_object()`) matches a vote that has a
  `dedupe_key` on that key alone (plus jurisdiction), ignoring session and bill. A key that repeats raises
  `DuplicateItemError` and fails the whole load: MA (one roll call cited by two bills; `VoteEvent.bill` is a single
  foreign key, so the intended model is one row per roll call per bill, and the fix adds the bill to the key) and NC
  (roll-call numbers restart every session, so the `2025E1` extra session collided with `2025`; the fix adds the
  session). Build the key from a URL or a stable source-system vote ID, unique across sessions, plus the bill if one roll call can cover
  several. Or set no key (FL, MI, UT, WA, US): the importer then matches on session + bill + the vote's `identifier`,
  or, with no identifier, on motion text + start date + organization, so that is only safe where those are stable and
  unambiguous. **Do not reach for `--allow_duplicates`:** it logs the duplicate and then updates the existing row
  with the new vote's fields, so the second vote silently overwrites the first. Keep the keys of votes already stored
  unless you are doing a deliberate migration (their identities and anything pointing at them change): qualify only
  new sessions, as `vote_dedupe_key()` in `scrapers/nc/bills.py` does.
- **`test-*.sh` shell tests** — `bash test-<thing>.sh`, no framework, no network, no database, no
  production paths: a `mktemp -d` per run, fixtures written as text files, `ALL PASS (N
  assertions)` and exit 0 or the first failing assertion and exit 1. Seven of these now exist
  (`test-import-summary.sh`, `test-scrape-outcome.sh`,
  `test-no-op-side-effects.sh`, `test-scrape-lock.sh`, `test-completion-record.sh`,
  `test-scraper-memory.sh`, `test-replica-monitoring.sh`) and they all share that shape — copy the nearest one rather than
  introducing a runner. Four of them drive
  **`run-scrape.sh` itself** against a stub `os-update`, which is the only way to assert what the
  script *does* with a decision rather than just what a matcher returns.
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
4. **Failure alerting?** If it needs a Slack alert, source `lib/slack-alert.sh` (with the readable-check guard the
   other scripts use) and call `post_slack_alert "text"`. Don't write another `curl` to `chat.postMessage`: it
   would post as Agent Smith instead of CodeBot, and `test-slack-alert.sh` fails on it.
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
