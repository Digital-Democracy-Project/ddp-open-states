# Onboarding Probe — nm (New Mexico)

**Classification:** RED
**Run at:** 2026-10-31T18:40:53.876836+00:00  |  **Wall clock:** 3.0s

PLAN-push-button-onboarding.md §4.4 / §5 Stage 0 -- OPEN-222. Read-only: no production database writes, no scraper code changes, no tickets filed. See the script's own docstring for exactly what each gate checks and the judgment calls made where the plan's prose left a gap.

Ran on Fargate: the people and database gates (G, H) were not run, so H shows SKIP. A RED here is final; a YELLOW is provisional. Finish on the Mac: download this run's folder (`probe/nm/probe-nm-20261031/`), un-tar `sample.tar.gz` inside it, then run `verify-jurisdiction nm --from-dir <that folder>`.

## Gate summary

| Gate | Blocking? | Status | Summary |
|---|---|---|---|
| A | yes | PASS | 56 scraped session(s), 1 active |
| B | yes | PASS | module shape recorded |
| C | yes | WARN | dry scrape produced no document links to check extractor coverage against (inconclusive, not a pass) -- widen --sample-bills or re-run once bills exist |
| D | yes | FAIL | dry scrape raised: FileNotFoundError: [Errno 2] No such file or directory: 'mdb-export' |
| E | no | WARN | no motion_classification.yaml block for 'nm' yet |
| F | no | SKIP | walk direction (informational only, NOT written to the manifest per OPEN-34's 2026-08-07 correction): unknown (0 classifiable multi-version bill(s) in this dry scrape's sample) |
| G | no | SKIP | not run on Fargate: it needs the people checkout and the dev database |
| H | yes | SKIP | no database on Fargate -- finish with --from-dir on the Mac |
| I | yes | SKIP | gate D did not pass, so there is no sample to compare |
| J | no | SKIP | no database on Fargate -- finish with --from-dir on the Mac |

## Details

### Gate A

**PASS** (blocking) — 56 scraped session(s), 1 active
- active: 2026

### Gate B

**PASS** (blocking) — module shape recorded
- votes scraper registered: True
- bills scraper accepts start=: False
- WAF resilience profile: none
- no module-level RPM override found (NM_SCRAPELIB_RPM not set) -- platform default applies
- no credential env-var references found in scraper source

### Gate C

**WARN** (blocking) — dry scrape produced no document links to check extractor coverage against (inconclusive, not a pass) -- widen --sample-bills or re-run once bills exist

### Gate D

**FAIL** (blocking) — dry scrape raised: FileNotFoundError: [Errno 2] No such file or directory: 'mdb-export'
- wall clock: 2.0s
- objects written: 0
- warnings/errors logged during scrape: Failed to read mdb file. Have you installed 'mdbtools' ?

### Gate E

**WARN** (advisory) — no motion_classification.yaml block for 'nm' yet

### Gate F

**SKIP** (advisory) — walk direction (informational only, NOT written to the manifest per OPEN-34's 2026-08-07 correction): unknown (0 classifiable multi-version bill(s) in this dry scrape's sample)

### Gate G

**SKIP** (advisory) — not run on Fargate: it needs the people checkout and the dev database

### Gate H

**SKIP** (blocking) — no database on Fargate -- finish with --from-dir on the Mac

### Gate I

**SKIP** (blocking) — gate D did not pass, so there is no sample to compare

### Gate J

**SKIP** (advisory) — no database on Fargate -- finish with --from-dir on the Mac

## Recommendation

WAF/structural — needs a human scoping conversation before any fix ticket is filed (PLAN-push-button-onboarding.md §5 Stage 0's explicit red-state instruction).
