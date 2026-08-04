# Tier 2 standalone check — FL 2026, 500-bill random sample, 2026-08-03

Run via the standalone `--tier2` flag (PR #70) against prod's live DB and the public
`v3.openstates.org` API, production key (30k req/day tier):

```
python3 quality_check.py --tier2 fl 2026 --tier2-limit 500 --tier2-random
```

Part of a sweep covering every tracked jurisdiction except Michigan — see
`notes/mi-tier2-500-bill-random-sample-20260803.md` (MI), `notes/al-tier2-500-bill-random-sample-20260803.md`
(AL, clean), `notes/az-tier2-500-bill-random-sample-20260803.md` (AZ).

## Result

**1988/2137 checks passed (93.0%) | 112 warnings | 37 failures | 0 skipped**

## Failures: mostly transient, but 14 are a real gap

| Cause | Count | Real? |
|---|---|---|
| `429 Too Many Requests` | 21 | No — transient |
| Read timeout (15s) | 2 | No — transient |
| **local is MISSING votes vs live** | **14** | **Yes** — local has 0 votes recorded where live has 1–3 |

## The 112 warnings are almost all vote-record disagreements, in both directions

- **25 warnings — "local has MORE votes than live (our fix not merged?)"**: `compare_bills()`'s own
  code comment (`quality_check.py:317`) says this pattern is *expected* for UT/MI specifically —
  "we have fixes not yet merged upstream" to the public API. Seeing it show up 25 times for FL is
  new: either FL has a similar unmerged local fix nobody's documented yet, or this is a local-side
  vote-duplication artifact distinct from UT/MI's known case. Examples: FL HB 559 (local=4,
  live=2), FL HB 1175 (local=6, live=3), FL HB 1137 (local=6, live=2). Not resolved here — flagging
  for follow-up, not diagnosed.
- **87 warnings — "first vote counts differ":** very likely a downstream artifact of the two
  count-mismatch patterns above — when local's and live's vote lists are different lengths (either
  direction), comparing "first vote" by list index compares two different actual roll calls.
- **0 latest_action, 0 title, 0 sponsorship-count issues** — every one of the 477 bills that
  completed matched exactly on those three fields. FL's disagreement here is entirely
  vote-record-shaped, not a general staleness problem like MI's.

## Net

**39 of 500 bills (7.8%) show a real vote-record disagreement** (14 missing + 25 more-than-live),
split across two different directions rather than one clear pattern — unlike MI (one-directional
staleness) or AZ (zeroed/misordered tallies with matching event counts). This is consistent with
Tier 1's earlier, smaller finding for FL (34 of 1931 bills, ~1.8%, missing entirely at the
identifier level) — Tier 2 surfaces a larger, vote-record-specific gap underneath bills that *do*
exist in both.

Raw log: `logs/quality-check/fl_2026_tier2only_500.log` in the prod checkout
(`~/Developer/repos/ddp-open-states`).

## References

- `notes/tier1-coverage-all-jurisdictions-20260803.md` — Tier 1 sweep (FL: 34 of 1931 missing,
  ~1.8%, not investigated further there)
- `notes/mi-tier2-500-bill-random-sample-20260803.md`, `notes/az-tier2-500-bill-random-sample-20260803.md`
  — the other two jurisdictions with real Tier 2 findings so far, both different failure shapes
- PR #70 — standalone `--tier2` flag this run used
