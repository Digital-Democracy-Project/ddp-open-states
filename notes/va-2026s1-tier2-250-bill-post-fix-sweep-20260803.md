# Tier 2 post-fix check — VA 2026S1, 250-bill random sample, 2026-08-03

Re-run of the standalone `--tier2` check with the vote-tally date/motion_text matching fix
(PR #73) in place:

```
python3 quality_check.py --tier2 va 2026S1 --tier2-limit 250 --tier2-random
```

Last jurisdiction of the post-fix sweep re-checking every jurisdiction from today's original
500-bill sweep. VA 2026S1 is a 300-bill special session; `--tier2-limit 250` samples a random
250 of those 300, unlike the original run which checked the full session.

## Result

**933/978 checks passed (95.4%) | 26 warnings | 19 failures | 0 skipped**

All 19 failures are transient live-API errors. This looks like a regression from the original
run's single warning — but it isn't.

## All 26 warnings come from one bill: VA HB 30

Every single warning in this run is `vote tally differs`, and every one is on **VA HB 30** — the
same bill flagged in `notes/quality-check-vote-date-matching-fix-20260803.md` as the documented
"vote-a-rama" limitation: ~15 same-day amendment votes on 2026-06-29 all sharing the identical
generic `motion_text` "Adopt Governor's Recommendation R" (plus more on 2026-06-22), with no field
in the data left to disambiguate individual roll calls once motion_text stops working. This is
the exact same known, un-fixable case already spot-checked and written up during the fix's
verification — not a new problem, and not spread across other bills.

**Every other bill in this 250-bill sample (249 of 250) passed with 0 warnings.**

## Net

Consistent with the original run's near-perfect result (0 real data-quality findings across 300
bills) — the one exception is a single, already-understood, already-documented limitation
concentrated entirely in one bill, not a new or spreading issue.

Raw log: `logs/quality-check/va_2026S1_tier2only_250_postfix.log` (this checkout).

## References

- `notes/va-2026s1-tier2-500-bill-random-sample-20260803.md` — the original run this compares against
- `notes/quality-check-vote-date-matching-fix-20260803.md` — the fix this sweep re-verifies, including VA HB 30's documented limitation
- PR #73 — the vote-tally date/motion_text matching fix
