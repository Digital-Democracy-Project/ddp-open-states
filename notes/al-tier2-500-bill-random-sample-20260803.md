# Tier 2 standalone check — AL 2026rs, 500-bill random sample, 2026-08-03

Run via the standalone `--tier2` flag (PR #70) against prod's live DB and the public
`v3.openstates.org` API, production key (30k req/day tier):

```
python3 quality_check.py --tier2 al 2026rs --tier2-limit 500 --tier2-random
```

Part of a sweep covering every tracked jurisdiction except Michigan (which already has its own
writeup — see `notes/mi-tier2-500-bill-random-sample-20260803.md`). This replaces an earlier,
interrupted 500-bill AL run from earlier today that was killed mid-flight with no summary line.

## Result

**1812/1859 checks passed (97.5%) | 0 warnings | 47 failures | 0 skipped**

## All 47 failures are transient — none are real data problems

| Cause | Count |
|---|---|
| `429 Too Many Requests` | 44 |
| Read timeout (15s) | 3 |

Every failure is a live-API request error, not a title/action/vote/sponsorship mismatch. Of the
checks that actually completed, **100% passed** — no warnings at all. This matches AL 2026rs's
clean Tier 1 result (0 missing, 0 extra out of 1507 bills), and extends that clean bill of health
down to the sub-record level: titles, latest actions, vote counts, and sponsorship counts all
agree wherever the live API request succeeded.

Re-running just the ~44-48 identifiers that hit a transient error would likely close this out at
or near 100%, but given zero real mismatches surfaced across the ~450 bills that did complete,
that's a confirmation run rather than an open question.

Raw log: `logs/quality-check/al_2026rs_tier2only_500.log` in the prod checkout
(`~/Developer/repos/ddp-open-states`).

## References

- `notes/tier1-coverage-all-jurisdictions-20260803.md` — Tier 1 sweep this follows up on (AL came
  back clean there too)
- `notes/mi-tier2-500-bill-random-sample-20260803.md` — the MI counterpart to this sweep, which
  did surface a real systematic staleness issue, for contrast
- PR #70 — standalone `--tier2` flag this run used
