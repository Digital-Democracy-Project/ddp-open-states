# Tier 2 standalone check — AZ 57th-2nd-regular, 500-bill random sample, 2026-08-03

Run via the standalone `--tier2` flag (PR #70) against prod's live DB and the public
`v3.openstates.org` API, production key (30k req/day tier):

```
python3 quality_check.py --tier2 az 57th-2nd-regular --tier2-limit 500 --tier2-random
```

Part of a sweep covering every tracked jurisdiction except Michigan — see
`notes/mi-tier2-500-bill-random-sample-20260803.md` for that writeup and
`notes/al-tier2-500-bill-random-sample-20260803.md` for AL's (clean).

## Result

**2028/2168 checks passed (93.5%) | 119 warnings | 21 failures | 0 skipped**

## Failures: all transient

21 failures, all live-API request errors (19x `429`, 2x read timeout) — no title, action, or
sponsorship mismatches ended up in the failure bucket at all. **0 "missing votes" failures** —
unlike MI, AZ's vote *event counts* match local-to-live for every one of the 479 bills checked
(no bill is missing a whole vote event locally).

## The 119 warnings are almost entirely one specific, real, systematic issue

- **113 warnings — "first vote counts differ":** despite vote event counts matching, the actual
  yes/no/other tallies on the first vote frequently don't. Breaking these down:
  - **68 of 113: local's tally is all-zero** (`{'yes': 0, 'no': 0, ...}`) while live shows real
    counts — local recorded that a vote happened but not its actual tally.
  - **18 of 113: the reverse** — live's tally is all-zero while local has real numbers.
  - **The remaining ~27: both sides have real, non-zero numbers that simply disagree** (e.g.
    AZ SB 1142: local `yes=16/no=11` vs. live `yes=33/no=25`) — plausibly a vote-ordering mismatch
    (comparing by list index, not vote identity), same underlying failure mode as MI's index-
    misalignment pattern, but here the event *counts* match so it's purely an ordering artifact
    rather than a missing-event one.
  - This is a distinct failure shape from MI's (MI: missing vote events entirely; AZ: vote events
    present locally but with zeroed-out or misordered tally data) — worth treating as its own bug
    class, not folded into MI's writeup.
- **6 warnings — `latest_action differs`, all one exact pattern:** `local='transmit to governor'`
  vs. `live='signed by governor'`, on 6 different bills (SB 1335, 1399, 1422, 1336, 1160, 1423).
  This reads as ordinary scrape-cadence lag (bills signed after AZ's last scrape, not yet
  re-scraped) rather than a chronic blocking issue — AZ has no WAF-blocking history like MI's.
- **0 title-differs, 0 sponsorship-count issues** — both fields matched on every one of the 479
  completed bills.

Raw log: `logs/quality-check/az_tier2only_500.log` in the prod checkout
(`~/Developer/repos/ddp-open-states`).

## References

- `notes/tier1-coverage-all-jurisdictions-20260803.md` — Tier 1 sweep (AZ came back clean there:
  0 missing, 0 extra out of 2190 bills)
- `notes/mi-tier2-500-bill-random-sample-20260803.md` — MI's counterpart finding (missing vote
  events, not zeroed/misordered tallies)
- PR #70 — standalone `--tier2` flag this run used
