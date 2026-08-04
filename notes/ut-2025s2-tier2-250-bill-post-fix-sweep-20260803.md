# Tier 2 post-fix check — UT 2025S2, full-session sample, 2026-08-03

Re-run of the standalone `--tier2` check with the vote-tally date/motion_text matching fix
(PR #73) in place:

```
python3 quality_check.py --tier2 ut 2025S2 --tier2-limit 250 --tier2-random
```

UT 2025S2 is a tiny special session — only 5 bills exist locally in total — so `--tier2-limit
250` samples the entire session, same as the original 500-bill run did.

## Result

**30/30 checks passed (100%) | 0 warnings | 0 failures | 0 skipped**

## Net

Perfectly clean, no failures at all this time (the original run's sole warning — UT SJR 201's
"first vote counts differ," already diagnosed there as a vote-ordering artifact between two
companion votes — is gone). Confirms the fix at the smallest possible scale in today's sweep.

Raw log: `logs/quality-check/ut_2025S2_tier2only_250_postfix.log` (this checkout).

## References

- `notes/ut-2025s2-tier2-500-bill-random-sample-20260803.md` — the original run this compares against
- `notes/quality-check-vote-date-matching-fix-20260803.md` — the fix this sweep re-verifies
- PR #73 — the vote-tally date/motion_text matching fix
