# Onboarding Probe — ut (Utah)

**Classification:** YELLOW
**Run at:** 2026-10-31T18:41:33.363999+00:00  |  **Wall clock:** 62.1s

PLAN-push-button-onboarding.md §4.4 / §5 Stage 0 -- OPEN-222. Read-only: no production database writes, no scraper code changes, no tickets filed. See the script's own docstring for exactly what each gate checks and the judgment calls made where the plan's prose left a gap.

Ran on Fargate: the people and database gates (G, H) were not run, so H shows SKIP. A RED here is final; a YELLOW is provisional. Finish on the Mac: download this run's folder (`probe/ut/probe-ut-20261031/`), un-tar `sample.tar.gz` inside it, then run `verify-jurisdiction ut --from-dir <that folder>`.

## Gate summary

| Gate | Blocking? | Status | Summary |
|---|---|---|---|
| A | yes | PASS | 84 scraped session(s), 2 active |
| B | yes | WARN | module shape recorded -- USER_AGENT referenced in source but absent from the environment (could be method-time-optional; confirm via gate D) |
| C | yes | PASS | all 2 media_type(s) seen have an extractor entry: application/pdf, text/xml |
| D | yes | PASS | dry scrape OK: 10 bill(s) in 40.2s |
| E | no | PASS | motion_classification.yaml has a 'ut' block |
| F | no | SKIP | walk direction (informational only, NOT written to the manifest per OPEN-34's 2026-08-07 correction): unknown (0 classifiable multi-version bill(s) in this dry scrape's sample) |
| G | no | SKIP | not run on Fargate: it needs the people checkout and the dev database |
| H | yes | SKIP | no database on Fargate -- finish with --from-dir on the Mac |
| I | yes | PASS | no vote key repeats across 2 sessions in the sample (30 vote event files) |
| J | no | SKIP | no database on Fargate -- finish with --from-dir on the Mac |

## Details

### Gate A

**PASS** (blocking) — 84 scraped session(s), 2 active
- active: 2025S2, 2026

### Gate B

**WARN** (blocking) — module shape recorded -- USER_AGENT referenced in source but absent from the environment (could be method-time-optional; confirm via gate D)
- votes scraper registered: False
- bills scraper accepts start=: True
- WAF resilience profile: none
- no module-level RPM override found (UT_SCRAPELIB_RPM not set) -- platform default applies
- credential env-var references found in source: USER_AGENT (present: none; absent: USER_AGENT)

### Gate C

**PASS** (blocking) — all 2 media_type(s) seen have an extractor entry: application/pdf, text/xml

### Gate D

**PASS** (blocking) — dry scrape OK: 10 bill(s) in 40.2s
- wall clock: 40.2s
- objects written: 10
- sample: 10 bill(s) and 20 vote event(s) (30 objects); stopped by: bill limit (limits: 10 bills, 200 objects)
- avg per-bill latency: 4.02s
- warnings/errors logged during scrape: Found unexpected actor Legislative Fiscal Analyst at https://le.utah.gov/data/2026GS/HB0001.json?_=1793472096877
Found unexpected actor Legislative Fiscal Agency at https://le.utah.gov/data/2026GS/HB0001.json?_=1793472096877
Found unexpected actor Version Sponsor at https://le.utah.gov/data/2026GS/HB0001.json?_=1793472096877
Found unexpected actor Released at https://le.utah.gov/data/2026GS/HB0001.json?_=1793472096877
Found unexpected actor Legislative Research and General Counsel / Enrolling at https://le.utah.gov/data/2026GS/HB0001.json?_=1793472096877
Found unexpected actor Legislative Research and General Counsel / Enrolling at https://le.utah.gov/data/2026GS/HB0001.json?_=1793472096877
Found unexpected actor Legislative Research and General Counsel / Enrolling at https://le.utah.gov/data/2026GS/HB0001.json?_=1793472096877
Found unexpected actor Legislative Fiscal Analyst at https://le.utah.gov/data/2026GS/HB0002.json?_=1793472100883
Found unexpected actor Legislative Fiscal Agency at https://le.utah.gov/data/2026GS/HB0002.json?_=1793472100883
Found unexpected actor Version Sponsor at https://le.utah.gov/data/2026GS/HB0002.json?_=1793472100883
Found unexpected actor Released at https://le.utah.gov/data/2026GS/HB0002.json?_=1793472100883
Found unexpected actor Legislative Research and General Counsel / Enrolling at https://le.utah.gov/data/2026GS/HB0002.json?_=1793472100883
Found unexpected actor Legislative Research and General Counsel / Enrolling at https://le.utah.gov/data/2026GS/HB0002.json?_=1793472100883
Found unexpected actor Legislative Fiscal Analyst at https://le.utah.gov/data/2026GS/HB0003.json?_=1793472104864
Found unexpected actor Legislative Fiscal Agency at https://le.utah.gov/data/2026GS/HB0003.json?_=1793472104864
Found unexpected actor Version Sponsor at https://le.utah.gov/data/2026GS/HB0003.json?_=1793472104864
Found unexpected actor Released at https://le.utah.gov/data/2026GS/HB0003.json?_=1793472104864
Found unexpected actor Legislative Rese

### Gate E

**PASS** (advisory) — motion_classification.yaml has a 'ut' block

### Gate F

**SKIP** (advisory) — walk direction (informational only, NOT written to the manifest per OPEN-34's 2026-08-07 correction): unknown (0 classifiable multi-version bill(s) in this dry scrape's sample)

### Gate G

**SKIP** (advisory) — not run on Fargate: it needs the people checkout and the dev database

### Gate H

**SKIP** (blocking) — no database on Fargate -- finish with --from-dir on the Mac

### Gate I

**PASS** (blocking) — no vote key repeats across 2 sessions in the sample (30 vote event files)
- probed session 2026: 20 vote event file(s)
- session 2025S2: dry scrape pass, 10 vote event file(s)

### Gate J

**SKIP** (advisory) — no database on Fargate -- finish with --from-dir on the Mac

## Recommendation

Needs scoped code work before progressing: blocking gate(s) none, advisory gate(s) needing attention: none. File templated tickets per RUNBOOK.md §5 Stage 1, copying the AC structure from the matching solved OPEN ticket named in each gate's detail above.
