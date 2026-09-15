# For research: 53 old Utah chamber/text mismatches -- confirmed harmless to real scorecards, but the underlying duplicate-motion pattern is worth understanding

Surfaced by `validate_scorecards`'s standing OPEN-67 tripwire (check #10) while validating last
night's `scorecard_update_chain` run -- not something last night's run caused, this is old data.
Ramon asked for full detail passed along for research. Here's everything I found, verified
directly against production rather than just reading the check's summary line.

## What the check found

53 `Motion` rows across **13 distinct Utah bills** (HB32, HB60, HB68, HB136, HB209, HB223, HB247,
HB392, HB479, SB153, SB189, SB194, SB234) whose own text disagrees with their recorded
`origin_chamber`. The swap is total and consistent, not random: every "House/..." motion (37 of
53) is recorded `chamber_type='upper'` (should be `lower`); every "Senate/..." motion (16 of 53)
is recorded `'lower'` (should be `'upper'`). Full inverse in both directions, no partial cases.

## Timing -- confirmed old

Motion `date` values range 2026-01-26 to 2026-03-06; `created_at` values range 2026-03-05 to
2026-04-26 -- landing exactly inside the already-documented incident window in
`validate_scorecards.py`'s own docstring ("Utah's votes were swapped House<->Senate for ~2
months, 2026-03-05 through 2026-04-26, root cause never confirmed"). This is that incident's
leftover data, unremediated five-plus months later -- not new, not from last night.

## Real-world impact on scorecards: confirmed NIL, and here's the mechanism why

This is the part worth double-checking your own thinking on, because it changes what kind of fix
this actually needs. I checked whether any of the 53 motions have real `Vote` rows attached:
**zero.** All 53 have `votes=0` and `eligible_for_scorecard=False`.

Then I checked each affected bill's FULL motion history, not just the flagged rows. Pattern,
using HB136 as the clearest example:

```
motion 898  chamber=upper votes=0  eligible=False  'House/ passed 3rd reading'   (flagged)
motion 1308 chamber=upper votes=0  eligible=False  'House/ passed 3rd reading'   (flagged)
motion 1546 chamber=upper votes=0  eligible=False  'House/ passed 3rd reading'   (flagged)
motion 1008 chamber=upper votes=0  eligible=False  'House/ passed 3rd reading'   (flagged)
motion 2454 chamber=lower votes=75 eligible=True   'House/ passed 3rd reading'   (NOT flagged -- correct)
```

Every affected bill has this same shape: several zero-vote, `eligible_for_scorecard=False`
duplicate motion stubs with the WRONG chamber (the ones the tripwire catches), sitting alongside
one LATER motion (all in the "2xxx" id range, e.g. 2454-2477) with the SAME text, the CORRECT
chamber, real attached votes, and `eligible_for_scorecard=True`. The real scorecard-building code
only ever uses `eligible_for_scorecard=True` motions with real votes -- so it's already using the
correct, later, correctly-chambered ones. `reconcile_scorecards` and `validate_scorecards` both
came back clean for Utah on every other check (tally, choice, accountability, completeness)
precisely because the pipeline was never actually scoring the broken duplicates.

## What's actually worth researching here

Not "are Utah scorecards wrong" -- confirmed they aren't, for these 13 bills at least. Two real
open questions instead:

1. **Why did Utah's bills each accumulate 2-7 duplicate motion stubs for the same real vote
   event**, several with a swapped chamber, before a later correctly-chambered version showed up
   in the "2xxx" id range? That numbering gap (700s/900s/1000s/1300s/1500s vs. 2400s/2500s)
   suggests a re-scrape or backfill pass created the good version well after the fact, without
   cleaning up what came before. Understanding that pass (what it was, why it re-ran, why it
   didn't clean up) would explain the root cause the original incident never confirmed.
2. **Is this pattern (broken duplicates + a later good version, orphaned rows never deleted)
   Utah-specific, or does it exist for other jurisdictions too**, just not caught because their
   duplicates didn't happen to also have the chamber swapped? The chamber-swap is what made this
   particular set visible to check #10 -- a bill with duplicate motions that all had the CORRECT
   chamber would create the same zero-vote orphan clutter without ever tripping this tripwire.

Not urgent, not customer-visible, not something I'm fixing here -- passing along everything I
found in case it's worth a real look. Full list of the 53 motion ids/bills/chambers available if
useful, just ask.
