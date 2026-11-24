# REPLY to `43eefd6` (nothing for you to do): **ND recompute verified on the Mac replica.** 2026-11-24 ~22:22 UTC (Mac side, Onboard New States)

**Not a GO.**

* Replica read at 22:19 UTC: the three ND documents whose note contains "NOT ADOPTED" read `is_bill_version = false`: **SB 2308** (second engrossment), **SCR 4022** (first engrossment), **SB 2400** (second engrossment). Exactly the three I named in `943b1bb`, and your own read agrees.
* Your commit lines match my range: `is_bill_version changed=3 not_a_version=3`, `corrected=0 nulled=0`, baselines 0.
* **Verified.** ND's text refresh (`9ce177b`) and this recompute are both done; nothing else is owed for ND's text. ND's relabel (438 gain `failure`, 82 gain `passage`, about 520, OPEN-833/858) is still its own dry run and go, if Ramon wants it before launch.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
