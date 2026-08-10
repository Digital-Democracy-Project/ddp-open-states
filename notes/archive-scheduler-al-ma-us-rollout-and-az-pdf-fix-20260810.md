# Archive scheduler: AL/MA/US flipped on, weekly-per-jurisdiction scheduling, AZ's real PDF bug fixed

## Context

Started from a routine status check: `os status` (before tonight's own fixes to it) showed AL,
MA, and US had never been archived at all, while AZ sat stuck at ~40% archived despite its
nightly job running cleanly for 7+ straight days. Digging into "did we actually flip on
AL/US/AZ/MA completely, or just test it" surfaced two genuinely separate problems that both
needed fixing before AL/MA/US could be safely enabled.

## Problem 1: AL/MA/US were never wired into the archive scheduler at all

Not a partial rollout — confirmed via `activate.sh`'s `ARCHIVE_ENABLED_STATES`, `ddp-sync`'s
`openstates_archive.jurisdictions` config, and `logs/scraper.log` (zero archiving lines ever,
not even a "not enabled, skipping" line) that all three agreed: these jurisdictions were simply
absent from every config, everywhere.

Before enabling them, checked the two gating comments already in `activate.sh`:
- **MA** was held back because its local data was "the stale pre-fix snapshot from
  2026-06-16" until a fresh full re-scrape happened. Confirmed via prod's `scraper.log`: a
  `mode=full` scrape completed 2026-08-09 (`bills_scraped=9496`). Blocker cleared.
- **US** was held back pending "its own sizing pass" — see Problem 3 below for how that
  actually got resolved (not a dedicated timed measurement, but real backlog data making the
  actual constraint obvious).
- **AL** has no documented correctness gate, but it's also not in `ddp-sync`'s
  `active_jurisdictions` scrape rotation at all — enabling its archiver clears its one-time
  existing backlog, but it won't get new bills to archive going forward unless it's later
  added to scraping too. Flagged, not blocking.

## Problem 2: daily-all-jurisdictions-concurrently doesn't scale to federal

`us` alone has ~83k never-archived documents (2026-08-10) — two orders of magnitude more than
any state jurisdiction (all others sit at 98–99.99% already archived). The existing
`openstates_archive` job ran every enabled jurisdiction concurrently, every day
(`run_archive_jobs`). Adding `us` to that model would let its fetch+extract volume dominate
shared CPU/network/DDP-HOT I/O and starve the smaller jurisdictions' own runs — the same shape
of problem `PLAN-bill-document-provenance.md`'s compounding-slowdown incident was about, just a
different cause.

**Fix:** `ddp-sync`'s scheduler now registers one independent weekly APScheduler job per
jurisdiction (`run_single_archive_job`) instead of one daily batch job. `us` gets Sunday
entirely to itself; `fl`+`ut` and `wa`+`va` share a day since both pairs are already
near-fully-archived and do almost no work once caught up. `ARCHIVE_TIMEOUT_S["us"] = 24h` added
for its cold-backfill runs.

## Problem 3: AZ was NOT hit by bot detection — ruled out directly

Initial hypothesis (mine and Ramon's) was WAF/bot-detection, matching the MI/FL pattern
elsewhere in this project. **Directly ruled out:** every AZ archive run logged
`fetched=0 blocked=0 fetch_errors=0` — it never even attempted these fetches, let alone got
blocked. Fetched a never-archived AZ PDF by hand (plain `curl`, no cookies/headers): `HTTP/2
200`, a clean valid PDF, no CAPTCHA/challenge page.

**Actual root cause:** `openstates-core`'s `CONVERSION_FUNCTIONS["az"]["application/pdf"]` has
been unconditionally `DoNotDownload` since before this fork existed. Fine when a version also
has an HTML copy (3,583 versions do) — but found **~1,160 AZ versions, mostly
committee-amendment stages, that exist *only* as PDF**, with no HTML fallback. Those got
silently zero-archived, forever.

Fix: `application/pdf` now maps to `extract_sometimes_numbered_pdf` — verified clean against a
real downloaded fixture (`sb1717p.pdf`, an introduced-bill PDF with the same numbered-line
layout already handled for AL/FL/MA/MD). Some committee-stage PDFs are scanned/image-only (no
text layer at all — confirmed via `pdffonts`/`pdfimages`: no embedded font, tiny image objects)
and will now archive with `is_error=True` instead of being silently skipped. Per Ramon: download
both HTML and PDF always, rather than conditionally skipping PDF only when HTML exists — simpler,
and the natural-key skip check already makes re-archiving an already-covered version a cheap DB
check going forward, not wasted work.

## A staleness bug pattern recurred twice more, same night

Adding `ma`/`al`/`us` to one config (`openstates_archive.jurisdictions`) wasn't enough — two
*other* places had their own independent, hardcoded copies of the jurisdiction list that didn't
get the memo:

1. `ddp-sync`'s manual archive-trigger endpoint (`triggers.py`) had its own
   `_OPENSTATES_ARCHIVE_JURISDICTIONS` set, still `{fl, ut, az, wa, va, mi}` — would have
   404'd on `us` when manually kicking it off. Fixed by extracting a single
   `DEFAULT_ARCHIVE_JURISDICTIONS` constant and having the endpoint read from config instead of
   maintaining a second copy.
2. `os-status`'s jurisdiction-full-name display was about to get the exact same hardcoded-list
   treatment mid-implementation — caught and redirected (thanks, Ramon) to look the name up
   from `opencivicdata_jurisdiction.name` in Postgres instead, the actual source of truth DDP
   already maintains.

Both are now single-source-of-truth by construction, not just corrected for today's list.

## `os-status` also got more descriptive while in there

Prompted by feedback that "ARCHIVER us pid 29672" was too terse and it wasn't clear whether that
represented *everything* OpenStates-related running. Now: full job descriptions ("Bill-document
archiver — United States (us)"), and a new footer that pulls `ddp-sync`'s complete scheduled-job
roster (all 15 OpenStates-related jobs, next-run times included) live from its own `/schedule`
API — since this script only ever sees `os-update --scrape`/`os-text-extract archive` as real OS
processes; `bill_sync`, `legislator_sync`, `patch_refresh`, etc. run in-process inside `ddp-sync`
and never show up here no matter how "running" they are.

Caught a real bug while building this: the footer's first draft used a backslash-escaped quote
inside a Python f-string expression — a `SyntaxError` on this machine's Python 3.9 (only legal
from 3.12/PEP 701), silently swallowed by its own `2>/dev/null` until tested without it.

## Manual `us` backfill kicked off the same night

Rather than wait for the first scheduled Sunday run, ran `run-archive.sh us` directly on the
production checkout once nothing else was active (confirmed via `os status` and `ps`). Running
steadily afterward (~13–14 docs/min, 0 errors, confirmed via a live Postgres backlog count) —
disowned and reparented to `PPID=1`, so it survives this session ending, terminal closing, or
anything short of the machine itself going down. The scheduled Sunday run will continue from
wherever this one leaves off (natural-key skip check makes interleaving safe).

## Disposition

All 5 PRs merged and deployed live tonight:

- [`ddp-open-states`#106](https://github.com/Digital-Democracy-Project/ddp-open-states/pull/106) —
  `ma`/`al`/`us` added to `ARCHIVE_ENABLED_STATES`
- [`ddp-sync`#31](https://github.com/Digital-Democracy-Project/ddp-sync/pull/31) — weekly
  per-jurisdiction archive scheduling
- [`openstates-core`#14](https://github.com/Digital-Democracy-Project/openstates-core/pull/14) —
  AZ's real PDF-download bug fixed
- [`ddp-sync`#32](https://github.com/Digital-Democracy-Project/ddp-sync/pull/32) — trigger
  endpoint's stale jurisdiction set fixed
- [`ddp-open-states`#107](https://github.com/Digital-Democracy-Project/ddp-open-states/pull/107) —
  `os-status` descriptive output + full job roster

Deployment confirmed live, not just merged: prod checkouts pulled (`ddp-open-states`,
`openstates-core` via `apply-local-patches.sh`), `ddp-sync`'s LaunchDaemon kickstarted twice
(once per merged PR) and confirmed clean via `ddp-sync/logs/ddp-sync.log` — all 9
per-jurisdiction archive jobs registered independently, `us` alone on Sunday.

**Not done / worth a follow-up:** the `us` archiver's 24h timeout and current ~13-14/min rate
puts a full 83k-document backfill at many weeks, not one run — expect several more weekly (or
manually-kicked) runs before it's caught up. AL isn't in the scrape rotation, so its archived
set is a one-time snapshot, not a living pipeline, unless/until that's separately decided.

## Reference

* `activate.sh` — `ARCHIVE_ENABLED_STATES`
* `ddp-sync/config/sync_schedule.yaml` — `openstates_archive.schedule`
* `openstates-core/openstates/fulltext/__init__.py` — AZ's `CONVERSION_FUNCTIONS` entry
* `os-status` (repo root, synced to `~/.local/bin/os-status`)
* `ddp-infra/PLAN-bill-document-provenance.md`, Phase 1's "Resolved 2026-08-10" note — the
  fuller cross-repo narrative this note summarizes from `ddp-open-states`' side
