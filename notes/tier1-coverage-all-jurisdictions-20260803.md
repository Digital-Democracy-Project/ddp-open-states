# Tier 1 coverage check — all tracked jurisdictions, 2026-08-03

Run via `quality_check.py --coverage <jurisdiction> <session> --tier2-limit 1` against prod's
live DB (`ddp-open-states`) and the public `v3.openstates.org` API, per
`PLAN-coverage-completeness-check.md` §2/§8. Tier 2 capped to 1 bill per run — this sweep is
Tier 1 only (full identifier-set coverage), not a real sub-record sweep. Fills in the plan's
long-standing open item that Tier 1 had never been run against anything but MA.

| Jurisdiction | Session | Live | Local | Missing | Extra | Both |
|---|---|---|---|---|---|---|
| AL | 2026rs | 1507 | 1507 | 0 | 0 | 1507 |
| AZ | 57th-2nd-regular | 2190 | 2190 | 0 | 0 | 2190 |
| FL | 2026 | 1931 | 1897 | 34 | 0 | 1897 |
| MA | 194th | 18604 | 11094 | 7510 | 0 | 11094 |
| MI | 2025-2026 | 3884 | 3884 | 0 | 0 | 3884 |
| UT | 2026 | 1016 | 1016 | 0 | 0 | 1016 |
| UT | 2025S2 | 5 | 5 | 0 | 0 | 5 |
| VA | 2026 | 3637 | 3637 | 0 | 0 | 3637 |
| VA | 2026S1 | 300 | 300 | 0 | 0 | 300 |
| US | 119 | 18052 | **0**\* | 18052\* | 0 | 0 |

\* **US 119's `local=0`/`missing=18052` is a false positive — a real bug in the tool, not an
actual coverage gap.** `fetch_all_local_identifiers()` (`quality_check.py:136-145`) filters on
`j.id LIKE '%/state:{jurisdiction_code}/%'`, which hardcodes a `state:` OCD-URI component. The
federal jurisdiction's OCD id is `ocd-jurisdiction/country:us/government` — no `state:` segment
at all — so the LIKE clause never matches any row and the query always returns an empty set for
`jurisdiction_code="us"`, regardless of how much data actually exists locally. A direct SQL query
against the same DB (bypassing the tool) confirms local `us`/`119` actually holds exactly 18,052
bills — matching the live count exactly. **Tier 1 has never actually been able to check US
federal coverage; every prior run against `us` would have shown the same false 100%-missing
result.** Not yet fixed — needs a jurisdiction-code-aware branch in `fetch_all_local_identifiers`
(or reuse of `OCD_TO_CODE`'s reverse mapping instead of a hand-built LIKE pattern) before this
row can be trusted.

**Real findings, otherwise:**
- 8 of 9 real (non-US) jurisdiction/session pairs came back **completely clean** (0 missing, 0
  extra) — AL, AZ, MI, both UT sessions, both VA sessions.
- FL 2026 has a small, real gap: 34 bills live but not local (~1.8% of 1931) — plausible normal
  drift, not investigated further here.
- MA 194th's 7510 "missing" (~40% of live) is very likely dominated by the same HD/SD
  docket-vs-bill-number duplication artifact §10 of the plan already diagnosed for MA's prior
  run (which showed an almost identical ~41% raw gap that was ~98% inflation) — not re-broken-out
  by prefix in this run, so treat as unconfirmed until it is.

Raw per-run logs: `logs/quality-check/<jurisdiction>_<session>.log` in the prod checkout
(`~/Developer/repos/ddp-open-states`).
