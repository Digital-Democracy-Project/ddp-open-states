# Onboarding Probe — va (Virginia)

**Classification:** YELLOW
**Run at:** 2026-10-31T18:41:33.581899+00:00  |  **Wall clock:** 80.4s

PLAN-push-button-onboarding.md §4.4 / §5 Stage 0 -- OPEN-222. Read-only: no production database writes, no scraper code changes, no tickets filed. See the script's own docstring for exactly what each gate checks and the judgment calls made where the plan's prose left a gap.

Ran on Fargate: the people and database gates (G, H) were not run, so H shows SKIP. A RED here is final; a YELLOW is provisional. Finish on the Mac: download this run's folder (`probe/va/probe-va-20261031/`), un-tar `sample.tar.gz` inside it, then run `verify-jurisdiction va --from-dir <that folder>`.

## Gate summary

| Gate | Blocking? | Status | Summary |
|---|---|---|---|
| A | yes | PASS | 58 scraped session(s), 2 active |
| B | yes | PASS | module shape recorded |
| C | yes | PASS | all 2 media_type(s) seen have an extractor entry: application/pdf, text/html |
| D | yes | PASS | dry scrape OK: 10 bill(s) in 40.1s |
| E | no | PASS | motion_classification.yaml has a 'va' block |
| F | no | SKIP | walk direction (informational only, NOT written to the manifest per OPEN-34's 2026-08-07 correction): unknown (0 classifiable multi-version bill(s) in this dry scrape's sample) |
| G | no | SKIP | not run on Fargate: it needs the people checkout and the dev database |
| H | yes | SKIP | no database on Fargate -- finish with --from-dir on the Mac |
| I | yes | PASS | no vote key repeats across 2 sessions in the sample (29 vote event files) |
| J | no | SKIP | no database on Fargate -- finish with --from-dir on the Mac |

## Details

### Gate A

**PASS** (blocking) — 58 scraped session(s), 2 active
- active: 2026S1, 2027

### Gate B

**PASS** (blocking) — module shape recorded
- votes scraper registered: False
- bills scraper accepts start=: True
- WAF resilience profile: none
- no module-level RPM override found (VA_SCRAPELIB_RPM not set) -- platform default applies
- credential env-var references found in source: VA_API_KEY (present: VA_API_KEY; absent: none)

### Gate C

**PASS** (blocking) — all 2 media_type(s) seen have an extractor entry: application/pdf, text/html

### Gate D

**PASS** (blocking) — dry scrape OK: 10 bill(s) in 40.1s
- wall clock: 40.1s
- objects written: 10
- sample: 10 bill(s) and 0 vote event(s) (10 objects); stopped by: bill limit (limits: 10 bills, 200 objects)
- avg per-bill latency: 4.01s

### Gate E

**PASS** (advisory) — motion_classification.yaml has a 'va' block

### Gate F

**SKIP** (advisory) — walk direction (informational only, NOT written to the manifest per OPEN-34's 2026-08-07 correction): unknown (0 classifiable multi-version bill(s) in this dry scrape's sample)

### Gate G

**SKIP** (advisory) — not run on Fargate: it needs the people checkout and the dev database

### Gate H

**SKIP** (blocking) — no database on Fargate -- finish with --from-dir on the Mac

### Gate I

**PASS** (blocking) — no vote key repeats across 2 sessions in the sample (29 vote event files)
- probed session 2027: 0 vote event file(s)
- session 2026S1: dry scrape pass, 29 vote event file(s)

### Gate J

**SKIP** (advisory) — no database on Fargate -- finish with --from-dir on the Mac

## Recommendation

Needs scoped code work before progressing: blocking gate(s) none, advisory gate(s) needing attention: none. File templated tickets per RUNBOOK.md §5 Stage 1, copying the AC structure from the matching solved OPEN ticket named in each gate's detail above.
