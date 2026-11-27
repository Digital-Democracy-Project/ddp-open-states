# REQUEST (not a GO): **after a scrapers image that carries openstates-scrapers #311 (OPEN-934) is live, re-import Virginia 2026 and 2026S1, then I re-measure.** 2026-11-27 (Mac side, State Specific Handling)

**Not a GO, nothing to start now.** Ramon gives the go in your session naming this note and the image. Virginia was already re-imported once today (the 2026 and 2026S1 loads of 11-27); this is a second, small one, for five votes whose labels the first could not fix.

## What the image must carry
openstates-scrapers **#311** (merge `c3ff46e1`, OPEN-934): four Virginia passage patterns in `motion_classification.yaml`. It is **not in v99** and not in any image yet. Read the recorded scrapers commit of the new image and report it; **stop if it does not contain `c3ff46e1`**. (Anything else riding the same image, such as the Iowa/Wyoming request, is separate.) If Ramon drops the SB 59 rule before the build, the numbers below do not change.

## What I need from you (after the go)
1. A Virginia re-import of **2026 and 2026S1**, the same way as today's. Report the vote-event counts per session (today: 2026 = 11,512, 2026S1 = 35; they should not change).
2. Tell me when it is done. I re-measure on the Mac replica and post the numbers; you do nothing else with Virginia's scorecards.

## What to expect (my measurement on the Mac replica, read-only, not production)
* **Exactly 5 stored labels change, all from none to passage:** SJ 139 (Senate) and SJ 140 (Senate) "Read third time and agreed to by Senate", SJ 111 (House) "VOTE: Agreed to by House", HB 671 (Senate) "(S5020) Passed Senate with amendment Block Vote", SB 59 (House) "Failed to pass House". Nothing else moves; no label is lost.
* Virginia's counted votes **2,657 to 2,661**, failed shown **40 (unchanged)**, bills with a counted vote **1,452 to 1,453**. SJ 139, SJ 140, SJ 111 and HB 671 gain a counted vote; SB 59 gets the label but stays uncounted.
* Any other difference: stop and report.

## Not authorized
The Virginia backfill, recount or switch-on (held in `b509a40e` until my re-measure is posted and Ramon says go); any other state's re-import; a manifest change; anything that touches a Voatz or auto-poll switch.

Tickets: OPEN-934 (this fix), OPEN-933 (why the earlier numbers differed), OPEN-919, BROKER-614; OPEN-536; OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
