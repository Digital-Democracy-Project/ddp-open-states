# AZ/WA/FL Tier 1 + Tier 2 quality-check sweep (500-bill random sample) — AZ and WA both clean, FL confirms two known pre-existing gaps

## Context

Ahead of BROKER-16's remaining Stage 1 flips (BROKER-34 = AZ, BROKER-36 = WA, BROKER-38 = FL —
see `ddp-infra/PLAN-open-states.md` §8.1a and the BROKER-16 umbrella ticket), ran a fresh
`quality_check.py --coverage` sweep against all three jurisdictions with a 500-bill random Tier 2
sample each, to get real, current evidence of replica data quality beyond what's already recorded
in the plan docs. AZ and WA have no jurisdiction-specific gate in the rollout; this sweep is
supporting evidence for their flips, not a new gate. FL's own gate (the WAF vote-gap re-scrape,
OPEN-41) already closed 2026-08-08 — this sweep is a fresh independent check, not a re-litigation
of that gate.

**Rate limit note:** the live `OPENSTATES_API_KEY` used for comparison is hard-capped at 2
requests/second (confirmed directly by the operator). All three jurisdictions were run strictly
sequentially against this key — never concurrently — to avoid compounding 429s/timeouts.

## Method

```
DATABASE_URL=postgresql://openstates:openstates_dev@localhost:5433/openstates \
  python3 quality_check.py --coverage <jurisdiction> <session> --tier2-limit 500 --tier2-random
```

Run from `ddp-open-states-dev`, with `DATABASE_URL` explicitly pointed at the real production
replica database (`openstates`, confirmed via `select current_database()` immediately before each
run — **not** `openstates_dev`, this checkout's own separate dev/test database). Sessions: FL
`2026`, WA `2025-2026`, AZ `57th-2nd-regular` (each confirmed as the jurisdiction's current
bill-bearing session via a direct DB query before running).

- **Tier 1**: full identifier-set diff — every bill identifier live vs. every bill identifier local.
- **Tier 2**: sub-record comparison (title, latest_action, vote event counts + tallies,
  sponsorship counts) on a 500-bill random sample of bills present in both sets.

## Results

### AZ (57th-2nd-regular)

**Tier 1: perfect.** 2,190 live == 2,190 local, 0 missing, 0 extra.

**Tier 2 (2,635 individual field checks): 2,552 passed / 56 warnings / 27 failures.**

| Category | Count | Verdict |
|---|---|---|
| "vote tally differs" | 51 | Cosmetic — see below |
| "latest_action differs" | 5 | Staleness lag, not a bug |
| "live API error" (ReadTimeout) | 26 | Infra noise, not local data |
| local missing a real vote event | 1 | Real gap — HR 2001 |

The 51 "vote tally differs" warnings collapse to only **24 distinct (bill, date) pairs**, and every
one of them is immediately followed by a correct "✓ matches" line for that same date. Example
(HB 2028, 2026-06-09): local vote #1 compared against live vote #2 (mismatch), local vote #2
against live vote #1 (the exact mirror-image mismatch), then a third pairing matches exactly. This
is the comparator pairing same-date vote events positionally rather than by content when a bill
has 2+ roll calls on one calendar date — the same benign cosmetic pattern already documented in
`notes/fl-open-41-waf-vote-gap-verification-20260808.md` (SB 1724's vote array in a different
order between the two APIs). Not a real data gap.

The 5 "latest_action differs" warnings are all the same shape: local shows `"transmit to
governor"` or `"transmit to senate"`, live already shows `"signed by governor"` — ordinary
incremental-scrape staleness (the bill progressed since AZ's last scrape), not corruption.

26 of the 27 failures are `HTTPSConnectionPool ... Read timed out` against `v3.openstates.org` —
the live API choking under the 2 req/s key limit, not a local data problem; those bills were
simply never successfully compared. **The one real failure: HR 2001 — local shows 0 vote events
vs. live's 1** — a genuine, small, missing-vote gap.

**Net for AZ: of 500 sampled bills, exactly one (HR 2001) has a confirmed real data gap.**
Everything else is a clean match, a cosmetic same-date vote-ordering artifact, an expected
staleness lag, or live-API noise.

### WA (2025-2026)

**Tier 1: near-perfect.** 3,413 live vs. 3,411 local — **2 bills missing locally** (99.94%
coverage). Specific identifiers not extracted in this pass (the script only reports the count, not
the identifiers themselves — pulling them would need a follow-up targeted diff; not done here to
avoid spending more of the rate-limited API budget while FL's retry was in flight).

**Tier 2 (2,289 individual field checks): 2,261 passed / 0 warnings / 28 failures.**

All 28 failures are infrastructure noise: 27 are `live API error` timeouts, and the remaining 1 is
the Tier 1 coverage-failure line itself carried into the same summary total. **Zero real content
warnings or mismatches** across every bill that was successfully compared — title, latest_action,
vote tallies, and sponsorship counts all matched 100% of the time.

**Net for WA: essentially clean.** The only open item is the 2-bill Tier 1 gap; every field on
every successfully-compared bill matched exactly.

### FL (2026)

**First attempt (2026-08-11 21:32 UTC) crashed.** Tier 1's live-identifier pagination hit
repeated `urllib3.exceptions.ReadTimeoutError`s around page 71-73/97 — a low-level exception the
script's retry wrapper doesn't catch — and the process exited with an unhandled traceback before
Tier 2 ever ran. Root cause is almost certainly the same 2 req/s key ceiling noted above; the
pagination loop has no per-request sleep the way the Tier 2 loop does.

**Retry launched standalone** (no concurrent jurisdiction sharing the key) at 2026-08-11 22:28
UTC, after confirming both WA and AZ had released it. Completed 2026-08-12 02:50 UTC.

**Tier 1: 34 bills missing** — 1,931 live vs. 1,897 local (1.76%). **This exact figure (34 of
1,931) matches `notes/tier1-coverage-all-jurisdictions-20260803.md`'s finding from 2026-08-03** —
the gap is unchanged over more than a week, i.e. pre-existing and unrepaired, not new. It is a
different, separate gap from OPEN-41's WAF-outage vote list (already verified closed
2026-08-08) — nobody has investigated this identifier-level gap's root cause yet.

**Tier 2 (2,322 individual field checks): 2,228 passed / 32 warnings / 62 failures.**

| Category | Count | Verdict |
|---|---|---|
| "local has MORE votes than live" | 30 | Expected/positive — OPEN-27, DDP's own WAF fix isn't merged upstream |
| "latest_action differs" | 2 | Cosmetic — live just appends extra text, e.g. `'adopted by publication'` vs. `'adopted by publication; companion bill(s) passed, '` |
| "live API error" (ReadTimeout) | 45 | Infra noise, not local data |
| local missing votes entirely | 16 | Real gap — see below |

The 30 "local has MORE votes than live" warnings are the already-diagnosed, already-accepted
OPEN-27 pattern (`notes/fl-tier2-more-votes-than-live-diagnosis-20260805.md`) — a genuine local-only
fix (`_FLHouseWAFSource`) that public upstream hasn't merged, so local legitimately has more real
data than live. Not a gap.

**The real finding: 16/500 bills (3.2%) show local with 0 votes where live has 1-3** (e.g. HB 1295:
local=0, live=3; HB 4023: local=0, live=1). This is comparable in shape and magnitude to
`notes/fl-tier2-500-bill-random-sample-20260803.md`'s prior finding (14/500, 2.8%, same
"local is MISSING votes vs live" category) — **not a new regression**, and importantly **not the
same gap OPEN-41 verified closed**: OPEN-41 was scoped narrowly to a specific 540-bill candidate
list from the 2026-06-25/26 WAF-outage scrape, verified via a targeted before/after count (+91%
recovery) — it was never claimed to close every FL vote-completeness gap. `PLAN-open-states.md`'s
own OPEN-41 resolution note already anticipated this: "failures are the separate, pre-existing
'local missing vs live' gap — both out of scope for this item." Whether today's 16 bills overlap
with the original 540-bill WAF list wasn't checked here (the candidate list file was ephemeral and
no longer exists) — a genuine open question for anyone who wants to fully close this out.

## Conclusion

**AZ and WA both show data quality strong enough to support their BROKER-16 flips** (BROKER-34,
BROKER-36) without a data-quality objection — the only non-cosmetic gaps found are AZ's single
missing vote event (HR 2001) and WA's 2 missing bills, both small enough not to block given
neither jurisdiction carries an existing gate in the rollout plan.

**FL shows no new regression, but is meaningfully less clean than AZ/WA** — it carries two
longstanding, unrepaired, and previously-undiagnosed-at-the-root-cause-level gaps (a 1.76% Tier 1
identifier gap, unchanged since 2026-08-03; a ~3% Tier 2 vote-completeness gap, same order of
magnitude as a week ago). Neither is part of BROKER-38's actual gate, which was specifically and
narrowly the WAF-outage vote list (OPEN-41, verified closed) — so this doesn't reopen that gate —
but it means "FL's data quality" as a whole is not fully clean the way AZ/WA's is.

## Recommendation

- **AZ (BROKER-34) / WA (BROKER-36):** no data-quality objection to executing per the runbook.
- Optional low-priority follow-up: identify WA's 2 missing-bill identifiers and confirm whether
  HR 2001's missing vote event is a scraper gap or a live-side artifact.
- **FL (BROKER-38):** OPEN-41's specific gate remains closed, so this doesn't block the flip on its
  own terms — but the 34-bill Tier 1 gap and 16-bill Tier 2 vote gap are real, unexplained, and
  static since 2026-08-03. Worth a root-cause ticket (checking whether either overlaps the original
  540-bill WAF list, and why the Tier 1 gap hasn't moved in over a week) before treating FL as
  "clean" the way AZ/WA now are.

## References

- `ddp-infra/PLAN-open-states.md` §8.1a — the live per-jurisdiction gate tracker
- BROKER-16 (umbrella), BROKER-34/36/38 (AZ/WA/FL flip sub-tasks)
- `notes/fl-open-41-waf-vote-gap-verification-20260808.md` — OPEN-41's WAF-outage vote-gap
  verification (the actual BROKER-38 gate, confirmed closed) and the same-date vote-ordering
  cosmetic pattern (SB 1724) also seen in AZ's results above
- `notes/tier1-coverage-all-jurisdictions-20260803.md` — the 2026-08-03 sweep that first found
  FL's 34-bill Tier 1 gap, unchanged in this sweep
- `notes/fl-tier2-500-bill-random-sample-20260803.md` — the 2026-08-03 sweep that first found
  FL's vote-completeness gap (14/500 then vs. 16/500 now, same order of magnitude)
- `notes/fl-tier2-more-votes-than-live-diagnosis-20260805.md` — OPEN-27's diagnosis of the
  "local has MORE votes than live" pattern as an expected, unmerged local fix
- Raw logs (this checkout): `logs/quality-check/az_57th-2nd-regular_tier1tier2_500_20260811.log`,
  `logs/quality-check/wa_2025-2026_tier1tier2_500_20260811.log`,
  `logs/quality-check/fl_2026_tier1tier2_500_20260811.log` (crashed first attempt),
  `logs/quality-check/fl_2026_tier1tier2_500_20260811_retry.log` (completed retry)
