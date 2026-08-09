# Tier 1 + Tier 2 quality check — all tracked jurisdictions, 2026-08-09

Fresh run of `quality_check.py --coverage <jurisdiction> <session>` against every currently
tracked jurisdiction/session pair, comparing the real production DB (`ddp-openstates-postgres-1`,
port 5433) against the public `v3.openstates.org` API. Alabama is intentionally excluded — nothing
scrapes it.

**Tier 1** = full public/local bill-identifier diff (catches bills never scraped at all).
**Tier 2** = per-bill field diff (title, latest action, vote events/tallies, sponsorships) on a
random sample of the bills present in both APIs.

## Ranking: best to worst

Primary sort: Tier 1 real-missing rate (ascending). Secondary sort: Tier 2 real-failure rate
(ascending, live-API infra errors excluded — see Methodology). All are effectively clean; the
ranking mostly separates "provably clean" from "one real, specific, named issue."

| Rank | Jurisdiction | Session | Live bills | Local bills | Tier 1 missing (real) | Tier 1 coverage | Tier 2 sample checked | Tier 2 real failures | Tier 2 real-failure rate | Notable WARNs |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | UT | 2025S2 | 5 | 5 | 0 | 100% | 5 | 0 | 0% | — |
| 2 | UT | 2026 | 1,016 | 1,016 | 0 | 100% | 490 | 0 | 0% | 4 vote-tally diffs |
| 3 | VA | 2026S1 | 300 | 300 | 0 | 100% | 262 | 0 | 0% | 26 vote-tally diffs (see finding below) |
| 4 | VA | 2026 | 3,637 | 3,637 | 0 | 100% | 99 | 0 | 0% | 18 vote-tally diffs, 4 local-ahead |
| 5 | US | 119 | 18,335 | 18,335 | 0 | 100% | 94 | 0 | 0% | — |
| 6 | AZ | 57th-2nd-regular | 2,190 | 2,190 | 0 | 100% | 472 | 1 | 0.21% | 47 vote-tally diffs (see finding below) |
| 7 | MI | 2025-2026 | 3,910 | 3,910 | 0 | 100% | 95 | 3 | 3.16% | 3 bills missing vote data |
| 8 | WA | 2025-2026 | 3,413 | 3,411 | 2 | 99.94% | 99 | 0 | 0% | — |
| 9 | MA | 194th | 18,629 | 11,108 | 124\* | 99.33%\* | 90 | 0 | 0% | 7,397 docket-stage duplicates (not real, see below) |
| 10 | FL | 2026 | 1,931 | 1,897 | 34 | 98.24% | 462 | 35 | 7.58% | 21 local-ahead, known WAF bug (OPEN-27) |

\* MA's raw Tier 1 diff is 7,521 (59.6% "missing") — the tool's `DOCKET_PREFIX_MAP` correction
strips out 7,397 of those as docket-stage duplicates (live's permanent HD/SD docket number for a
bill we already have under its H/S bill number, not a real gap). 124 is the corrected, real count.

## Methodology notes

- **"Tier 2 real failures" excludes live-API infra noise.** During Tier 2 sampling, individual
  per-bill fetches against `v3.openstates.org` intermittently hit `429`/`502`/read-timeout errors
  from the same rate limit described below. `compare_bills()` records those as a generic FAIL
  ("live API error"), indistinguishable at a glance from an actual content mismatch. We excluded
  those from both the numerator and denominator (i.e. "real-failure rate" = real content mismatches
  ÷ bills that actually got compared) rather than counting infra noise as a data-quality failure.
  Noise-affected bill counts by jurisdiction: VA 2026S1 (38), FL (38), AZ (28), UT 2026 (10), MA
  (10), US (6), MI (5), WA (1), VA 2026 (1), UT 2025S2 (0).
- **Sample sizes vary.** AZ, FL, UT (both sessions), and VA 2026S1 got the requested 500-bill
  random Tier 2 sample (or full population where smaller). WA, VA 2026, MI, MA, and US/119 — the
  five largest/most rate-limited jurisdictions — needed a second, more patient retry pass (7-minute
  cooldowns between attempts) after repeatedly crashing on rate limits at the 500-bill setting, and
  completed at a reduced 100-bill sample.
- **Live API rate limiting was real and severe.** The first full-sweep attempt hit `429 Too Many
  Requests` starting on the 4th of 10 pairs, and a second attempt (with Tier 2 bumped to 500) got
  through only 5 of 10 pairs before every subsequent jurisdiction crashed repeatedly (429s and
  connection timeouts) despite 5 retries with 90-second cooldowns each. A dedicated retry pass with
  longer (7-minute) cooldowns and a smaller 100-bill sample eventually got all 5 remaining pairs
  through. Total run time across both passes: roughly 4.5 hours.

## Findings worth flagging separately (not folded into the ranking above)

1. **FL has a real, known vote-completeness gap** (OPEN-27): local is missing vote data on 35 of
   462 effectively-checked bills (7.6%). This matches the previously-diagnosed FL House WAF-session-
   cookie-expiry bug in the upstream scraper (unpatched at
   `openstates-scrapers` PR #5751) — not a new issue, but this run reconfirms it's still live and
   quantifies it at a larger (500-bill) sample than prior checks.
2. **A vote-tally pairing artifact inflates VA and AZ's WARN counts.** VA HB 30 (2026S1) and AZ
   HB 2114 / HB 2190 (57th-2nd-regular) each show a "vote tally differs" WARN where the local and
   live voter sets are *completely disjoint* — not a few voters off, but two entirely different
   roll calls (e.g. a ~24-member vote vs. a ~100-member vote on the same bill/date). This looks like
   `compare_bills()`'s positional-fallback pairing (used when `motion_text` is blank on both sides)
   matching two unrelated same-day roll calls — likely one chamber's vote against the other
   chamber's companion vote — rather than a real local/live data discrepancy. Worth a tool fix
   (pair by chamber/`from_organization` when motion_text is blank) before trusting VA/AZ's raw
   vote-tally-diff counts as real quality signal.
3. **MA's headline Tier 1 number is misleading without the docket correction.** Raw missing is
   7,521 (59.6%); real missing is 124 (0.67%). Anyone querying MA's coverage directly should use
   `--coverage` (which applies `DOCKET_PREFIX_MAP`), not a naive identifier-set diff.
4. **The live API's rate limit is tighter than the tooling assumes.** `quality_check.py`'s own
   docstring says "designed to stay well within the 250 req/day API rate limit," but Tier 1's full
   identifier pagination alone can cost hundreds of requests for a single large jurisdiction (MA:
   ~930 pages at 20/page). A full-coverage sweep across all tracked jurisdictions in one day is
   only reliably achievable with patient, long-cooldown retries — budget several hours, not
   minutes, for a repeat of this sweep.

## Raw logs

`logs/quality-check/<jurisdiction>_<session>.log` (this run's output, from `quality_check.py`'s own
`--coverage` log writer) plus `logs/quality-check/sweep_summary_20260809.txt` and
`logs/quality-check/retry_missing_summary_20260809.txt` (driver-script summaries) in this checkout.
