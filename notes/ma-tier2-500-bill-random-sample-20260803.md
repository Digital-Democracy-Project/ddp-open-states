# Tier 2 standalone check — MA 194th, 500-bill random sample, 2026-08-03

Run via the standalone `--tier2` flag (PR #70) against prod's live DB and the public
`v3.openstates.org` API, production key (30k req/day tier):

```
python3 quality_check.py --tier2 ma 194th --tier2-limit 500 --tier2-random
```

Part of a sweep covering every tracked jurisdiction except Michigan — see
`notes/mi-tier2-500-bill-random-sample-20260803.md`, `notes/al-tier2-500-bill-random-sample-20260803.md`,
`notes/az-tier2-500-bill-random-sample-20260803.md`, `notes/fl-tier2-500-bill-random-sample-20260803.md`.

**Important scope note:** this samples 500 bills straight from MA's *local* DB — it says nothing
about MA 194th's much larger Tier 1 identifier-coverage gap (7,510 of 18,604 live bills, ~40%,
suspected HD/SD docket-duplication artifact, unconfirmed — see
`notes/tier1-coverage-all-jurisdictions-20260803.md`). This run only checks sub-record agreement
on bills that *do* exist locally; it doesn't touch that open question at all.

## Result

**1832/1889 checks passed (97.0%) | 12 warnings | 45 failures | 0 skipped**

## Failures: mostly transient, 7 are real

| Cause | Count | Real? |
|---|---|---|
| `429 Too Many Requests` | 38 | No — transient |
| **local is MISSING votes vs live** | **7** | **Yes** |

One of the 7 is a large single-bill gap worth flagging on its own: **MA H 5500 — local shows 0
votes, live shows 34.**

## The 12 warnings

- **8 — `latest_action differs`**, all one-directional (local behind live), e.g. local="hearing
  scheduled for 06/23/2026..." vs. live="read second and ordered to a third reading"; local="enacted
  and laid before the governor" vs. live="signed by the governor, chapter 112 of the acts of...".
  Ordinary scrape-cadence lag, same shape as every other jurisdiction checked so far — nothing MA-
  specific about it.
- **3 — "first vote counts differ"** — likely downstream of the missing-votes gap above (index
  mismatch when list lengths differ).
- **1 — "local has MORE votes than live (our fix not merged?)"** — same pattern flagged as
  unexpectedly present in FL's writeup; here it's a single instance, not worth more than noting.
- **0 title, 0 sponsorship-count issues.**

## Net

**8 of 500 bills (1.6%) show a real vote/action disagreement** — a much lower real-issue rate than
MI (8.4%), FL (7.8%), or AZ (~1.25% latest_action + a much larger 23.6% vote-tally issue). MA's
sub-record data, for bills that exist locally, is largely trustworthy; the open question remains
Tier 1's much larger identifier-level gap, untouched by this run.

Raw log: `logs/quality-check/ma_194th_tier2only_500.log` in the prod checkout
(`~/Developer/repos/ddp-open-states`).

## References

- `notes/tier1-coverage-all-jurisdictions-20260803.md` — MA's much larger, separate Tier 1 gap
- `notes/mi-tier2-500-bill-random-sample-20260803.md`, `notes/az-tier2-500-bill-random-sample-20260803.md`,
  `notes/fl-tier2-500-bill-random-sample-20260803.md` — other jurisdictions' Tier 2 findings so far
- PR #70 — standalone `--tier2` flag this run used
