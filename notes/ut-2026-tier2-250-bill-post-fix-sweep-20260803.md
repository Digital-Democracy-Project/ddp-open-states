# Tier 2 post-fix check — UT 2026, 250-bill random sample, 2026-08-03

Re-run of the standalone `--tier2` check with the vote-tally date/motion_text matching fix
(PR #73) in place:

```
python3 quality_check.py --tier2 ut 2026 --tier2-limit 250 --tier2-random
```

Part of a fresh sweep re-checking every jurisdiction from today's original 500-bill sweep now
that the vote-comparison fix is applied. UT 2026 is a strong test of this fix: its original
writeup had 173 warnings, *all* "first vote counts differ," already diagnosed there as a pure
comparison-ordering artifact (Utah's House/Senate vote lists sorted differently between local and
live, no missing or corrupted data).

## Result

**1393/1405 checks passed (99.1%) | 0 warnings | 12 failures | 0 skipped**

## Failures: all transient

All 12 failures are live API errors (timeout/`429`/`502`) — no data-based failures.

## Net

**0 warnings.** The original run's entire 173-warning "first vote counts differ" category is
completely gone — exactly what the earlier diagnosis predicted, since UT 2026's case was
characterized as a pure ordering artifact with no zeroed or missing tallies underneath. This is
the cleanest possible confirmation of the date/motion_text matching fix: a jurisdiction that had
zero real data-quality issues and a very large false-positive warning count now shows neither.

Raw log: `logs/quality-check/ut_2026_tier2only_250_postfix.log` (this checkout).

## References

- `notes/ut-2026-tier2-500-bill-random-sample-20260803.md` — the original 500-bill run this compares against
- `notes/quality-check-vote-date-matching-fix-20260803.md` — the fix this sweep re-verifies
- PR #73 — the vote-tally date/motion_text matching fix
