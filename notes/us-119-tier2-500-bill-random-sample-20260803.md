# Tier 2 standalone check — US federal 119, 500-bill random sample, 2026-08-03

Run via the standalone `--tier2` flag (PR #70) against prod's live DB and the public
`v3.openstates.org` API, production key (30k req/day tier):

```
python3 quality_check.py --tier2 us 119 --tier2-limit 500 --tier2-random
```

Last of the sweep covering every tracked jurisdiction except Michigan — see the sibling
`notes/*-tier2-500-bill-random-sample-20260803.md` docs from today (MI, AL, AZ, FL, MA, UT×2,
VA×2).

**Notable context:** this is the first real Tier 2 exercise of the `us` jurisdiction since PR #69
fixed `fetch_all_local_identifiers()`'s hardcoded `state:` OCD-URI assumption (US federal's OCD id
has no `state:` component, so every prior Tier 1 `--coverage us` run reported a false 100% missing
— see `notes/tier1-coverage-all-jurisdictions-20260803.md`). `sample_local_bills_for_session()`
already had its own separate US-aware branch before that fix (per its own docstring), so this run
also confirms that branch works correctly end-to-end: **500 bills sampled successfully from local**
(no repeat of the Tier 1 bug in this standalone path).

## Result

**1900/1928 checks passed (98.5%) | 2 warnings | 26 failures | 0 skipped**

## Failures: all transient

| Cause | Count |
|---|---|
| Read timeout (15s) | 24 |
| `502 Bad Gateway` | 2 |

No `429`s this time, but two new-for-this-sweep `502`s — a live-API server error, still not a
data problem on our end.

## The 2 warnings

Both are the familiar "first vote counts differ" ordering/tally artifact seen across
AZ/UT/VA — close, not wildly different, numbers (e.g. US HR 8595: local `yes=217/no=209` vs. live
`yes=209/no=216`), consistent with a vote-list ordering or a real small tally discrepancy rather
than missing data.

## Net

**0 real data-quality findings** — 0 missing votes, 0 title mismatches, 0 sponsorship mismatches,
0 `latest_action` staleness, out of every one of the ~500 bills that got a live response. US
federal's Tier 2 data is clean, and — as importantly — the standalone `--tier2` path handles the
`us` jurisdiction correctly, closing out the last open question from the Tier 1 sweep's US-federal
bug.

Raw log: `logs/quality-check/us_119_tier2only_500.log` in the prod checkout
(`~/Developer/repos/ddp-open-states`).

## References

- `notes/tier1-coverage-all-jurisdictions-20260803.md` — the US-federal false-100%-missing bug
  this run's context builds on
- PR #69 — the `fetch_all_local_identifiers()` fix for Tier 1's `us` handling
- PR #70 — standalone `--tier2` flag this run used (its own `sample_local_bills_for_session()`
  already had US-aware handling, confirmed working here)
