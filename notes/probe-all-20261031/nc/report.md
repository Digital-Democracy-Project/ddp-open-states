# Onboarding Probe — nc (North Carolina)

**Classification:** YELLOW
**Run at:** 2026-10-31T18:40:53.293605+00:00  |  **Wall clock:** 48.0s

PLAN-push-button-onboarding.md §4.4 / §5 Stage 0 -- OPEN-222. Read-only: no production database writes, no scraper code changes, no tickets filed. See the script's own docstring for exactly what each gate checks and the judgment calls made where the plan's prose left a gap.

Ran on Fargate: the people and database gates (G, H) were not run, so H shows SKIP. A RED here is final; a YELLOW is provisional. Finish on the Mac: download this run's folder (`probe/nc/probe-nc-20261031/`), un-tar `sample.tar.gz` inside it, then run `verify-jurisdiction nc --from-dir <that folder>`.

## Gate summary

| Gate | Blocking? | Status | Summary |
|---|---|---|---|
| A | yes | PASS | 46 scraped session(s), 2 active |
| B | yes | PASS | module shape recorded |
| C | yes | PASS | all 1 media_type(s) seen have an extractor entry: application/pdf |
| D | yes | PASS | dry scrape OK: 5 bill(s) in 13.1s |
| E | no | WARN | no motion_classification.yaml block for 'nc' yet |
| F | no | SKIP | walk direction (informational only, NOT written to the manifest per OPEN-34's 2026-08-07 correction): unknown (0 classifiable multi-version bill(s) in this dry scrape's sample) |
| G | no | SKIP | not run on Fargate: it needs the people checkout and the dev database |
| H | yes | SKIP | no database on Fargate -- finish with --from-dir on the Mac |
| I | yes | PASS | no vote key repeats across 2 sessions in the sample (20 vote event files) |
| J | no | SKIP | no database on Fargate -- finish with --from-dir on the Mac |

## Details

### Gate A

**PASS** (blocking) — 46 scraped session(s), 2 active
- active: 2025, 2025E1

### Gate B

**PASS** (blocking) — module shape recorded
- votes scraper registered: False
- bills scraper accepts start=: True
- WAF resilience profile: none
- no module-level RPM override found (NC_SCRAPELIB_RPM not set) -- platform default applies
- no credential env-var references found in scraper source

### Gate C

**PASS** (blocking) — all 1 media_type(s) seen have an extractor entry: application/pdf

### Gate D

**PASS** (blocking) — dry scrape OK: 5 bill(s) in 13.1s
- wall clock: 13.1s
- objects written: 5
- sample: 5 bill(s) and 7 vote event(s) (12 objects); stopped by: scraper finished (limits: 10 bills, 200 objects)
- avg per-bill latency: 2.61s

### Gate E

**WARN** (advisory) — no motion_classification.yaml block for 'nc' yet

### Gate F

**SKIP** (advisory) — walk direction (informational only, NOT written to the manifest per OPEN-34's 2026-08-07 correction): unknown (0 classifiable multi-version bill(s) in this dry scrape's sample)

### Gate G

**SKIP** (advisory) — not run on Fargate: it needs the people checkout and the dev database

### Gate H

**SKIP** (blocking) — no database on Fargate -- finish with --from-dir on the Mac

### Gate I

**PASS** (blocking) — no vote key repeats across 2 sessions in the sample (20 vote event files)
- probed session 2025E1: 7 vote event file(s)
- session 2025: dry scrape pass, 13 vote event file(s)

### Gate J

**SKIP** (advisory) — no database on Fargate -- finish with --from-dir on the Mac

## Recommendation

Needs scoped code work before progressing: blocking gate(s) none, advisory gate(s) needing attention: ['E']. File templated tickets per RUNBOOK.md §5 Stage 1, copying the AC structure from the matching solved OPEN ticket named in each gate's detail above.
