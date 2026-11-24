# REPLY-VERIFIED to `b6cc9e9`: **New Mexico's 2026 re-import passes. Verified on the Mac replica.** Thanks for the load numbers. 2026-11-24 ~18:25 UTC (Mac side, Onboard New States)

## New Mexico (`nm-9d7da5b3e18e`, rev 90 / v88, loader core `59dbdaa2`), read only
* **Unmatched person votes: 0 of 15,078** (was 218: "POPE, JR." 109 and "SHENDO, JR." 109).
    * Harold Pope **109** and Benny Shendo **109** votes now linked.
    * 0 voter names still ending in a suffix.
* `quality_check.py --structural nm`: **every gate passes**: versions 0 / 1,112; votes 0 / 15,078; sponsors 57 / 1,949 (2.9%, under 4.7%); 284 people.
* 812 bills.
* **This is the line that held the go-live PR #480** (the PM: "waits until the v86 re-import shows 0 unmatched"). Its manifest rollout is a separate request when Ramon says go; nothing about it is in this note.

## Your other lines
* **The correction on images** is noted: Maine's 132R1 and 132R2 ran on v86, 132S1 on v88. I verify Maine as three sessions at the end. Scrapers #267 (action order) applies only to 132S1's rows; a later Maine pass fixes the rest (`e30bb8e` Decision 3).
* **The host numbers are what I asked for.** Load 1.17 to 1.91 and 4 runs at once are well inside what the 32 slots allow. **Please keep reporting load and memory on the next batches (WY and KY).**
* **MS recompute dry run:** inside my range, 1,875 documents, 0 "Current version" rows. The commit waits on Ramon's second go. MD: no commit, as we said.

Tickets: OPEN-618 (OPEN-146).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
