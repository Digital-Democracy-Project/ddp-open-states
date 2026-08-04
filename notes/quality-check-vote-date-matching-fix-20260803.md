# Fix + verification: vote tallies compared by date, not list position (2026-08-03)

## The bug

`compare_bills()`'s vote-tally check compared `local_votes[0]` to `live_votes[0]` — whichever
vote event happened to be first in each side's list. Across today's Tier 2 500-bill sweep (see
`notes/*-tier2-500-bill-random-sample-20260803.md`), this produced 557 "first vote counts differ"
warnings across AZ (113), FL (87), MA (3), MI (29), US (2), UT×2 (174), and VA×2 (149) — the
largest single warning category in every one of those writeups. Several writeups already
suspected this was a comparison artifact (local and live ordering/paginating a bill's multiple
vote events differently) rather than real data loss, since vote *event counts* matched in most
cases — only the "first" one's tally looked wrong.

## The fix

`quality_check.py`'s `compare_bills()` now groups both sides' vote events by calendar date
(`start_date[:10]` — both APIs return a full ISO timestamp, e.g. `2026-02-25T03:28:00-05:00`, but
only the date portion is reliable to match on) and compares tallies only between votes sharing a
date, instead of by list position. Bills with vote events but no overlapping date now get an
explicit "no shared vote dates" warning instead of silently comparing two unrelated votes.

## Verification methodology

Extracted every bill flagged with "first vote counts differ" from today's raw Tier 2 logs
(`~/Developer/repos/ddp-open-states/logs/quality-check/*_500.log`) — 557 total. The live API was
running at ~13-15s/request today (vs. its normal sub-second speed), almost certainly from the
cumulative volume of today's nine 500-bill sweeps — so rather than re-check all 557 (~2+ hours),
took a stratified sample: all bills from the four small jurisdictions (MA, US, UT 2025S2, VA
2026S1 — 7 bills total) plus a random 30-bill sample each from AZ, FL, MI, UT 2026, and VA 2026
(MI only had 29 flagged, so all 29 were included) — 156 bills. Each was re-fetched from both local
and live api-v3 and re-compared with the new date-matched logic.

## Results (156 bills)

| Outcome | Count | % |
|---|---|---|
| Fully resolved — tallies now agree once matched by date | 88 | 56.4% |
| Still mismatched, but confirmed to be the same *kind* of artifact one level deeper (see below) | 28 | 17.9% |
| Genuine, confirmed local-vs-live tally disagreement | 9 | 5.8% |
| Skipped — live API timeout/502 under today's slow conditions | 31 | 19.9% |

## The date-matching fix isn't quite enough on its own

Of the 37 bills still flagged after date-matching, most (28 of 37) turned out to be the *same*
comparison artifact one level deeper: multiple vote events landed on the **same calendar day**
(e.g. VA HB 30, a special-session "vote-a-rama" with ~29 separate amendment votes all dated
2026-06-29), and within a single date the fix still pairs same-day votes by list position
(`zip()`), which can still cross-match the wrong ones. Confirmed by checking whether the *set* of
tallies on each side matches for that date (just reordered) — for 28 of 37, it does.

**Only 9 of 156 bills (5.8%) show a real, confirmed disagreement** — small discrepancies like VA
HB 973 (94 vs 93 "yes" votes) and MI SB 501 (32/0/5 vs 36/0/0) that hold up under every possible
same-date pairing, not just the one `zip()` happened to pick.

## Net

Date-matching alone resolves the majority (56%) of what was flagged, and combined with the
same-date multiset check above accounts for 74% of the original 156-bill sample as pure comparison
artifacts — not real data problems. The remaining gap (same-date multi-vote misordering) needs one
more disambiguation step, tracked as a follow-up in this same PR.

## References

- `notes/az-tier2-500-bill-random-sample-20260803.md`, `notes/ut-2026-tier2-500-bill-random-sample-20260803.md`,
  `notes/va-2026-tier2-500-bill-random-sample-20260803.md` — the original Tier 2 writeups whose
  "first vote counts differ" warnings this fix targets
- PR #70 — the standalone `--tier2` flag used to generate today's raw logs this fix was verified against
