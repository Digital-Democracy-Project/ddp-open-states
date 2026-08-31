# Onboarding Probe — nc (North Carolina)

**Classification:** YELLOW
**Run at:** 2026-08-31T18:18:43.661385+00:00  |  **Wall clock:** 44.4s

PLAN-push-button-onboarding.md §4.4 / §5 Stage 0 -- OPEN-222. Read-only: no production database writes, no scraper code changes, no tickets filed. See the script's own docstring for exactly what each gate checks and the judgment calls made where the plan's prose left a gap.

## Gate summary

| Gate | Blocking? | Status | Summary |
|---|---|---|---|
| A | yes | PASS | 45 scraped session(s), 1 active |
| B | yes | PASS | module shape recorded |
| C | yes | PASS | all 1 media_type(s) seen have an extractor entry: application/pdf |
| D | yes | PASS | dry scrape OK: 9 object(s) in 43.3s |
| E | no | WARN | no motion_classification.yaml block for 'nc' yet |
| F | no | SKIP | walk direction (informational only, NOT written to the manifest per OPEN-34's 2026-08-07 correction): unknown (0 classifiable multi-version bill(s) in this dry scrape's sample) |
| G | no | PASS | people data / broker session-shape check OK |
| H | yes | FAIL | zero BillVersionLink rows for this jurisdiction (the UT zero-links trap) |

## Details

### Gate A

**PASS** (blocking) — 45 scraped session(s), 1 active
- active: 2025

### Gate B

**PASS** (blocking) — module shape recorded
- votes scraper registered: False
- bills scraper accepts start=: False
- WAF resilience profile: none
- no module-level RPM override found (NC_SCRAPELIB_RPM not set) -- platform default applies
- no credential env-var references found in scraper source

### Gate C

**PASS** (blocking) — all 1 media_type(s) seen have an extractor entry: application/pdf

### Gate D

**PASS** (blocking) — dry scrape OK: 9 object(s) in 43.3s
- wall clock: 43.3s
- objects written: 9
- avg per-bill latency: 4.82s

### Gate E

**WARN** (advisory) — no motion_classification.yaml block for 'nc' yet
- no vote events in local DB yet to sample motion texts from

### Gate F

**SKIP** (advisory) — walk direction (informational only, NOT written to the manifest per OPEN-34's 2026-08-07 correction): unknown (0 classifiable multi-version bill(s) in this dry scrape's sample)

### Gate G

**PASS** (advisory) — people data / broker session-shape check OK
- people/data/nc/legislature/ non-empty: True
- broker fixture not found locally (/Users/agentsmith/Developer/repos/ddp-broker-py/common/fixtures/jurisdictions.csv) -- this is a different repo's checkout, not expected to be present here; skipped rather than guessed

### Gate H

**FAIL** (blocking) — zero BillVersionLink rows for this jurisdiction (the UT zero-links trap)
- import command: /Users/agentsmith/Developer/repos/ddp-open-states-dev/.venv/bin/os-update nc --import --datadir /Users/agentsmith/Developer/repos/ddp-open-states-dev/openstates-scrapers/_data/_probe/nc
- import exit code: 0
- BillVersionLink rows for nc (session 2025): 0
- most recent opencivicdata_bill.updated_at for nc (session 2025): None

## Recommendation

Needs scoped code work before progressing: blocking gate(s) ['H'], advisory gate(s) needing attention: ['E']. File templated tickets per RUNBOOK.md §5 Stage 1, copying the AC structure from the matching solved OPEN ticket named in each gate's detail above.
