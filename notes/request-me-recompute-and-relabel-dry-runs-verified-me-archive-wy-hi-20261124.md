# REQUEST (not a GO): **two dry runs for Maine now that its archive passes**, and my verification of the Maine archive, Wyoming and Hawaii. 2026-11-24 ~22:45 UTC (Mac side, Onboard New States)

**Not a GO.** Both asks are **dry runs only**. Nothing is committed without Ramon's second go after he sees the numbers.

## What I need from you
1. **`os-text-extract recompute-diff-order me --dry-run --list <file>`** at core `70146fac` (ddp-sync container). Report the exact summary lines and the list md5. **Expect none** (`corrected=0 nulled=0`, no baseline change): Maine's text did not exist before today's archive, so there is nothing stored to correct. Anything else: report it, don't commit.
2. **`os-text-extract relabel me --dry-run --list <file>`** (OPEN-866, core #171). **Expect about 5,177 actions changed** (2,870 gain `passage`, 2,307 lose it; I re-measure at `70146fac` and post any difference before Ramon sees it). Report the exact lines and the list md5.
* Both are read-only. Neither is a commit.

## Verified on the Mac replica (read 22:32–22:45 UTC)
* **Maine archive: verified.** 5,131 version documents, **5,131 with text**, all rewritten after 20:30 UTC (last 22:07:52). Matches your `fetched=5131 archived=5131`.
* **Wyoming 2026: verified.** Counted bill-chambers **382** (was 276, as predicted); 0 unmatched of 45,490 person votes; the 14 SF 1 line items are still `veto-override` (not counted); HB 178's later failed whole-bill override ("Did Not Override Veto 36-21") is typed `passage` beside the earlier concurrence (the broker's "latest replaces earlier" rule does the replacing).
* **Missouri archive:** your `fetched=47 archived=47` is as expected after MO's load (`reply-verified-mo-…`).
* **Hawaii 2026 (loaded 22:29:09): mostly verified, one finding.** Senate passage roll calls with no person votes **0 of 1,182** (was 1,004); sponsors unmatched **0 of 31,954**; 6,728 bills. **Finding:** **4,795 of 285,990 person votes (1.7%) match no legislator**: "Ward" 1,334, "Rachele Lamosao" 1,085, "Lee, C" 1,050, "Aquino" 442, "Henry Aquino" 320, "Lamosao" 305, "C." 147, "Gene Ward" 81. These members are missing from the scorecard. I filed **OPEN-879** for it; nothing for you to do, and **no second Hawaii run** (Ramon chose once).
* The resource reading you posted (load up to 3.70, 6.9 of 15.7 GB, 7 runs at once, no loader or RDS failure) is what I asked for; please add the peak after the NE and UT loads.

## Not authorized
Any commit of either dry run; a second Hawaii run; any Maine run; anything beyond the two dry runs.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
