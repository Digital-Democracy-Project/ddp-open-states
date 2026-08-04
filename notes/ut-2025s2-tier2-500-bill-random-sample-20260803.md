# Tier 2 standalone check — UT 2025S2, full-session sample, 2026-08-03

Run via the standalone `--tier2` flag (PR #70) against prod's live DB and the public
`v3.openstates.org` API, production key:

```
python3 quality_check.py --tier2 ut 2025S2 --tier2-limit 500 --tier2-random
```

Part of a sweep covering every tracked jurisdiction except Michigan (see the sibling `*-tier2-500-bill-*`
notes docs from today). UT 2025S2 is a tiny special session — only 5 bills exist locally in total
(matches the Tier 1 sweep's finding: 5 live, 5 local, 0 missing) — so `--tier2-limit 500` samples
the entire session, not a 500-of-many subset.

## Result

**24/25 checks passed (96%) | 1 warning | 0 failures | 0 skipped**

## The one warning

`UT SJR 201`: "first vote counts differ" — `local={'yes': 22, 'no': 7, 'other': 0}` vs.
`live={'yes': 58, 'no': 12, 'other': 5}`. Same pattern as UT 2026's writeup: vote event counts
match (2 on both sides), but the two sides evidently order multi-vote lists differently, so "first
vote" compares two different actual roll calls. The `22/7/0` figure also shows up as the correctly-
matched first vote for two other bills in this same session (SB 2001, SB 2002) — consistent with
several of these bills sharing a companion/concurrent vote, and SJR 201 simply being the one case
in this tiny sample where local and live picked different votes as "first."

## Net

Clean session — no real data-quality issues, 0 failures, and the sole warning is the same
comparison-ordering artifact already characterized in UT 2026's writeup, not a new finding.

Raw log: `logs/quality-check/ut_2025S2_tier2only_500.log` in the prod checkout
(`~/Developer/repos/ddp-open-states`).

## References

- `notes/tier1-coverage-all-jurisdictions-20260803.md` — Tier 1 (UT 2025S2: 0 missing, 0 extra
  out of 5 bills)
- `notes/ut-2026-tier2-500-bill-random-sample-20260803.md` — same jurisdiction, main 2026 session,
  same vote-ordering artifact at larger scale
- PR #70 — standalone `--tier2` flag this run used
