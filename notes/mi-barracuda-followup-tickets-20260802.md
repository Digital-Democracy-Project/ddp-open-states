# Michigan bot-detection: OPEN-18 merged, wider problem scoped into two follow-up tickets, 2026-08-02

## Context: continuing from the prior note

Builds on `notes/mi-barracuda-bot-detection-analysis-20260801.md` rather than replacing it —
that note ended with an open "what to watch at the next real test" question and one disclosed,
not-yet-closed gap (`events.py`'s two fetch sites not covered by OPEN-18's skip-and-continue
wrapper). This note records what happened since: OPEN-18 shipped, and the wider
reputation-based-blocking problem that note surfaced got scoped into two new tickets.

## OPEN-18 shipped and merged, 2026-08-02

CodeBot dispatched against OPEN-18 the same evening the prior note was written, and delivered
three PRs, all reviewed (diff-read, since none of these repos run CI) and merged same day:

- [openstates-core PR #8](https://github.com/Digital-Democracy-Project/openstates-core/pull/8) —
  `content_matches_fake_404_block()`, a narrow literal-string marker check
  (`"the specified url cannot be found"`, case-insensitive, first 2KB only), kept separate from
  the existing 200-status `content_matches_block_markers()` since it's only meaningful to check
  from inside a 404/HTTPError handler.
- [openstates-scrapers PR #17](https://github.com/Digital-Democracy-Project/openstates-scrapers/pull/17) —
  wires it into `MIBillScraper`: `mi_waf_get()`'s `do_request` now catches `scrapelib.HTTPError`,
  raises `WafBlockDetected` on a match (feeding the existing cookie-invalidate-and-retry-once
  path), and re-raises unchanged otherwise — a genuine dead link still crashes exactly as
  before. `scrape_bill()` catches a block that survives the retry, skips just that bill, and
  aborts with `ScrapeError` after `MAX_CONSECUTIVE_WAF_BLOCKS=3` consecutive detections.
- [ddp-open-states PR #49](https://github.com/Digital-Democracy-Project/ddp-open-states/pull/49) —
  RUNBOOK.md documentation, including an explicit disclosure that `events.py`'s two fetch sites
  get the improved block-detection (centralized in the shared `mi_waf_get()`) but **not** the
  skip-and-continue/circuit-breaker wrapper — a real, known, still-open gap.

Also merged the same day: [openstates-core PR #7](https://github.com/Digital-Democracy-Project/openstates-core/pull/7)
(the reputation-blocking docstring update flagged as "not yet merged" in the prior note) —
merged 2026-08-02T16:28:29Z, docs-only, no behavior change.

## Scoping the wider problem: two new tickets, not one

The prior note's real finding — cookies are necessary but not sufficient; Barracuda tracks
something beyond the two `x-bni-*` cookies (most likely IP reputation and/or
request-volume/rate history) that can override cookie-based validation entirely once tripped —
isn't something OPEN-18 or OPEN-19 touches. Scoping a fix for that considered five candidate
levers (rate-limiting/pacing, cross-run adaptive backoff, halting ad-hoc manual testing against
production, researching an alternate non-WAF data source, IP/egress rotation via proxies) and
deliberately narrowed to the first two for now. The alternate-data-source research and IP
rotation were set aside — the latter specifically flagged as crossing from "well-behaved
client" into "actively evading a state government site's bot protection," worth an explicit
decision on its own rather than defaulting into it.

- [OPEN-21](https://digitaldemocracyproject.atlassian.net/browse/OPEN-21) — give MI its own
  conservative `requests_per_minute` (below the platform-wide default of 60 every jurisdiction
  currently shares via `settings.SCRAPELIB_RPM`) and opt `MIBillScraper`/`MIEventScraper` into
  `http_resilience_mode` — an existing, richer resilience wrapper already built into
  `openstates/scrape/base.py` (jittered delay, circuit breaker, UA rotation, connection-pool
  reset) that, as far as this investigation found, no scraper in the codebase currently uses.
  Requires a live check that it doesn't interfere with `mi_waf_get()`'s own retry-once dance.
- [OPEN-22](https://digitaldemocracyproject.atlassian.net/browse/OPEN-22) — `ddp-sync`'s
  `run_secondary_scrapes_job` (`src/ddp_sync/pipelines/openstates_scrape.py`) already alerts
  per-run (Slack `#automation-errors` + CAMS's `/api/v1/failures`) and persists per-run history
  to Redis (the `openstates_secondary_scrapes` flow-status key) — but nothing reads that history
  back, so a first-time block and a month of consecutive blocks look identical today. Scoped to
  detecting and escalating the *sustained* pattern using that existing history, explicitly not
  to auto-skipping scheduled runs (unproven value, and skipping means less data on whether the
  block has actually cleared).

Neither ticket is assigned yet.

## What to watch next

- ~~Whether the 2026-08-02 02:00 UTC `openstates_secondary_scrapes` run... came back clean~~ —
  **answered below: it did not.**
- Whether OPEN-21/OPEN-22 get assigned, and if so, whether OPEN-21's required live-interaction
  check between `http_resilience_mode` and `mi_waf_get()` turns up anything — **OPEN-21
  answered below; OPEN-22 still open, unassigned.**
- The still-open `events.py` gap disclosed in the OPEN-18 RUNBOOK entry (PR #49) — no ticket
  filed for it yet as of this note. Still true as of this update.

## Update, later 2026-08-02: the 02:00 UTC run failed; OPEN-21 shipped and live-verified; the
## reputation block itself is still fully open (OPEN-22)

The 2026-08-02 02:00 UTC `openstates_secondary_scrapes` run did **not** come back clean: MI
failed with `returncode=1` in 17.5s (`ddp-sync` log), before OPEN-21's fix had landed. Two manual
retrigger attempts the same day (12:56, 15:00 EDT) also failed the same way.

OPEN-21 was then dispatched to CodeBot and shipped same day as three PRs — openstates-core #9
(adds an opt-in `_resilience_retry_excluded_exceptions` attribute to `Scraper.retry_on_connection_error`,
empty by default so no other jurisdiction's behavior changes), openstates-scrapers #18 (adds
`MIResilientScraperMixin`: forces `http_resilience_mode=True`, lowers `requests_per_minute` to an
env-tunable `MI_SCRAPELIB_RPM` — default 10, versus the platform default of 60 — and sets the new
exclusion tuple to `(scrapelib.HTTPError, requests.exceptions.ConnectionError)` so `mi_waf_get()`'s
own invalidate-and-retry-once dance stays the only retry layer for WAF failures), and
ddp-open-states #51 (RUNBOOK.md write-up). All three reviewed by diff-read plus independently
re-running each PR's test suite (checking out each branch for real, not trusting the self-reported
"tests pass") before merging, then fast-forwarded into the production checkout via
`apply-local-patches.sh` (core, scrapers) and a plain `git pull --ff-only` (outer repo) the same
day — no scrape was running at the time.

**Live-verified the same evening** via a manual `./run-scrape.sh mi` run (bypassing ddp-sync's
HTTP trigger, so no API key needed) against the real, current `legislature.mi.gov`. Result,
read from the actual traceback in `logs/scraper.log`:

- The retry-stacking fix works exactly as designed: exactly 2 physical HTTP attempts per
  top-level scrape try (one initial cookie warm-up + one `mi_waf_get()` rewarm-retry), ~2-3s
  apart — no 10s/20s/40s exponential backoff stacking from the resilience layer's own retry
  loop. `WafBlockDetected` propagated immediately through `mi_waf_get()` once the rewarm also
  got blocked, instead of being caught and retried again by `retry_on_connection_error`.
- MI is still fully blocked regardless of fresh cookies: both the initial warm-up and the
  rewarm attempt hit the block within the same run. This is the *exact* sustained,
  reputation-based override this note's "Scoping the wider problem" section already described
  as out of OPEN-21's scope — OPEN-21 was about footprint/retry-stacking, never about defeating
  the block itself.
- No new CAMS-triaged failure ticket was filed from this run (checked `project = OPEN order by
  created desc` immediately after) — consistent with this being the same, already-tracked
  problem rather than a new bug.

**Net: OPEN-21 is done and verified correct. OPEN-22 (detect/escalate a sustained blocking
pattern) is still fully open** — MI won't scrape successfully again until that, or some other fix
for the underlying reputation block, ships. Still unassigned as of this update.
