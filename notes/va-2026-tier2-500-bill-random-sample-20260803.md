# Tier 2 standalone check — VA 2026, 500-bill random sample, 2026-08-03

Run via the standalone `--tier2` flag (PR #70) against prod's live DB and the public
`v3.openstates.org` API, production key (30k req/day tier):

```
python3 quality_check.py --tier2 va 2026 --tier2-limit 500 --tier2-random
```

Part of a sweep covering every tracked jurisdiction except Michigan — see the sibling
`notes/*-tier2-500-bill-random-sample-20260803.md` docs from today (MI, AL, AZ, FL, MA, UT×2).

## Result

**1701/2030 checks passed (83.8%) | 254 warnings | 75 failures | 0 skipped**

Lowest pass rate of any jurisdiction checked so far — worth reading past the headline number,
though, since **0 of the 75 failures are real** (all 75 are transient: 74x `429`, 1x timeout — no
"missing votes" failures at all). The story here is entirely in the 254 warnings.

## The dominant warning: a systematic, VA-specific `latest_action` pattern (76 bills, 15.2%)

This is **not** the simple one-directional staleness seen in MI/MA — it's much more structural.
**50 of the 76** `latest_action`-differs cases show local's action as the *exact same templated
string*: `"acts of assembly chapter text (chapNNNN)"`. Live's side varies: sometimes an earlier-
looking step (`"governor's recommendation received by senate/house"`), sometimes a later one
(`"approved by governor-chapter NNNN (effective 7/1/20...)"`) — often referencing the *same*
chapter number local already has. Examples:

- VA SB 60: local=`"acts of assembly chapter text (chap0984)"` vs. live=`"governor's recommendation
  received by senate"`
- VA SB 713: local=`"acts of assembly chapter text (chap0830)"` vs. live=`"approved by
  governor-chapter 830 (effective 7/1/20..."` — both reference chapter 830, just disagreeing on
  which log entry is "latest"

Reading this as ordinary staleness doesn't fit — local isn't uniformly behind or ahead of live.
More likely, local's action list construction always terminates at the "acts of assembly chapter
text" entry once a bill is chaptered, while live's action list includes different/additional
post-passage entries that get selected as "latest" instead. This looks like a genuine structural
difference in how VA's action list is built or ordered locally, not a scrape-recency gap — flagged
here, not root-caused.

## Title differs (16 bills, 3.2%) — partial overlap with the action-diff bills, not full

Only **6 of these 16** are also in the `latest_action`-diff set — a real but partial correlation,
not one unified cause. Some are clearly the same content in a different abbreviation style (e.g.
VA SB 60: `"Virginia Parole Board..."` vs. `"Va. Parole Board..."`), but at least two are
substantively different topics/phrasing, not just formatting:

- VA SB 175: local=`"Renewable energy portfolio standard prog"` vs. live=`"Electric utilities;
  amends renewable ene"`
- VA HB 1405: local=`"Certain decedents; local department of s"` vs. live=`"Social services, local
  dept. of social s"`

Plausibly VA bills get a revised/chaptered final title distinct from the introduced title, and
local vs. live disagree on which one they're storing — consistent with, but not proven by, the
action-list finding above.

## The rest of the 254 warnings

- **148 — "first vote counts differ":** same index/ordering-mismatch shape seen in AZ and UT
  (vote event counts aren't reported as mismatched here since 0 "missing votes" failures occurred,
  so this is comparison-by-index breaking down, not missing data).
- **14 — "local has MORE votes than live (our fix not merged?)"**: the pattern flagged as
  unexpectedly present in FL and MA shows up here too, at a higher count (14) — worth aggregating
  across jurisdictions in a follow-up rather than treating each occurrence in isolation.

## Net

VA's real (non-transient) issue rate is high — roughly **90 of 500 bills (18%)** show some
non-vote-ordering disagreement (76 action + 16 title, with some overlap) — but it looks like a
structural/data-modeling difference in how "latest" is determined for enacted bills, not scraper
staleness or data loss. Worth a follow-up investigation into VA's action-list construction
specifically, given how uniform the dominant pattern is.

Raw log: `logs/quality-check/va_2026_tier2only_500.log` in the prod checkout
(`~/Developer/repos/ddp-open-states`).

## References

- `notes/tier1-coverage-all-jurisdictions-20260803.md` — Tier 1 sweep (VA 2026 came back clean:
  0 missing, 0 extra out of 3637 bills)
- `notes/mi-tier2-500-bill-random-sample-20260803.md`, `notes/fl-tier2-500-bill-random-sample-20260803.md`,
  `notes/ma-tier2-500-bill-random-sample-20260803.md` — other jurisdictions' "our fix not merged?"
  warning instances
- PR #70 — standalone `--tier2` flag this run used
