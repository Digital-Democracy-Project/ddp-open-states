# Tier 2 post-fix check — MA 194th, 250-bill random sample, 2026-08-03

Re-run of the standalone `--tier2` check with the vote-tally date/motion_text matching fix
(PR #73) in place:

```
python3 quality_check.py --tier2 ma 194th --tier2-limit 250 --tier2-random
```

Part of a fresh sweep re-checking every jurisdiction from today's original 500-bill sweep now
that the vote-comparison fix is applied. Same scope note as the original MA writeup applies: this
samples straight from MA's local DB and says nothing about MA 194th's much larger Tier 1
identifier-coverage gap (see `notes/tier1-coverage-all-jurisdictions-20260803.md`).

## Result

**934/956 checks passed (97.7%) | 6 warnings | 16 failures | 0 skipped**

## Failures: 15 transient, 1 a real gap

| Cause | Count | Real? |
|---|---|---|
| `429 Too Many Requests` | 15 | No — transient |
| **local is MISSING votes vs live** | **1** | **Yes** |

## Warnings: "first vote counts differ" is gone; one honest new-shaped warning appears

| Warning | Original (500 bills) | This run (250 bills) |
|---|---|---|
| "first vote counts differ" (ordering artifact) | 3 | **0** |
| `latest_action differs` | 8 | 4 |
| "local has MORE votes than live (our fix not merged?)" | 1 | 1 |
| **"no shared vote dates to compare tallies against"** | n/a (new check) | 1 |

The ordering-artifact warning is fully gone, consistent with FL and AZ. One bill (MA H 5501) now
surfaces the fix's honest-failure-mode warning: local's only vote is dated 2026-05-21, live's only
vote is dated 2026-05-28 — no shared date exists to compare against at all, so the fix correctly
declines to guess rather than silently comparing two different votes. Worth a manual look (is one
side's date wrong, or are these genuinely two different votes one side is missing?) but not
re-diagnosed here.

## Net

Same story as FL/AZ: the ordering artifact this fix targets is fully resolved, and the one new
warning type it introduces (no shared dates) is doing exactly its intended job — flagging a case
honestly instead of hiding it behind a wrong comparison.

Raw log: `logs/quality-check/ma_194th_tier2only_250_postfix.log` (this checkout).

## References

- `notes/ma-tier2-500-bill-random-sample-20260803.md` — the original 500-bill run this compares against
- `notes/quality-check-vote-date-matching-fix-20260803.md` — the fix this sweep re-verifies
- PR #73 — the vote-tally date/motion_text matching fix
