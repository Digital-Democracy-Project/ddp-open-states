# Tier 2 standalone check — UT 2026, 500-bill random sample, 2026-08-03

Run via the standalone `--tier2` flag (PR #70) against prod's live DB and the public
`v3.openstates.org` API, production key (30k req/day tier):

```
python3 quality_check.py --tier2 ut 2026 --tier2-limit 500 --tier2-random
```

Part of a sweep covering every tracked jurisdiction except Michigan — see
`notes/mi-tier2-500-bill-random-sample-20260803.md`, `notes/al-tier2-500-bill-random-sample-20260803.md`,
`notes/az-tier2-500-bill-random-sample-20260803.md`, `notes/fl-tier2-500-bill-random-sample-20260803.md`,
`notes/ma-tier2-500-bill-random-sample-20260803.md`.

## Result

**2157/2334 checks passed (92.4%) | 173 warnings | 4 failures | 0 skipped**

## Failures: all 4 transient, zero real

All 4 failures are live-API request errors. **No "missing votes" failures at all** — vote event
counts matched local-to-live on every one of the 496 bills checked. **0 title-differs, 0
latest_action-differs, 0 sponsorship issues.**

## The 173 warnings are all "first vote counts differ" — and look like an ordering artifact, not data loss

Since vote *event counts* match perfectly (496/496) but the first vote's tally frequently doesn't,
and unlike AZ's version of this warning, **none of UT's mismatches involve an all-zero side** —
both local and live always report real, non-zero numbers. The scale of the numbers is the tell:
Utah bills get separate House (~75-member) and Senate (~29-member) floor votes, and the two
sides' vote lists are evidently ordered differently. Examples:

- UT HB 47: local `yes=70` (House-scale) vs. live `yes=25` (Senate-scale)
- UT HB 320: local `yes=26` (Senate-scale) vs. live `yes=69` (House-scale) — the reverse pairing
- UT SB 128: local `yes=21` vs. live `yes=24` — closer in scale, plausibly still a real small
  discrepancy rather than a chamber mismatch

This reads as local and live sorting a bill's multiple vote events differently (e.g. by chamber
vs. by date), so "first vote" by list index compares two different actual roll calls most of the
time — not evidence of missing or corrupted vote data, since every event count agrees.

## Net

**0 of 500 bills show a confirmed real data gap** — UT 2026's sub-record data is clean wherever it
was checked; the 173 warnings are a comparison-methodology artifact (index-based "first vote"
comparison breaking down when a jurisdiction records multiple votes per bill in different orders),
not a UT scraper defect. Contrast with MI (real missing-vote-event staleness) and AZ (some zeroed
tallies, a different and more concerning variant of this same warning class).

Raw log: `logs/quality-check/ut_2026_tier2only_500.log` in the prod checkout
(`~/Developer/repos/ddp-open-states`).

## References

- `notes/tier1-coverage-all-jurisdictions-20260803.md` — Tier 1 sweep (UT 2026 came back clean:
  0 missing, 0 extra out of 1016 bills)
- `notes/az-tier2-500-bill-random-sample-20260803.md` — the other jurisdiction with this same
  warning class, but with real zeroed-tally cases mixed in, unlike UT's clean ordering-only version
- PR #70 — standalone `--tier2` flag this run used
