# Tier 2 post-fix check — VA 2026, 250-bill random sample, 2026-08-03

Re-run of the standalone `--tier2` check with the vote-tally date/motion_text matching fix
(PR #73) in place:

```
python3 quality_check.py --tier2 va 2026 --tier2-limit 250 --tier2-random
```

Part of a fresh sweep re-checking every jurisdiction from today's original 500-bill sweep now
that the vote-comparison fix is applied. VA 2026 had the lowest pass rate and largest warning
count of any jurisdiction in the original sweep (254 warnings), driven mostly by a structural
`latest_action` pattern the fix doesn't target, plus 148 "first vote counts differ" it does.

## Result

**1573/1679 checks passed (93.7%) | 98 warnings | 8 failures | 0 skipped**

Pass rate improved from 83.8% (original) to 93.7%. All 8 failures are transient live-API errors.

## Warnings: down from 254 to 98, but the residual vote-tally cases surfaced something new

| Warning | Original (500 bills) | This run (250 bills) |
|---|---|---|
| `latest_action differs` (structural chaptering pattern) | 76 | 44 |
| "first vote counts differ" / vote tally differs | 148 | 36 |
| title differs | 16 | 9 |
| "local has MORE votes than live" | 14 | 9 |

`latest_action` and title counts track proportionally with the original run — unaffected by this
fix, as expected (that's VA's separate, structural chaptering issue, not a comparison bug).

## The 36 remaining vote-tally warnings split into two distinct groups

**20 of 36 are a single new finding, not 20 separate bugs:** every one is on the *same date*,
**2026-02-17**, and shows the *same shape* — local's "yes" count is consistently **one vote
higher** than live's, with every other tally (no/abstain/not voting) matching exactly (e.g. HB
1030, HB 1103, HB 1231, HB 1292, HB 1334, HB 1337, HB 1528, HB 200: all local
`{yes:97,no:0,not_voting:3}` vs. live `{yes:96,no:0,not_voting:3}`). This is almost certainly one
shared roll call — Virginia's House runs bills through en-bloc "Block Vote" passage days where
dozens of bills share a single floor vote — and one side is missing (or has an extra) single
member's vote on that shared roll call, applied identically across every bill in the block. This
reads as one real discrepancy affecting ~20 bills at once, not 20 independent ones. Not
root-caused further here (would need to identify which specific member's vote is missing/extra on
2026-02-17 and cross-check against VA's own record) — but VA HB 973, called out as a "genuine"
finding in earlier spot-checks, is part of this exact pattern (94 vs 93), not an isolated case.

**16 of 36 (8 bill/date groups) are the already-documented same-date reciprocal-swap artifact** —
HB 1400, HB 218, HB 330 (×2 dates), HB 346, HB 975, SB 197, SB 276 each show exactly two mismatch
lines per date with the values swapped between local and live, the same signature as VA HB 30 in
`notes/quality-check-vote-date-matching-fix-20260803.md`: multiple votes on the same day sharing
identical or blank `motion_text`, with nothing left to disambiguate them by.

## Net

The fix cuts VA's ordering-artifact warnings roughly in line with expectations, but this
250-bill re-sample also surfaced a genuinely new, real finding the original 500-bill run's larger
warning volume had buried: a likely single-vote discrepancy on VA's 2026-02-17 block-vote day,
affecting a whole batch of bills identically. Worth a follow-up look specifically at that date's
roll call, separate from the fix's own verification.

Raw log: `logs/quality-check/va_2026_tier2only_250_postfix.log` (this checkout).

## References

- `notes/va-2026-tier2-500-bill-random-sample-20260803.md` — the original 500-bill run this compares against
- `notes/quality-check-vote-date-matching-fix-20260803.md` — the fix this sweep re-verifies, including the same-date reciprocal-swap limitation
- PR #73 — the vote-tally date/motion_text matching fix
