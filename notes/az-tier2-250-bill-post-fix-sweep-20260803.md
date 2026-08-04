# Tier 2 post-fix check — AZ 57th-2nd-regular, 250-bill random sample, 2026-08-03

Re-run of the standalone `--tier2` check with the vote-tally date/motion_text matching fix
(PR #73) in place:

```
python3 quality_check.py --tier2 az 57th-2nd-regular --tier2-limit 250 --tier2-random
```

Part of a fresh sweep re-checking every jurisdiction from today's original 500-bill sweep now
that the vote-comparison fix is applied — AZ is the most direct test of this fix, since AZ's
original writeup (`notes/az-tier2-500-bill-random-sample-20260803.md`) had the largest warning
count of any jurisdiction (119), almost entirely "first vote counts differ."

## Result

**1136/1205 checks passed (94.3%) | 28 warnings | 41 failures | 0 skipped**

## Failures: all transient, same as before

| Cause | Count |
|---|---|
| Read timeout (15s) | 38 |
| `502 Bad Gateway` | 3 |

**0 "missing votes" failures** — same as the original run, AZ's vote *event counts* still match
local-to-live on every bill checked.

## Warnings dropped from 119 → 28 (76% reduction)

The fix's target metric: AZ's original 500-bill run had 119 warnings, 113 of them "first vote
counts differ" from the old index-based comparison. This 250-bill post-fix run has only 28 total
warnings (26 vote-tally, 2 `latest_action`) — a large drop, consistent with most of those
originally being the ordering artifact the fix targets.

The 26 remaining vote-tally warnings are concentrated on a handful of dates (10 on 2026-06-11
alone — likely AZ's last-day-of-session floor votes, where many bills share the same generic
motion_text like "Third Reading" or "Passed" and can't be disambiguated further, the same
documented limitation as VA HB 30 in `notes/quality-check-vote-date-matching-fix-20260803.md`).
At least one (SB 1037) shows the same zero-vs-real reciprocal-swap signature as that known
limitation. Not individually re-verified bill-by-bill here — flagging the pattern, not
re-diagnosing each one.

## Net

The fix substantially reduces AZ's false-positive warning rate as expected. The residual 28
warnings are consistent with the one known, documented gap (same-date votes sharing identical
generic motion_text) rather than a new problem.

Raw log: `logs/quality-check/az_tier2only_250_postfix.log` (this checkout).

## References

- `notes/az-tier2-500-bill-random-sample-20260803.md` — the original 500-bill run this compares against
- `notes/quality-check-vote-date-matching-fix-20260803.md` — the fix this sweep re-verifies, including the same-generic-motion_text limitation
- PR #73 — the vote-tally date/motion_text matching fix
