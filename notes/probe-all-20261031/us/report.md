# Onboarding Probe — us (United States)

**Classification:** YELLOW
**Run at:** 2026-10-31T18:41:32.980209+00:00  |  **Wall clock:** 11.5s

PLAN-push-button-onboarding.md §4.4 / §5 Stage 0 -- OPEN-222. Read-only: no production database writes, no scraper code changes, no tickets filed. See the script's own docstring for exactly what each gate checks and the judgment calls made where the plan's prose left a gap.

Ran on Fargate: the people and database gates (G, H) were not run, so H shows SKIP. A RED here is final; a YELLOW is provisional. Finish on the Mac: download this run's folder (`probe/us/probe-us-20261031/`), un-tar `sample.tar.gz` inside it, then run `verify-jurisdiction us --from-dir <that folder>`.

## Gate summary

| Gate | Blocking? | Status | Summary |
|---|---|---|---|
| A | yes | PASS | 8 scraped session(s), 1 active |
| B | yes | WARN | module shape recorded -- HTTPS_PROXY_SELECTIVE, HTTP_PROXY_SELECTIVE referenced in source but absent from the environment (could be method-time-optional; confirm via gate D) |
| C | yes | FAIL | 1 media_type(s) with no CONVERSION_FUNCTIONS['us'] entry: text/html |
| D | yes | PASS | dry scrape OK: 10 bill(s) in 11.5s |
| E | no | PASS | motion_classification.yaml has a 'us' block |
| F | no | SKIP | walk direction (informational only, NOT written to the manifest per OPEN-34's 2026-08-07 correction): unknown (3 classifiable multi-version bill(s) in this dry scrape's sample) |
| G | no | SKIP | not run on Fargate: it needs the people checkout and the dev database |
| H | yes | SKIP | no database on Fargate -- finish with --from-dir on the Mac |
| I | yes | PASS | only one active session, so there is no other session to collide with |
| J | no | SKIP | no database on Fargate -- finish with --from-dir on the Mac |

## Details

### Gate A

**PASS** (blocking) — 8 scraped session(s), 1 active
- active: 119

### Gate B

**WARN** (blocking) — module shape recorded -- HTTPS_PROXY_SELECTIVE, HTTP_PROXY_SELECTIVE referenced in source but absent from the environment (could be method-time-optional; confirm via gate D)
- votes scraper registered: False
- bills scraper accepts start=: True
- WAF resilience profile: none
- no module-level RPM override found (US_SCRAPELIB_RPM not set) -- platform default applies
- credential env-var references found in source: CONGRESS_GOV_API_KEY, HTTPS_PROXY_SELECTIVE, HTTP_PROXY_SELECTIVE (present: CONGRESS_GOV_API_KEY; absent: HTTPS_PROXY_SELECTIVE, HTTP_PROXY_SELECTIVE)

### Gate C

**FAIL** (blocking) — 1 media_type(s) with no CONVERSION_FUNCTIONS['us'] entry: text/html

### Gate D

**PASS** (blocking) — dry scrape OK: 10 bill(s) in 11.5s
- wall clock: 11.5s
- objects written: 10
- sample: 10 bill(s) and 5 vote event(s) (15 objects); stopped by: bill limit (limits: 10 bills, 200 objects)
- avg per-bill latency: 1.15s

### Gate E

**PASS** (advisory) — motion_classification.yaml has a 'us' block

### Gate F

**SKIP** (advisory) — walk direction (informational only, NOT written to the manifest per OPEN-34's 2026-08-07 correction): unknown (3 classifiable multi-version bill(s) in this dry scrape's sample)

### Gate G

**SKIP** (advisory) — not run on Fargate: it needs the people checkout and the dev database

### Gate H

**SKIP** (blocking) — no database on Fargate -- finish with --from-dir on the Mac

### Gate I

**PASS** (blocking) — only one active session, so there is no other session to collide with
- probed session 119: 5 vote event file(s)

### Gate J

**SKIP** (advisory) — no database on Fargate -- finish with --from-dir on the Mac

## Recommendation

Needs scoped code work before progressing: blocking gate(s) ['C'], advisory gate(s) needing attention: none. File templated tickets per RUNBOOK.md §5 Stage 1, copying the AC structure from the matching solved OPEN ticket named in each gate's detail above.
