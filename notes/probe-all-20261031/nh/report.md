# Onboarding Probe — nh (New Hampshire)

**Classification:** RED
**Run at:** 2026-10-31T18:40:51.952911+00:00  |  **Wall clock:** 133.3s

PLAN-push-button-onboarding.md §4.4 / §5 Stage 0 -- OPEN-222. Read-only: no production database writes, no scraper code changes, no tickets filed. See the script's own docstring for exactly what each gate checks and the judgment calls made where the plan's prose left a gap.

Ran on Fargate: the people and database gates (G, H) were not run, so H shows SKIP. A RED here is final; a YELLOW is provisional. Finish on the Mac: download this run's folder (`probe/nh/probe-nh-20261031/`), un-tar `sample.tar.gz` inside it, then run `verify-jurisdiction nh --from-dir <that folder>`.

## Gate summary

| Gate | Blocking? | Status | Summary |
|---|---|---|---|
| A | yes | PASS | 1 scraped session(s), 1 active |
| B | yes | PASS | module shape recorded |
| C | yes | WARN | dry scrape produced no document links to check extractor coverage against (inconclusive, not a pass) -- widen --sample-bills or re-run once bills exist |
| D | yes | FAIL | dry scrape raised: ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')) |
| E | no | WARN | no motion_classification.yaml block for 'nh' yet |
| F | no | SKIP | walk direction (informational only, NOT written to the manifest per OPEN-34's 2026-08-07 correction): unknown (0 classifiable multi-version bill(s) in this dry scrape's sample) |
| G | no | SKIP | not run on Fargate: it needs the people checkout and the dev database |
| H | yes | SKIP | no database on Fargate -- finish with --from-dir on the Mac |
| I | yes | SKIP | gate D did not pass, so there is no sample to compare |
| J | no | SKIP | no database on Fargate -- finish with --from-dir on the Mac |

## Details

### Gate A

**PASS** (blocking) — 1 scraped session(s), 1 active
- active: 2026

### Gate B

**PASS** (blocking) — module shape recorded
- votes scraper registered: False
- bills scraper accepts start=: False
- WAF resilience profile: none
- no module-level RPM override found (NH_SCRAPELIB_RPM not set) -- platform default applies
- no credential env-var references found in scraper source

### Gate C

**WARN** (blocking) — dry scrape produced no document links to check extractor coverage against (inconclusive, not a pass) -- widen --sample-bills or re-run once bills exist

### Gate D

**FAIL** (blocking) — dry scrape raised: ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
- wall clock: 133.2s
- objects written: 0
- warnings/errors logged during scrape: NH bans scraping between 6am and 9pm. This may fail.
Missing version_id for SB34, can't build bill page
Missing version_id for SB211, can't build bill page
Missing version_id for SB33, can't build bill page
Missing version_id for SB71, can't build bill page
Missing version_id for SB15, can't build bill page
Missing version_id for SB270, can't build bill page
Missing version_id for SB36, can't build bill page
Missing version_id for SB106, can't build bill page
Missing version_id for SB39, can't build bill page
Missing version_id for SB103, can't build bill page
Missing version_id for SB223, can't build bill page
Missing version_id for SB183, can't build bill page
Missing version_id for SB49, can't build bill page
Missing version_id for SB149, can't build bill page
Missing version_id for SB44, can't build bill page
Missing version_id for SB41, can't build bill page
Missing version_id for SB123, can't build bill page
Missing version_id for SB155, can't build bill page
Missing version_id for SB185, can't build bill page
Missing version_id for SB27, can't build bill page
Missing version_id for SB139, can't build bill page
Missing version_id for SB56, can't build bill page
Missing version_id for SB150, can't build bill page
Missing version_id for SB226, can't build bill page
Missing version_id for SB186, can't build bill page
Missing version_id for SB82, can't build bill page
Missing version_id for SB247, can't build bill page
Missing version_id for SB208, can't build bill page
Missing version_id for SB83, can't build bill page
Missing version_id for SB187, can't build bill page
Missing version_id for SB256, can't build bill page
Missing version_id for SB84, can't build bill page
Missing version_id for SB109, can't build bill page
Missing version_id for SB204, can't build bill page
Missing version_id for SB261, can't build bill page
Missing version_id for SB63, can't build bill page
Missing version_id for SB101, can't build bill page
Missing version_id for SB142, can't bu

### Gate E

**WARN** (advisory) — no motion_classification.yaml block for 'nh' yet

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
