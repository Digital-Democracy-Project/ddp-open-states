# Onboarding Probe — fl (Florida)

**Classification:** GREEN
**Run at:** 2026-08-31T03:50:08.108548+00:00  |  **Wall clock:** 207.2s

PLAN-push-button-onboarding.md §4.4 / §5 Stage 0 -- OPEN-222. Read-only: no production database writes, no scraper code changes, no tickets filed. See the script's own docstring for exactly what each gate checks and the judgment calls made where the plan's prose left a gap.

## Gate summary

| Gate | Blocking? | Status | Summary |
|---|---|---|---|
| A | yes | PASS | 85 scraped session(s), 2 active |
| B | yes | PASS | module shape recorded |
| C | yes | PASS | all 2 media_type(s) seen have an extractor entry: application/pdf, text/html |
| D | yes | PASS | dry scrape OK: 8 object(s) in 204.5s |
| E | no | PASS | motion_classification.yaml has a 'fl' block |
| F | no | SKIP | walk direction (informational only, NOT written to the manifest per OPEN-34's 2026-08-07 correction): unknown (0 classifiable multi-version bill(s) in this dry scrape's sample) |
| G | no | PASS | people data / broker session-shape check OK |
| H | yes | PASS | 4672 BillVersionLink row(s) present |

## Details

### Gate A

**PASS** (blocking) — 85 scraped session(s), 2 active
- active: 2026, 2026F

### Gate B

**PASS** (blocking) — module shape recorded
- votes scraper registered: False
- bills scraper accepts start=: True
- WAF resilience profile: cookie_provider
- no credential env-var references found in scraper source

### Gate C

**PASS** (blocking) — all 2 media_type(s) seen have an extractor entry: application/pdf, text/html

### Gate D

**PASS** (blocking) — dry scrape OK: 8 object(s) in 204.5s
- wall clock: 204.5s
- objects written: 8
- avg per-bill latency: 25.56s
- warnings/errors logged during scrape: No citations table for SB 2
No chapter law table for SB 2
No vote table for SB 2
No analysis table for SB 4
No citations table for SB 4
No chapter law table for SB 4
No vote table for SB 4
No citations table for SB 6
No chapter law table for SB 6
No vote table for SB 6
No analysis table for SB 8
No citations table for SB 8
No chapter law table for SB 8
No vote table for SB 8
No analysis table for SB 10
No citations table for SB 10
No chapter law table for SB 10
No vote table for SB 10
No citations table for HB 11
No chapter law table for HB 11
No vote table for HB 11
No analysis table for SB 12
No citations table for SB 12
No chapter law table for SB 12
No vote table for SB 12
No citations table for HB 13
No chapter law table for HB 13

### Gate E

**PASS** (advisory) — motion_classification.yaml has a 'fl' block
- sample motion texts already in local DB: ['Motion to Co-Introduce', 'Favorable (Government Operations Subcommittee)', 'Favorable (Insurance & Banking Subcommittee)', 'Favorable (Judiciary Committee)', 'Favorable With Committee Substitute (Commerce Committee)', 'Favorable With Committee Substitute (PreK-12 Budget Subcommittee)', 'A - 722464, Amendment, Second Reading', 'A - 726506, Amendment, Second Reading', 'Favorable (State Affairs Committee)', 'Temporarily Postponed (Ways & Means Committee)']

### Gate F

**SKIP** (advisory) — walk direction (informational only, NOT written to the manifest per OPEN-34's 2026-08-07 correction): unknown (0 classifiable multi-version bill(s) in this dry scrape's sample)

### Gate G

**PASS** (advisory) — people data / broker session-shape check OK
- people/data/fl/legislature/ non-empty: True
- broker fixture not found locally (/Users/agentsmith/Developer/repos/ddp-broker-py/common/fixtures/jurisdictions.csv) -- this is a different repo's checkout, not expected to be present here; skipped rather than guessed

### Gate H

**PASS** (blocking) — 4672 BillVersionLink row(s) present
- BillVersionLink rows for fl: 4672
- most recent opencivicdata_bill.updated_at for fl: 2026-08-13 17:06:36.539477+00:00

## Recommendation

Config-only. Proceed to RUNBOOK.md §5 Stage 1 (fix cycle) with zero expected tickets.
