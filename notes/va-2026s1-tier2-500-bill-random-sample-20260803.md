# Tier 2 standalone check — VA 2026S1, full-session sample, 2026-08-03

Run via the standalone `--tier2` flag (PR #70) against prod's live DB and the public
`v3.openstates.org` API, production key:

```
python3 quality_check.py --tier2 va 2026S1 --tier2-limit 500 --tier2-random
```

Part of a sweep covering every tracked jurisdiction except Michigan (see the sibling
`notes/*-tier2-500-bill-random-sample-20260803.md` docs from today). VA 2026S1 is a special
session with only 300 bills locally in total (matches the Tier 1 sweep's finding: 300 live, 300
local, 0 missing) — so `--tier2-limit 500` samples the entire session, not a subset.

## Result

**1141/1158 checks passed (98.5%) | 1 warning | 16 failures | 0 skipped**

All 16 failures are transient (11 read timeouts, 5x `429`). The single warning is the same
"first vote counts differ" ordering artifact seen across AZ/UT/VA-2026's writeups — no missing
votes, no title mismatches, no sponsorship issues.

## Net — a sharp contrast to VA's main 2026 session

VA 2026S1 is essentially clean: **0 real data-quality findings** out of 300 bills. This is a
notable contrast with VA 2026's writeup (the regular session), which showed a systematic,
structural `latest_action`/title disagreement pattern on ~18% of its sample. Whatever's driving
that pattern in the regular session doesn't show up here — plausibly because this special
session's bills haven't gone through the same chaptering/enactment pipeline the regular session's
`latest_action` finding was tied to (or simply too few of this session's 300 bills have reached
that stage yet to surface it in a 300-bill sample).

Raw log: `logs/quality-check/va_2026S1_tier2only_500.log` in the prod checkout
(`~/Developer/repos/ddp-open-states`).

## References

- `notes/tier1-coverage-all-jurisdictions-20260803.md` — Tier 1 (VA 2026S1: 0 missing, 0 extra
  out of 300 bills)
- `notes/va-2026-tier2-500-bill-random-sample-20260803.md` — same jurisdiction, regular session,
  the structural `latest_action` finding this session doesn't show
- PR #70 — standalone `--tier2` flag this run used
