# QA baseline — NC 2025, OPEN-231 Stage 3, 2026-08-31

First-ever QA baseline for North Carolina, Phase 1's pilot state (OPEN-230). Run after the
first supervised production scrape (Stage 2) and after fixing the people-load gap that scrape
surfaced (people were never loaded for a never-before-onboarded state — see below).

```
python3 quality_check.py --coverage nc 2025 --tier2-limit 250 --tier2-random
```

## Result

**Tier 1 coverage: 2338/2338 (100%) — 0 missing, 0 extra.**
**Tier 2 (250-bill random sample): 1081/1081 checks passed (100%) | 0 warnings | 0 failures | 0 skipped.**

One transient `page 117 failed (HTTPError)` on the live API fetch, resolved on retry 3/3 — not a
real gap, noted for completeness.

Raw log: `logs/quality-check/nc_2025.log` (this checkout).

## The gap Tier 1/Tier 2 alone would have hidden

Both of the checks above compare *counts* (bill identifiers, vote-event counts, sponsorship
counts) against the live API — exactly the blind spot the plan's own §4.5 addendum names (a vote
event with the right tally and an unresolvable voter matches on count and is wrong in the only
way that reaches a scorecard). Before the people-load fix, every single sponsorship and vote in
NC's data resolved to nobody, and the checks above still would have passed 100% on count alone.

Per that addendum, the additional required check: what fraction of `personvote`/`billsponsorship`
rows for the sampled session carry a name but no resolved person.

| | Before people load | After `os-people to-database nc` + re-import |
|---|---|---|
| `personvote` unresolved | 72,058 / 72,058 (100%) | 611 / 72,058 (0.85%) |
| `billsponsorship` (person entities) unresolved | 26,095 / 26,095 (100%) | 898 / 26,095 (3.4%) |

Root cause of the 100%-unresolved state: NC was never in `run-people-refresh.sh`'s hardcoded
state list, so its 170 legislator records existed in the `people/` repo but were never loaded
into the production database — the same "hardcoded list never updated for a new state" bug
class as the manual scrape-trigger endpoint (flagged separately, not yet fixed). Fixed live by
running `os-people to-database nc` then re-running `os-update nc --import` (confirmed via code
read: sponsorships/votes aren't in the importers' `merge_related`, so a plain re-import
re-resolves and rewrites them without needing a re-scrape).

Both resolution rates now clear the plan's 95% sign-off bar (99.15% and 96.6% respectively).

## Remainder, itemized

Per §4.5's exception language — the remainder is named and explained, not zero:

- **481 unresolved votes, `voter_name='Helfrich'`** — a real legislator (Beth Gardner Helfrich)
  whose people-record name variants don't include the bare surname NC's roll-call pages use.
  **OPEN-233** (people-data alias fix).
- **130 unresolved votes, `voter_name='JohnLowery'`** — a real legislator (John Lowery) whose
  name loses its internal space to a scraper bug (`scrape_votes()` strips all spaces from the
  row before splitting names, not just the separators). **OPEN-234** (scraper code fix).

No other names account for a meaningful share of either remainder.

## Sign-off

**Stage 3 passes.** Tier 1/Tier 2 clear their thresholds outright; the additional
voter/sponsor-resolution check clears its bar with a fully itemized, ticketed remainder (OPEN-233,
OPEN-234) rather than an unexplained gap. Recommending NC proceed to Stage 4.
