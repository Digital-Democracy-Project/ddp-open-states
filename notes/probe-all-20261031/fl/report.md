# Onboarding Probe — fl (Florida)

**Classification:** YELLOW
**Run at:** 2026-10-31T18:40:08.420002+00:00  |  **Wall clock:** 115.5s

PLAN-push-button-onboarding.md §4.4 / §5 Stage 0 -- OPEN-222. Read-only: no production database writes, no scraper code changes, no tickets filed. See the script's own docstring for exactly what each gate checks and the judgment calls made where the plan's prose left a gap.

Ran on Fargate: the people and database gates (G, H) were not run, so H shows SKIP. A RED here is final; a YELLOW is provisional. Finish on the Mac: download this run's folder (`probe/fl/probe-fl-20261031/`), un-tar `sample.tar.gz` inside it, then run `verify-jurisdiction fl --from-dir <that folder>`.

## Gate summary

| Gate | Blocking? | Status | Summary |
|---|---|---|---|
| A | yes | PASS | 85 scraped session(s), 1 active |
| B | yes | PASS | module shape recorded |
| C | yes | PASS | all 2 media_type(s) seen have an extractor entry: application/pdf, text/html |
| D | yes | PASS | dry scrape OK: 10 bill(s) in 114.0s |
| E | no | PASS | motion_classification.yaml has a 'fl' block |
| F | no | SKIP | walk direction (informational only, NOT written to the manifest per OPEN-34's 2026-08-07 correction): unknown (0 classifiable multi-version bill(s) in this dry scrape's sample) |
| G | no | SKIP | not run on Fargate: it needs the people checkout and the dev database |
| H | yes | SKIP | no database on Fargate -- finish with --from-dir on the Mac |
| I | yes | PASS | only one active session, so there is no other session to collide with |
| J | no | SKIP | no database on Fargate -- finish with --from-dir on the Mac |

## Details

### Gate A

**PASS** (blocking) — 85 scraped session(s), 1 active
- active: 2027

### Gate B

**PASS** (blocking) — module shape recorded
- votes scraper registered: False
- bills scraper accepts start=: True
- WAF resilience profile: cookie_provider
- no module-level RPM override found (FL_SCRAPELIB_RPM not set) -- platform default applies
- no credential env-var references found in scraper source

### Gate C

**PASS** (blocking) — all 2 media_type(s) seen have an extractor entry: application/pdf, text/html

### Gate D

**PASS** (blocking) — dry scrape OK: 10 bill(s) in 114.0s
- wall clock: 114.0s
- objects written: 10
- sample: 10 bill(s) and 0 vote event(s) (10 objects); stopped by: bill limit (limits: 10 bills, 200 objects)
- avg per-bill latency: 11.40s
- warnings/errors logged during scrape: No analysis table for SB 12
No citations table for SB 12
No chapter law table for SB 12
No vote table for SB 12
No analysis table for SB 14
No citations table for SB 14
No chapter law table for SB 14
No vote table for SB 14
No analysis table for SB 16
No citations table for SB 16
No chapter law table for SB 16
No vote table for SB 16
No analysis table for SB 18
No citations table for SB 18
No chapter law table for SB 18
No vote table for SB 18
No analysis table for SB 20
No citations table for SB 20
No chapter law table for SB 20
No vote table for SB 20
No analysis table for SB 22
No citations table for SB 22
No chapter law table for SB 22
No vote table for SB 22
No analysis table for SB 24
No citations table for SB 24
No chapter law table for SB 24
No vote table for SB 24
No analysis table for SB 26
No citations table for SB 26
No chapter law table for SB 26
No vote table for SB 26
No analysis table for SB 28
No citations table for SB 28
No chapter law table for SB 28
No vote table for SB 28
No analysis table for SB 30
No citations table for SB 30
No chapter law table for SB 30

### Gate E

**PASS** (advisory) — motion_classification.yaml has a 'fl' block

### Gate F

**SKIP** (advisory) — walk direction (informational only, NOT written to the manifest per OPEN-34's 2026-08-07 correction): unknown (0 classifiable multi-version bill(s) in this dry scrape's sample)

### Gate G

**SKIP** (advisory) — not run on Fargate: it needs the people checkout and the dev database

### Gate H

**SKIP** (blocking) — no database on Fargate -- finish with --from-dir on the Mac

### Gate I

**PASS** (blocking) — only one active session, so there is no other session to collide with
- probed session 2027: 0 vote event file(s)

### Gate J

**SKIP** (advisory) — no database on Fargate -- finish with --from-dir on the Mac

## Recommendation

Needs scoped code work before progressing: blocking gate(s) none, advisory gate(s) needing attention: none. File templated tickets per RUNBOOK.md §5 Stage 1, copying the AC structure from the matching solved OPEN ticket named in each gate's detail above.
