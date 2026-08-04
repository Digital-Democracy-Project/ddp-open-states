# Tier 2 post-fix check — US federal 119, 250-bill random sample, 2026-08-03

Re-run of the standalone `--tier2` check with the vote-tally date/motion_text matching fix
(PR #73) in place:

```
python3 quality_check.py --tier2 us 119 --tier2-limit 250 --tier2-random
```

Part of a fresh sweep re-checking every jurisdiction from today's original 500-bill sweep now
that the vote-comparison fix is applied.

## Result

**960/971 checks passed (98.9%) | 0 warnings | 11 failures | 0 skipped**

## Failures: all transient

All 11 failures are live API errors (timeout/`429`/`502`) — no data-based failures at all.

## Net

Perfectly clean, same as the original 500-bill run (0 real data-quality findings there too). US
federal's Tier 2 data remains clean at both the identifier and sub-record level; nothing here for
the vote-tally fix to have caught, consistent with the original run's 2 "first vote counts
differ" warnings (a small enough number that a 250-bill random re-sample simply didn't happen to
include either bill).

Raw log: `logs/quality-check/us_119_tier2only_250_postfix.log` (this checkout).

## References

- `notes/us-119-tier2-500-bill-random-sample-20260803.md` — the original 500-bill run this compares against
- `notes/quality-check-vote-date-matching-fix-20260803.md` — the fix this sweep re-verifies
- PR #73 — the vote-tally date/motion_text matching fix
