# Tier 2 standalone check — MI 2025-2026, 500-bill random sample, 2026-08-03

Run via the new standalone `--tier2` flag (`feat/quality-check-standalone-tier2`, PR #70, merged
today) against prod's live DB and the public `v3.openstates.org` API, using the production API key
(30,000 req/day tier — the 250 req/day figure in `quality_check.py`'s docstring is just the
conservative default-run target, not a hard cap):

```
python3 quality_check.py --tier2 mi 2025-2026 --tier2-limit 500 --tier2-random
```

This follows up on two earlier, smaller runs today: an interrupted 500-bill AL sweep (killed
mid-run, no summary line) and a 2-bill MI smoke test of the same `--tier2` flag (8/9 passed, one
`latest_action` warning). This is the first completed run at real sample size.

## Result

**1924/2033 checks passed (94.7%) | 61 warnings | 48 failures | 0 skipped**

## Failures are mostly transient, not data problems

Of the 48 failures, **31 never actually got compared** — the live API request itself failed:

| Cause | Count |
|---|---|
| `429 Too Many Requests` | 20 |
| Read timeout (15s) | 11 |

Both came in short bursts despite the 0.5s inter-request pacing (2 req/sec steady-state, per
`quality_check.py`'s own comment) — the live API's throttling window is apparently tighter than
that in bursts, independent of the 30k/day quota. Re-running just these 31 identifiers would give
a cleaner number.

## The other 17 failures + 61 warnings are a real, systematic finding

**17 bills: local is missing vote events live has** (e.g. local shows 1 recorded vote where live
shows 2–3). This one real bug cascades into most of the warnings below:

- **29 warnings — "first vote counts differ":** near-certainly downstream of the missing-votes
  bug above. When local's and live's vote lists are different lengths, comparing "first vote" by
  list index compares two different actual roll calls, producing wildly different yes/no/other
  counts that look like data corruption but are really an index-alignment artifact of the
  underlying missing-votes gap.
- **26 warnings — `latest_action` differs:** one-directional in every case — local is always
  *behind* live (e.g. local: "referred to committee on judiciary" / "transmitted" / "placed on
  order of third reading" vs. live: "assigned PA...with immediate effect" / "presented to
  governor..."). Local never leads live. This is staleness, not disagreement.
- **5 warnings — title differs:** most look like formatting/whitespace, but at least one
  (MI SB 293) is a real content change: local="Animals: care and treatment; restitution" vs.
  live="Animals: care and treatment; forfeiture" — worth a manual look, not dismissed as noise.
- **1 warning — sponsorship count off by one** (MI SB 1047: local=10, live=11).

**Net: 42 distinct bills out of 500 (8.4%) show real staleness**, all pointing the same direction
(local behind live on votes and/or actions). This is consistent with MI's ongoing WAF-blocking
history (OPEN-19/OPEN-21/OPEN-22/OPEN-23): if a jurisdiction's secondary/update scrapes keep
getting blocked, a bill that landed once during an initial scrape would never pick up its later
votes or status changes — exactly this pattern.

## Not yet done

- The 31 transiently-failed identifiers haven't been re-run.
- No attempt yet to correlate the 42 stale bills against MI's actual scrape-run history/logs to
  confirm they line up with known WAF-blocked windows rather than some other cause.

Raw log: `logs/quality-check/mi_2025-2026_tier2only_500.log` in the prod checkout
(`~/Developer/repos/ddp-open-states`).

## References

- `notes/tier1-coverage-all-jurisdictions-20260803.md` — the Tier 1 sweep this follows up on
- `PLAN-coverage-completeness-check.md` §14 — Tier 1 run + US-federal bug this Tier 2 run follows
- Jira: OPEN-19, OPEN-21, OPEN-22, OPEN-23
- PR #67 (`--tier2-random`), #69 (US-federal `fetch_all_local_identifiers` fix), #70 (standalone
  `--tier2`, decoupled from Tier 1's pagination cost) — all merged today
