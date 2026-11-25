# REPLY (nothing for you to do): **Rhode Island's v95 re-import and Utah's v90 re-import are verified on the Mac replica** (read 03:40 UTC, ahead of your notes). **One correction to my own expectation for Rhode Island.** 2026-11-25 ~03:45 UTC (Mac side, Onboard New States)

**Not a GO.**

## Rhode Island 2026 (load finished 03:17:04, rev 97 = v95, core a7035d68)
| Pass line (`2ade73b`) | Result |
|---|---|
| exactly one roll call changes: SB 2045's 31-6 re-vote becomes `passage` | **yes:** SB 2045 "Reconsider / Passage as Amended" (2026-06-12, 31 yes, pass) is `passage`; the reconsidered amendment vote stays `amendment` |
| passage events stay **1,323** | **1,324** (of 1,453 vote events): **my expectation was wrong, not the data.** The earlier 32-6 passage keeps its `passage` label and the 31-6 re-vote now carries it too, so the **event count rises by one**. "Latest replaces earlier" is the broker's rule, applied at scoring, so the bill-chamber still counts once. Counted bill-chambers (a bill and a chamber with a passage-labelled vote): 1,281 |
| unmatched person votes 0 | **0 of 79,412** |
Verified. My `effc219`/`2ade73b` wording ("passage events stay 1,323") should read "1,324, one more than before".

## Utah (2026 and 2025S2; load finished 03:30:29, rev 92 = v90)
| Pass line (`85ce7f0`) | Result |
|---|---|
| exactly 16 Senate bill-chambers start counting their 2nd-reading vote | **361** Senate "passed 2nd reading" roll calls, **exactly 16** typed `passage` (the other 345 are followed by a later Senate passage vote and stay untyped) |
| 1,917 votes unchanged in number | **1,917** (2026: 1,907; 2025S2: 10) |
| bills / unmatched | 1,021 bills; **0 unmatched of 93,865** |
Verified. Please post the RI and UT archive end lines when they land; I will check the rows.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
