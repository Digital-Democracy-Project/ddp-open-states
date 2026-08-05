# Tier 2 post-fix check — FL 2026, 250-bill random sample, 2026-08-03

Re-run of the standalone `--tier2` check with the vote-tally date/motion_text matching fix
(PR #73) in place:

```
python3 quality_check.py --tier2 fl 2026 --tier2-limit 250 --tier2-random
```

Part of a fresh sweep re-checking every jurisdiction from today's original 500-bill sweep now
that the vote-comparison fix is applied.

## Result

**1188/1223 checks passed (97.1%) | 18 warnings | 17 failures | 0 skipped**

## Failures: 8 transient, 9 a real gap (unchanged from before the fix)

| Cause | Count | Real? |
|---|---|---|
| Read timeout (15s) | 8 | No — transient |
| **local is MISSING votes vs live** | **9** | **Yes** |

The fix doesn't touch this check (vote *event count*, not tally) — 9 real missing-vote bills out
of 250 is proportionally consistent with the original run's 14 of 500.

## Warnings: "first vote counts differ" is fully gone — 0 this run

The fix's target metric, direct comparison to the original 500-bill run:

| Warning | Original (500 bills) | This run (250 bills) |
|---|---|---|
| "first vote counts differ" (ordering artifact) | 87 | **0** |
| "local has MORE votes than live (our fix not merged?)" | 25 | 18 |

The ordering-artifact warning category the fix targets is completely gone in this sample — every
one of the 250 bills' shared vote dates now compares cleanly. The 18 remaining warnings are all
"local has MORE votes than live," a separate, real pattern (local recorded more vote events than
the live API has) that this fix doesn't address and was never meant to — it's an event-count
question, not a tally-comparison one.

**Resolved 2026-08-05, OPEN-27**: the "local has MORE votes than live" pattern is a genuine
local-only fix (`_FLHouseWAFSource`, flhouse.gov WAF session-cookie expiry dropping House
committee votes past ~1hr into any long FL scrape), not duplication — see
`notes/fl-tier2-more-votes-than-live-diagnosis-20260805.md`.

## Net

Clean confirmation of the fix: the artifact it targets (0 of 250) is fully resolved, while the
two genuinely separate, real FL issues (missing votes, "more votes than live") persist at roughly
the same proportional rate as the original 500-bill run — exactly the expected outcome.

Raw log: `logs/quality-check/fl_2026_tier2only_250_postfix.log` (this checkout).

## References

- `notes/fl-tier2-500-bill-random-sample-20260803.md` — the original 500-bill run this compares against
- `notes/quality-check-vote-date-matching-fix-20260803.md` — the fix this sweep re-verifies
- PR #73 — the vote-tally date/motion_text matching fix
