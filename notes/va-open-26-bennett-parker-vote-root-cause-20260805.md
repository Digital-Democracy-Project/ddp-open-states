# OPEN-26 root-caused: VA 2026's 2026-02-17 vote-tally gap is a single legislator's House vote, dropped by live's own ingest, isolated to that one date — not our bug

## Context

OPEN-26 asked to root-cause the pattern first surfaced in the 2026-08-03 Tier 2 250-bill
post-fix sweep (`notes/va-2026-tier2-250-bill-post-fix-sweep-20260803.md`,
`PLAN-coverage-completeness-check.md` §15): 20 of 36 remaining "vote tally differs" warnings in a
250-bill VA 2026 sample shared one exact signature — all dated 2026-02-17, local's "yes" count
always exactly one higher than live's, every other tally field matching. VA HB 973 (94 vs. 93,
flagged "genuine" during PR #73's 156-bill verification) was already known to be part of this
same pattern, not a separate finding.

A same-day `/architect-ticket` pass (`OPEN-26-architecture-assessment-20260805.md`, superseded by
this note — see "What the prior assessment got wrong" below) ran in a sandbox with **no local
Postgres/api-v3 access**, and could only compare live's per-voter data against a *current*
100-seat House roster. That method pointed at Kirk McPike (District 5) as the missing legislator.
This session's environment has both `http://localhost:8002` (local api-v3, reachable, keyed with
the standard dev key `00000000-0000-0000-0000-000000000001` already hardcoded in
`quality_check.py`) and live `v3.openstates.org` (via `OPENSTATES_API_KEY`) reachable, which
allows a **direct local-vs-live per-voter diff** — the decisive test the prior assessment
correctly identified as necessary but couldn't run itself.

## Method

1. Fetched `HB 1030`, `HB 973`, and `HB 161` from both local api-v3 and live api-v3 with
   `include=votes`, and diffed the two sides' raw per-voter `votes[]` lists (voter name + option)
   for every vote dated 2026-02-17 — not just the aggregate `counts` field `compare_bills()`
   itself compares.
2. Checked one bill (`HB 1030`) across *every* one of its vote dates, not just 2026-02-17, to
   determine whether any gap was a one-day artifact or a general policy affecting a legislator's
   entire vote history.
3. Paged through the entire local VA 2026 corpus (3,637 bills, `per_page=20`, 182 pages,
   `include=votes`) checking every vote dated 2026-02-17 for the differing voter's presence, to
   size the true blast radius beyond the ~20-bill sample.
4. Verified a fresh random 8-bill sample of newly-found bills (excluding the ~20 originally
   sampled) directly against live, to confirm the pattern generalizes.
5. Web search to establish the differing legislator's actual seat history/timeline for AC #2.

Raw data: `logs/quality-check/va_open26_hb1030_hb973_voter_diff.json`,
`va_open26_hb1030_date_isolation.json`, `va_open26_hb161_two_votes_same_day.json`,
`va_open26_full_corpus_scan.json`, `va_open26_sample8_live_verify.json` (this checkout).

## Result 1: one shared event, confirmed — and it's a single legislator, not a roll call artifact

Diffing local's and live's per-voter `votes[]` lists for HB 1030's and HB 973's 2026-02-17 votes
(two *independent* roll calls, per the earlier writeup's own observation that HB 973's 94/93
tally didn't match the 96/0/3-group bills) shows **exactly one name different in each case, and
it's the same name both times**:

| Bill | Local voters | Live voters | Voter present in local, absent from live |
|---|---|---|---|
| HB 1030 | 100 | 99 | Elizabeth B. Bennett-Parker (yes) |
| HB 973 | 100 | 99 | Elizabeth B. Bennett-Parker (yes) |

Every other one of the 99-100 names matches exactly between local and live on both bills. This
directly confirms AC #1's first half: this is one real, shared discrepancy (one legislator's
vote, dropped from live on this date across every roll call she participated in that day) — not
20 independent bugs, and not a roll-call-identity coincidence.

`HB 161` initially looked like a bigger, unrelated discrepancy (67/30/3 vs. 46/48/5) — but that's
an artifact of this session's own ad hoc diffing, not a second bug: HB 161 has *two* votes on
2026-02-17 sharing the identical blank-disambiguator `motion_text` ("H VOTE:", one `pass` one
`fail`), and naively pairing local's first vote against live's first vote crossed the two.
Pairing correctly by `result` (matching `compare_bills()`'s own existing date+motion_text+
positional-fallback pairing logic) shows HB 161 carries the *exact same* single-voter signature,
twice — see `va_open26_hb161_two_votes_same_day.json`.

## Result 2: the specific legislator — Elizabeth B. Bennett-Parker, not Kirk McPike

**What the prior assessment got wrong:** its method compared live's 99-voter list against the
*current* 100-seat House roster and found two current members (McPike, Andrew Rice) missing —
correctly observed, but the wrong signal. Neither McPike nor Rice held their House seats on
2026-02-17 at all (both members' local `people` records show a 2026-04-09 creation date, i.e.
after this vote and after VA's 2026 session ends 2026-03-14), so of course they don't appear in
that day's roll call on *either* side — their absence from live's data is expected and uninformative,
not the bug. A roster-based check can't distinguish "missing because dropped" from "missing
because not yet seated," which is exactly what happened here.

The direct local-vs-live diff doesn't have that blind spot: it shows unambiguously that
**Elizabeth B. Bennett-Parker** is the one voter present in local's per-voter list and completely
absent from live's, on both HB 1030's and HB 973's independent 2026-02-17 roll calls (and HB
161's two).

## Result 3: which side is correct — local. Live's own data is missing a real, legitimate vote

Bennett-Parker was, as of 2026-02-17, a sitting member of the Virginia House of Delegates:

- She won the Democratic nomination for VA Senate District 39 (vacated by Sen. Adam Ebbin) on
  2026-01-13, and won the special general election on **2026-02-10**.
- She was **sworn into the Senate on 2026-02-18** — the day *after* the vote in question — to
  complete the remainder of Ebbin's term.
- Through 2026-02-17, she was still a Delegate representing her House district (per Ballotpedia
  and Wikipedia, House member since 2022; per the Virginia Mercury/ALXnow/Democratic Party of
  Virginia special-election coverage, her Senate swearing-in date is 2026-02-18).

So her House floor vote on 2026-02-17 is a real, legitimate vote by a sitting Delegate — **local's
data is correct**, and live is the side missing a real record. This is AC #2 answered directly:
local wins.

**How isolated is live's gap — a one-day glitch, or a broader "drop transitioned members"
policy?** Checked Bennett-Parker's presence across *every* one of HB 1030's votes
(`va_open26_hb1030_date_isolation.json`): she appears identically on both local and live for
2026-02-12, 2026-02-13, 2026-03-09, and 2026-03-10 (present on all four, correctly, on both
sides), and is correctly absent from both sides' 2026-03-11 vote (she genuinely didn't vote that
day). **2026-02-17 is the only date where the two sides disagree.** This rules out a general
upstream policy that strips a since-transitioed member's entire historical voting record — it's
isolated to this one date, consistent with a narrow ingest/snapshot-timing issue in live's own
pipeline that happened to coincide with her chamber transition, not a systemic exclusion rule.

**Since when have we found this class of upstream problem?** This is a different failure shape
from OPEN-28's MI finding (a silently-swallowed scraper fetch on *our* side) — here, our own
scraper and import correctly captured and retain her vote; the gap is entirely on live
(`v3.openstates.org`)'s side, a system we don't control. No scraper/import fix is proposed or
needed on our end.

## Result 4: blast radius — 266 bills, not ~20

Paging through the full local VA 2026 corpus (3,637 bills) for every 2026-02-17 vote and checking
for Bennett-Parker's presence (`va_open26_full_corpus_scan.json`):

- **338 bills** have at least one vote dated 2026-02-17.
- **266 of those 338** include Bennett-Parker as a voter in local's data — i.e., 266 bills share
  this exact discrepancy pattern, not the ~20 originally sampled by the 250-bill Tier 2 sweep.
- The remaining **72** bills' same-day votes are structurally unrelated: Senate floor votes
  (40-voter roll calls) or House committee votes (15-22 voters) she wasn't part of — different
  chamber/committee, not additional instances of this finding.
- A fresh random 8-bill sample drawn from the newly-found 266 (excluding the originally-sampled
  ~20) was checked directly against live and **8 of 8 confirmed the pattern**
  (`va_open26_sample8_live_verify.json`), including HB 161's two-votes-same-day case once
  correctly paired.

This answers AC #5: the true blast radius is roughly **13x** the sampled ~20 bills.

## Conclusion

- **AC #1 (root cause + specific legislator):** confirmed — one shared event (actually two
  independent 2026-02-17 roll calls, both affected identically), caused by a single legislator's
  vote (Elizabeth B. Bennett-Parker) being present in local's data and missing from live's.
- **AC #2 (which side is correct):** local is correct. Bennett-Parker was a sitting Delegate
  through 2026-02-17 (Senate swearing-in was 2026-02-18); her House floor vote is real and should
  count.
- **AC #3 (if local is wrong, fix it):** N/A — local isn't wrong.
- **AC #4 (if live is wrong, document and close as not-actionable):** applies. The gap is in
  `v3.openstates.org`'s own data, isolated to 2026-02-17 specifically (not a general policy — see
  Result 3), most plausibly an ingest/snapshot timing issue on their side coinciding with her
  chamber transition. This is upstream's system, not ours — nothing to fix in our scraper or
  import pipeline.
- **AC #5 (blast radius):** 266 of 3,637 local VA 2026 bills (not ~20) share this exact
  discrepancy.

## Recommendation

- **Close OPEN-26** with this conclusion — no scraper/import code change on our side.
- **Do not re-open the McPike/Rice thread** — that was a real but unrelated observation (both
  members simply weren't seated yet on 2026-02-17), not part of this finding.
- **Follow-up ticket filed: [OPEN-32](https://digitaldemocracyproject.atlassian.net/browse/OPEN-32)**
  (mirroring how OPEN-28's investigation spawned OPEN-30 as a separate ticket rather than bundling
  code into the diagnostic ticket), proposing `quality_check.py`'s `compare_bills()` gain a
  per-voter diff (name the specific differing voter(s), not just aggregate counts) and a same-date
  blast-radius helper — exactly the ad hoc analysis this note did by hand. This is the second "one
  shared date, many bills" finding this quarter (after OPEN-28/MI), and neither time did the
  existing tool surface "who" or "how many" as first-class output.

## Still open

- Whether live's ingest bug recurs for other legislators who change chambers mid-session — this
  investigation only checked Bennett-Parker's case; not generalized.
- The exact mechanism inside `v3.openstates.org`'s own pipeline that dropped this one date's
  votes — out of scope (upstream's system, not ours) and not diagnosable from outside it.
- [OPEN-32](https://digitaldemocracyproject.atlassian.net/browse/OPEN-32) (the `compare_bills()`
  per-voter-diff + blast-radius helper) itself — not yet implemented, just filed.
- Everything else already carried forward in `PLAN-coverage-completeness-check.md` §15/§16 (HD/SD
  dedup, `scraper-audit`, cadence wiring, MA prefix re-check, FL's "local has MORE votes" pattern).

## References

- `notes/va-2026-tier2-250-bill-post-fix-sweep-20260803.md` — original finding
- `notes/quality-check-vote-date-matching-fix-20260803.md` — the vote-comparison fix this finding
  surfaced under
- `PLAN-coverage-completeness-check.md` §15, §16 (this ticket closes out §15/§16's carried-forward
  "VA's 2026-02-17 block-vote discrepancy" item — see new §17)
- `notes/mi-open-28-missing-vote-root-cause-20260805.md` — sibling investigation this session's
  method and note structure follow; also the OPEN-28→OPEN-30 precedent for filing a separate
  follow-up ticket rather than bundling a tooling fix into a diagnostic ticket
- Raw diagnostic data: `logs/quality-check/va_open26_hb1030_hb973_voter_diff.json`,
  `va_open26_hb1030_date_isolation.json`, `va_open26_hb161_two_votes_same_day.json`,
  `va_open26_full_corpus_scan.json`, `va_open26_sample8_live_verify.json`
- Bennett-Parker's seat timeline: Ballotpedia, Wikipedia, Virginia Mercury
  ("Bennett-Parker wins Va. Senate District 39 special election", 2026-02-10), ALXnow
  ("JUST IN: Elizabeth Bennett-Parker wins decisive victory in special election for State
  Senate"), Democratic Party of Virginia ("Elizabeth Bennett-Parker Wins Virginia's Senate
  District 39 Special Election")
- Jira: OPEN-26 (this ticket); [OPEN-32](https://digitaldemocracyproject.atlassian.net/browse/OPEN-32) (follow-up tooling ticket)
