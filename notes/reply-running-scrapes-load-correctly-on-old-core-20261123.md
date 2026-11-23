# REPLY to your `3cef331` (core rebuild plan): none of the running scrapes (mi, ri, id, wy, ok, fl, pa) needs core `42b48982` in the loader to load correctly. The old loader core loads them exactly as before. 2026-11-23 (Mac side, Onboard New States)

**Nothing to do from this note.** It answers your question so the rebuild can proceed in your planned order. Ramon: "rebuild once the Oklahoma archive finishes".

## What the loader core changes between `7f531958` (EC2 ddp-sync now, your `7310af7`) and `42b48982`
`git diff 7f531958 42b48982` touches 5 files, with no migration and no model change. Leaving out tests:
* **`openstates/importers/base.py` and `importers/vote_events.py`: OPEN-767** (#138, `3ac06b6a`).
    * When a roll-call name matches **two or more** people and the current-role tie-break can't choose, it keeps only those who held the seat on the vote's date. A name that already gives one person is never re-decided.
    * With the old core, such a vote stays unmatched: exactly how it is stored today. It isn't written wrong.
* **`openstates/utils/version_ordering.py`: OPEN-773** (#139). It adds one version-name rule: "Current/Final" is chamber passage.
    * That name exists only in Kentucky (replica: 652 rows, all `ky`).
    * The rule acts at the archive/recompute, not the load.

## The four states you asked about (read-only, Mac replica, 2026-11-23)
| State | Votes stored | Unmatched | Does OPEN-767 change any? |
|---|---|---|---|
| pa | 426,758 | **0** | no: nothing is unmatched |
| mi | 96,566 | 787 | no: the top names ("O’Neal" 406, "OâNeal" 51, "Myers-Phillips" 11) have 0 or 1 candidate person. 767 only splits ties |
| fl | 348,693 | 2,131 | no: most names have 0 or 1 candidate ("Rayner-Goolsby", "Campbell, Daryl" none; "Valdés", "Cassel", "Mayfield" one). "Altman" (3) and "Bell" (2) are ties, about 23 votes |
| ok | 331,234 | 3,451 | no: "Hader" 1,928 has 0 candidates; "Mr. Speaker" 1,479 is a title, not a surname |

* **The regression run for OPEN-767** (#138's PR body) re-resolved every stored vote with the new core against production's people: **2.43M votes, 0 lost and 0 switched in every state. Gains only in NE ("Meyer") and LA ("Henry").**
    * So the FL "Altman"/"Bell" ties stay unmatched under either core.
    * PA, MI and FL were all in that run.
* **Oklahoma wasn't in that run** (it had no data yet). Its first scrape is already loaded, on the old core. The table shows OPEN-767 has nothing to resolve there.
* **id, wy and ri:** as in my requests (`46ab1e0`, `994956e`, `3c17467`), none needs a core change since `7f531958`.

## So
* Loading mi, ri, id, wy, ok, fl and pa with the old core gives the same result as the new core.
* The rebuild's real cost is the one you named: runs that lose their archive step or a later session. That cost is Ramon's call.
* **Nothing needs a re-run because of the core.**

## Found on the way (no action from you)
Oklahoma's 3,451 unmatched votes are almost all two names:
* "Mr. Speaker" (1,479): the same pattern as Louisiana's OPEN-764;
* "Hader" (1,928): no such person in the people data.

They are below the Stage 3 limit (1.0% against 4.7%). I'll take them up in Oklahoma's Mac-side checks (OPEN-666), with fix tickets on the source.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
