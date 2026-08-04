# Tier 2 post-fix check — AL 2026rs, 250-bill random sample, 2026-08-03

Re-run of the standalone `--tier2` check with the vote-tally date/motion_text matching fix
(PR #73) in place, at a smaller 250-bill sample size:

```
python3 quality_check.py --tier2 al 2026rs --tier2-limit 250 --tier2-random
```

Part of a fresh sweep re-checking every jurisdiction from today's original 500-bill sweep
(`notes/*-tier2-500-bill-random-sample-20260803.md`) now that the vote-comparison fix is applied.

## Result

**1000/1000 checks passed (100%) | 0 warnings | 0 failures | 0 skipped**

## Net

Perfectly clean — no failures at all this run (not even the transient `429`/timeout noise the
original 500-bill AL run saw), and 0 warnings, meaning the vote-tally fix had nothing left to
catch here: AL's data was already clean at the tally level, consistent with the original sweep's
finding (0 real issues out of 500). This run is a smaller sample (250 vs. 500) so it isn't a
stronger signal than the original, just a consistent one.

Raw log: `logs/quality-check/al_2026rs_tier2only_250_postfix.log` (this checkout).

## References

- `notes/al-tier2-500-bill-random-sample-20260803.md` — the original 500-bill run (also clean)
- `notes/quality-check-vote-date-matching-fix-20260803.md` — the fix this sweep re-verifies
- PR #73 — the vote-tally date/motion_text matching fix
