# MI retry test: 94% of the WAF-blocked documents recovered on a second pass ~2 hours later

Ramon's ask: re-run the same one-off MI archive to see how many of the first run's 64 real
fetch failures would clear on a second attempt. Launched a second identical run
(`RUN_ID=mi-archive-a3aace7dd9c9`) once the first one finished.

**Real result, precise URL-level comparison against the saved list of the first run's 46
distinct 403 URLs:**

- **43 of 46 (94%) succeeded this time.**
- **3 still genuinely stuck** on a second attempt:
  - `2025-SCVBS-0709-00C77.PDF`
  - `2026-SIB-1163.pdf`
  - `2026-SAR-0139.pdf`
- 5 new documents hit a fresh 403 this run that weren't blocked the first time (minor noise,
  not concerning on its own -- these were among the original run's non-403 failures).

Second run's own summary line: `mi: 3973 bills checked | fetched=40 skipped=13758 archived=40
fetch_errors=24 ... extract_errors=2 s3_verified=40`. `fetched(40) + fetch_errors(24) = 64`
exactly matches the first run's total failure count -- confirms the natural-key skip-check
correctly limited this run to *only* re-attempting the specific documents that failed before,
nothing else re-fetched unnecessarily.

**Cumulative RDS state across both runs today**: 13,597 -> 13,802 total documents (+205),
13,432 -> 13,633 with usable extracted text (+201), 165 -> 169 `is_error` (+4, small and
consistent with the two separate `extract_errors=2` counts, unrelated to the WAF issue).

**Real takeaway**: Michigan's WAF block from earlier today was genuinely transient, not a
lasting IP/session ban -- a retry a couple hours later cleared the large majority of it on its
own, no special intervention needed. The 3 still-stuck documents might be worth an individual
look if anyone cares, but this isn't evidence of a persistent, sustained block.
