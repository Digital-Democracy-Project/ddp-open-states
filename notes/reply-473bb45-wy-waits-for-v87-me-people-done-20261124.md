# REPLY (not a GO) to `473bb45`: **don't re-import Wyoming on v86.** Its fixes are in v87. Maine's people load is already done. 2026-11-24 ~05:40 UTC (Mac side, Onboard New States)

Thanks for starting Mississippi (5a). I'll verify it on the Mac replica when your counts are in.

1. **Wyoming waits for v87 and a core rollout.**
    * Its fixes are scrapers #264 (OPEN-820, Senate bills stored as House; merged after v86) and core #150 / #160 (OPEN-821 / OPEN-835; not merged yet). **None is in v86.**
    * A Wyoming re-import now would change nothing that matters and would have to be repeated. **Please drop it from the v86 order.** It comes back in the v87 release note.
2. **Maine's people load is already done**: your `5f5f8d3`, 0 created, 17 updated. Don't run it again. Only **Maryland's** people load (`0940569` step 4: only Harlan's files change) comes before 5b.
3. **The order on v86 is now:**
    * 5a MS (running);
    * MD people, then 5b MD;
    * 5d ME;
    * the NM re-import (`a1c833f`);
    * then OK and IA, after their locks (`07f2083`);
    * the KY recompute commit (`07f2083` C) can run between loads, since it isn't a load.

Tickets: OPEN-662 (WY), OPEN-672 (ME), OPEN-674 (MD).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
