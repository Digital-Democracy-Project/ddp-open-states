# Onboarding Probe — ks (Kansas)

**Classification:** YELLOW
**Run at:** 2026-10-31T18:40:13.488041+00:00  |  **Wall clock:** 22.9s

PLAN-push-button-onboarding.md §4.4 / §5 Stage 0 -- OPEN-222. Read-only: no production database writes, no scraper code changes, no tickets filed. See the script's own docstring for exactly what each gate checks and the judgment calls made where the plan's prose left a gap.

Ran on Fargate: the people and database gates (G, H) were not run, so H shows SKIP. A RED here is final; a YELLOW is provisional. Finish on the Mac: download this run's folder (`probe/ks/probe-ks-20261031/`), un-tar `sample.tar.gz` inside it, then run `verify-jurisdiction ks --from-dir <that folder>`.

## Gate summary

| Gate | Blocking? | Status | Summary |
|---|---|---|---|
| A | yes | PASS | 13 scraped session(s), 1 active |
| B | yes | PASS | module shape recorded |
| C | yes | FAIL | 1 media_type(s) with no CONVERSION_FUNCTIONS['ks'] entry: text/html |
| D | yes | PASS | dry scrape OK: 10 bill(s) in 22.4s |
| E | no | WARN | no motion_classification.yaml block for 'ks' yet |
| F | no | SKIP | walk direction (informational only, NOT written to the manifest per OPEN-34's 2026-08-07 correction): unknown (0 classifiable multi-version bill(s) in this dry scrape's sample) |
| G | no | SKIP | not run on Fargate: it needs the people checkout and the dev database |
| H | yes | SKIP | no database on Fargate -- finish with --from-dir on the Mac |
| I | yes | PASS | only one active session, so there is no other session to collide with |
| J | no | SKIP | no database on Fargate -- finish with --from-dir on the Mac |

## Details

### Gate A

**PASS** (blocking) — 13 scraped session(s), 1 active
- active: 2025-2026

### Gate B

**PASS** (blocking) — module shape recorded
- votes scraper registered: True
- bills scraper accepts start=: False
- WAF resilience profile: none
- no module-level RPM override found (KS_SCRAPELIB_RPM not set) -- platform default applies
- no credential env-var references found in scraper source

### Gate C

**FAIL** (blocking) — 1 media_type(s) with no CONVERSION_FUNCTIONS['ks'] entry: text/html

### Gate D

**PASS** (blocking) — dry scrape OK: 10 bill(s) in 22.4s
- wall clock: 22.4s
- objects written: 10
- sample: 10 bill(s) and 0 vote event(s) (10 objects); stopped by: bill limit (limits: 10 bills, 200 objects)
- avg per-bill latency: 2.24s
- warnings/errors logged during scrape: No date found for action row Hearing: Tuesday, March 17, 2026, 9:00 AM — Room 346-S event for SB1 in 2025-2026
No date found for action row Hearing: Thursday, January 23, 2025, 10:30 AM — Room 144-S event for SB1 in 2025-2026
No date found for action row Hearing: Wednesday, March 5, 2025, 9:00 AM — Room 281-N event for SB2 in 2025-2026
No date found for action row Hearing: Tuesday, February 11, 2025, 10:30 AM — Room 548-S event for SB2 in 2025-2026
No date found for action row Hearing: Tuesday, January 28, 2025, 9:30 AM — Room 142-S event for SB2 in 2025-2026
No date found for action row Hearing: Tuesday, February 4, 2025, 8:30 AM — Room 142-S event for SB3 in 2025-2026
No date found for action row Hearing: Tuesday, February 11, 2025, 3:30 PM — Room 218-N event for SB4 in 2025-2026
No date found for action row Hearing: Wednesday, January 22, 2025, 10:30 AM — Room 144-S event for SB4 in 2025-2026
No date found for action row Hearing: Tuesday, February 25, 2025, 3:30 PM — Room 218-N event for SB5 in 2025-2026
No date found for action row Hearing: Thursday, February 27, 2025, 3:30 PM — Room 218-N event for SB6 in 2025-2026
No date found for action row Hearing: Monday, March 3, 2025, 9:00 AM — Room 281-N event for SB7 in 2025-2026
No date found for action row Hearing: Tuesday, January 28, 2025, 9:30 AM — Room 142-S event for SB7 in 2025-2026
No date found for action row Hearing: Thursday, February 27, 2025, 1:30 PM — Room 582-N event for SB8 in 2025-2026
No date found for action row Hearing: Thursday, January 23, 2025, 8:30 AM — Room 546-S event for SB8 in 2025-2026
No date found for action row Hearing: Tuesday, February 25, 2025, 9:08 AM — Room 346-S event for SB9 in 2025-2026
No date found for action row Hearing: Tuesday, February 25, 2025, 9:00 AM — Room 346-S event for SB9 in 2025-2026
No date found for action row Hearing: Tuesday, January 28, 2025, 8:30 AM — Room 546-S event for SB9 in 2025-2026
No date found for action row Hearing: Monday, February 10, 2025, 3:30 

### Gate E

**WARN** (advisory) — no motion_classification.yaml block for 'ks' yet

### Gate F

**SKIP** (advisory) — walk direction (informational only, NOT written to the manifest per OPEN-34's 2026-08-07 correction): unknown (0 classifiable multi-version bill(s) in this dry scrape's sample)

### Gate G

**SKIP** (advisory) — not run on Fargate: it needs the people checkout and the dev database

### Gate H

**SKIP** (blocking) — no database on Fargate -- finish with --from-dir on the Mac

### Gate I

**PASS** (blocking) — only one active session, so there is no other session to collide with
- probed session 2025-2026: 0 vote event file(s)

### Gate J

**SKIP** (advisory) — no database on Fargate -- finish with --from-dir on the Mac

## Recommendation

Needs scoped code work before progressing: blocking gate(s) ['C'], advisory gate(s) needing attention: ['E']. File templated tickets per RUNBOOK.md §5 Stage 1, copying the AC structure from the matching solved OPEN ticket named in each gate's detail above.
