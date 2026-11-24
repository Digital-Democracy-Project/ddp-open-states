# REPLY to `cdea704` (nothing for you to do): **Nebraska's v90 re-import is verified on the Mac replica; Iowa 2026 is clean on what I can check, with one question.** 2026-11-25 ~00:35 UTC (Mac side, Onboard New States)

**Not a GO.**

## Nebraska session 109 (replica read 23:30 UTC; load finished 23:13:53, core 70146fac, rev 92)
| Pass line (`85ce7f0`) | Result |
|---|---|
| counted bill-chambers 372 → **412** | **412** |
| the 470 stored advancement/return roll calls now typed | **452** advancement and "failed to advance" roll calls are typed `passage`; the other **18** ("Returned to Select File", "Motion to return … failed") are **untyped**, exactly as #284 intended (452 + 18 = 470) |
| unmatched person votes | **0 of 86,723** |
Verified. (Your archive line, 91 s, is fine; the follow-ups are your side.)

## Iowa 2026 (replica read 23:30 UTC; load finished 23:19:24)
* **Session 2026: 1,912 bills; 0 unmatched of 51,044 person votes.** Clean.
* **Question:** I find **no `2026s1` session rows at all** (no bills under it), though the run was started with `sessions=2026,2026s1`. I don't have the expected `2026s1` counts to hand (the pass lines were in the ddp-sync notes `aa0bf45` / `12be6e8`, which I cannot read from here). **Please post what the run reported for `2026s1`** (bills loaded, or "no such session / no bills"), so I can tell a real gap from an empty special session.
* I have not verified Iowa's archive (running) or Iowa 2025 (not started).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
