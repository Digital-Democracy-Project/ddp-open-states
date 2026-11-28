# Update (not a GO): Massachusetts backfill dry run read 17 / 3 / 0, I expected 16 / 3 / 1. Your stop was right; please hold, and send me five read-only answers. 2026-11-27 (Mac side, State Specific Handling)

Answers checkpoint `95d4d53`. **Hold the Massachusetts backfill and scrape exactly as you did: nothing applied, no MA scrape.** This is a request for reads, not a GO.

## What I checked
I ran the scraper's own `classify_motion('ma', ...)` (scrapers `744f0212`, the commit your v100 image carries) over **all 530 stored Massachusetts votes on the Mac replica** (read-only; the replica's newest Massachusetts row is from 2026-11-24 08:44 UTC). It reproduces my expected list exactly: **16 passage to none, 3 amendment to none, 1 none to passage (H 4692 "Resolutions adopted")**. So the rules (OPEN-921 to 924) and the code are right; **the difference is in the data**: your production rows have moved since the replica was copied.

My reading, **not verified**: Massachusetts bills were re-scraped on the v99/v100 image after the replica's last row (an incremental run), so H 4692's "Resolutions adopted" vote was written with the new rule and already reads passage (nothing to add), and a later vote was written that the old rules label passage (the 17th). If so, your 17 / 3 / 0 may be correct for production and my expectation was written from older data.

## What I need (read-only, nothing written)
1. The 20 rows of `ma-motion-dry-v100.csv`: bill, chamber, date, motion text, old label, new label (no row ids or hosts needed).
2. H 4692's three stored votes: motion text, label, and last-updated time ("Resolutions adopted", "Adopted", "Amendment #1 (Tarr) rejected").
3. Massachusetts stored totals: votes, and how many are labelled passage, amendment, and unlabelled (my replica: 530 votes; 232 passage, 3 amendment, 295 unlabelled).
4. The time of the last Massachusetts scrape that wrote votes, and which image ran it.
5. How many of the 530 votes have a `house-rollcall-num` or `senate-rollcall-num` extra today (my replica: 0; the full walk should add about 510).

## What I do with it
I compare the 20 rows with my 16 / 3 / 1 and post an update saying what the dry run **should** read and whether to apply it (a request; Ramon's go for the Massachusetts steps stands once the list is agreed). If the 17th row or a missing H 4692 is a rule problem, I file a ticket and build it before anything is applied.

## Not authorized
Applying any Massachusetts list; the Massachusetts scrape; any recompute; any change to Massachusetts's scorecard or LegBot switches.

Tickets: OPEN-921, OPEN-922, OPEN-923, OPEN-924, BROKER-617; OPEN-536.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
