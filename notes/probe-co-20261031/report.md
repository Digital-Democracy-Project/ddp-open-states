# Onboarding Probe — co (Colorado)

**Classification:** YELLOW
**Run at:** 2026-10-31T18:00:44.730239+00:00  |  **Wall clock:** 327.8s

PLAN-push-button-onboarding.md §4.4 / §5 Stage 0 -- OPEN-222. Read-only: no production database writes, no scraper code changes, no tickets filed. See the script's own docstring for exactly what each gate checks and the judgment calls made where the plan's prose left a gap.

Ran on Fargate: the people and database gates (G, H) were not run, so H shows SKIP. A RED here is final; a YELLOW is provisional. Finish on the Mac: download this run's folder (`probe/co/probe-co-20261031-v40/`), un-tar `sample.tar.gz` inside it, then run `verify-jurisdiction co --from-dir <that folder>`.

## Gate summary

| Gate | Blocking? | Status | Summary |
|---|---|---|---|
| A | yes | PASS | 16 scraped session(s), 1 active |
| B | yes | PASS | module shape recorded |
| C | yes | FAIL | 1 media_type(s) with no CONVERSION_FUNCTIONS['co'] entry: text/html |
| D | yes | PASS | dry scrape OK: 10 bill(s) in 326.4s |
| E | no | WARN | no motion_classification.yaml block for 'co' yet |
| F | no | PASS | walk direction (informational only, NOT written to the manifest per OPEN-34's 2026-08-07 correction): backward (10 classifiable multi-version bill(s) in this dry scrape's sample) |
| G | no | SKIP | not run on Fargate: it needs the people checkout and the dev database |
| H | yes | SKIP | no database on Fargate -- finish with --from-dir on the Mac |
| I | yes | PASS | only one active session, so there is no other session to collide with |
| J | no | SKIP | no database on Fargate -- finish with --from-dir on the Mac |

## Details

### Gate A

**PASS** (blocking) — 16 scraped session(s), 1 active
- active: 2026A

### Gate B

**PASS** (blocking) — module shape recorded
- votes scraper registered: False
- bills scraper accepts start=: False
- WAF resilience profile: none
- no module-level RPM override found (CO_SCRAPELIB_RPM not set) -- platform default applies
- no credential env-var references found in scraper source

### Gate C

**FAIL** (blocking) — 1 media_type(s) with no CONVERSION_FUNCTIONS['co'] entry: text/html

### Gate D

**PASS** (blocking) — dry scrape OK: 10 bill(s) in 326.4s
- wall clock: 326.4s
- objects written: 10
- sample: 10 bill(s) and 153 vote event(s) (163 objects); stopped by: bill limit (limits: 10 bills, 200 objects)
- avg per-bill latency: 32.64s

### Gate E

**WARN** (advisory) — no motion_classification.yaml block for 'co' yet

### Gate F

**PASS** (advisory) — walk direction (informational only, NOT written to the manifest per OPEN-34's 2026-08-07 correction): backward (10 classifiable multi-version bill(s) in this dry scrape's sample)

### Gate G

**SKIP** (advisory) — not run on Fargate: it needs the people checkout and the dev database

### Gate H

**SKIP** (blocking) — no database on Fargate -- finish with --from-dir on the Mac

### Gate I

**PASS** (blocking) — only one active session, so there is no other session to collide with
- probed session 2026A: 153 vote event file(s)

### Gate J

**SKIP** (advisory) — no database on Fargate -- finish with --from-dir on the Mac

## Recommendation

Needs scoped code work before progressing: blocking gate(s) ['C'], advisory gate(s) needing attention: ['E']. File templated tickets per RUNBOOK.md §5 Stage 1, copying the AC structure from the matching solved OPEN ticket named in each gate's detail above.
