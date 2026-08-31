# Onboarding Probe — in (Indiana)

**Classification:** RED
**Run at:** 2026-08-31T18:19:55.873808+00:00  |  **Wall clock:** 0.5s

PLAN-push-button-onboarding.md §4.4 / §5 Stage 0 -- OPEN-222. Read-only: no production database writes, no scraper code changes, no tickets filed. See the script's own docstring for exactly what each gate checks and the judgment calls made where the plan's prose left a gap.

## Gate summary

| Gate | Blocking? | Status | Summary |
|---|---|---|---|
| A | yes | FAIL | get_session_list() raised KeyError('INDIANA_API_KEY') |
| B | yes | WARN | module shape recorded -- INDIANA_API_KEY, USER_AGENT referenced in source but absent from the environment (could be method-time-optional; confirm via gate D) |
| C | yes | WARN | dry scrape produced no document links to check extractor coverage against (inconclusive, not a pass) -- widen --sample-bills or re-run once bills exist |
| D | yes | FAIL | dry scrape raised: KeyError: 'INDIANA_API_KEY' |
| E | no | WARN | no motion_classification.yaml block for 'in' yet |
| F | no | SKIP | walk direction (informational only, NOT written to the manifest per OPEN-34's 2026-08-07 correction): unknown (0 classifiable multi-version bill(s) in this dry scrape's sample) |
| G | no | PASS | people data / broker session-shape check OK |
| H | yes | FAIL | zero BillVersionLink rows for this jurisdiction (the UT zero-links trap) |

## Details

### Gate A

**FAIL** (blocking) — get_session_list() raised KeyError('INDIANA_API_KEY')

### Gate B

**WARN** (blocking) — module shape recorded -- INDIANA_API_KEY, USER_AGENT referenced in source but absent from the environment (could be method-time-optional; confirm via gate D)
- votes scraper registered: False
- bills scraper accepts start=: False
- WAF resilience profile: none
- no module-level RPM override found (IN_SCRAPELIB_RPM not set) -- platform default applies
- credential env-var references found in source: INDIANA_API_KEY, USER_AGENT (present: none; absent: INDIANA_API_KEY, USER_AGENT)

### Gate C

**WARN** (blocking) — dry scrape produced no document links to check extractor coverage against (inconclusive, not a pass) -- widen --sample-bills or re-run once bills exist

### Gate D

**FAIL** (blocking) — dry scrape raised: KeyError: 'INDIANA_API_KEY'
- wall clock: 0.0s
- objects written: 0

### Gate E

**WARN** (advisory) — no motion_classification.yaml block for 'in' yet
- no vote events in local DB yet to sample motion texts from

### Gate F

**SKIP** (advisory) — walk direction (informational only, NOT written to the manifest per OPEN-34's 2026-08-07 correction): unknown (0 classifiable multi-version bill(s) in this dry scrape's sample)

### Gate G

**PASS** (advisory) — people data / broker session-shape check OK
- people/data/in/legislature/ non-empty: True
- broker fixture not found locally (/Users/agentsmith/Developer/repos/ddp-broker-py/common/fixtures/jurisdictions.csv) -- this is a different repo's checkout, not expected to be present here; skipped rather than guessed

### Gate H

**FAIL** (blocking) — zero BillVersionLink rows for this jurisdiction (the UT zero-links trap)
- import command: /Users/agentsmith/Developer/repos/ddp-open-states-dev/.venv/bin/os-update in --import --datadir /Users/agentsmith/Developer/repos/ddp-open-states-dev/openstates-scrapers/_data/_probe/in
- import exit code: 0
- BillVersionLink rows for in (jurisdiction-wide (no session determined)): 0
- most recent opencivicdata_bill.updated_at for in (jurisdiction-wide (no session determined)): None

## Recommendation

WAF/structural — needs a human scoping conversation before any fix ticket is filed (PLAN-push-button-onboarding.md §5 Stage 0's explicit red-state instruction).
