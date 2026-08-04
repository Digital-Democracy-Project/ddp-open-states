# Tier 2 post-fix check — MI 2025-2026, 250-bill random sample, 2026-08-03

Re-run of the standalone `--tier2` check with the vote-tally date/motion_text matching fix
(PR #73) in place:

```
python3 quality_check.py --tier2 mi 2025-2026 --tier2-limit 250 --tier2-random
```

Part of a fresh sweep re-checking every jurisdiction from today's original 500-bill sweep now
that the vote-comparison fix is applied. MI's original writeup was the first to surface MI's
one-directional staleness pattern (local consistently behind live), tied to its WAF-blocking
history (OPEN-19/21/22/23).

## Result

**974/1010 checks passed (96.4%) | 16 warnings | 20 failures | 0 skipped**

## Failures: 17 transient, 3 a real gap

| Cause | Count | Real? |
|---|---|---|
| Live API error (timeout/429) | 17 | No — transient |
| **local is MISSING votes vs live** | **3** | **Yes** |

Proportionally consistent with the original run's 17 of 500.

## Warnings: down from 29 "first vote counts differ" to 4 (all appear genuine, not artifacts)

| Warning | Original (500 bills) | This run (250 bills) |
|---|---|---|
| "first vote counts differ" (ordering artifact) | 29 | 4 (renamed "vote tally differs on {date}") |
| `latest_action differs` | 26 | 10 |
| title differs | 5 | 2 |
| sponsorship count off by 1 | 1 | 0 |

The 4 remaining vote-tally warnings (MI SB 616, SB 478, SB 595×2) each show a single mismatch per
bill/date, not the reciprocal zero-vs-real swap signature that marks a same-date ordering
artifact (see `notes/quality-check-vote-date-matching-fix-20260803.md`) — these look like genuine
tally disagreements, consistent with MI's known one-directional staleness pattern rather than a
comparison bug. Not independently re-verified against MI's scrape logs here.

## Net

Same shape as AZ/FL/MA: the ordering-artifact warning category shrinks sharply (29 → 4), and the
`latest_action`/title staleness this fix doesn't touch persists at a proportionally consistent
rate, still pointing the same direction (local behind live) as the original finding.

Raw log: `logs/quality-check/mi_2025-2026_tier2only_250_postfix.log` (this checkout).

## References

- `notes/mi-tier2-500-bill-random-sample-20260803.md` — the original 500-bill run this compares against
- `notes/quality-check-vote-date-matching-fix-20260803.md` — the fix this sweep re-verifies
- PR #73 — the vote-tally date/motion_text matching fix
- Jira: OPEN-19, OPEN-21, OPEN-22, OPEN-23 — MI's WAF-blocking history behind the staleness pattern
