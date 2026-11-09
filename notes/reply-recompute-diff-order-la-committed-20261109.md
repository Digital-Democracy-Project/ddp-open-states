# Reply: recompute-diff-order la COMMITTED + api-v3 on EC2 (OPEN-510/511), 2026-11-09 02:35-02:40 UTC (prod agent)

User's words: pop-up "Yes, commit only if numbers are exactly those (Recommended)".
- Restore point recorded 02:35:40Z. Code: openstates-core 6641dda7 (worktree on PYTHONPATH).
- Dry run before: `unchanged=9147 corrected=1266 nulled=55`, `not_a_version=3383 changed=55`: exact.
- Commit (02:36:08, 14 s): same numbers. Dry run after: `unchanged=10468 corrected=0 nulled=0`, `not_a_version=3383`.
- G3 after: docs 10,468, true 7,085, false 3,383, null 0, with a diff 4,486; fingerprint 9d63127c158490c56c9f0ee40c432a24 (before: b2fd5c70e579d17b4e315b1c6e91d2b6). Files `~/ops/la-part2-*.txt`, `g3_la_*.out`. No search refresh.
- api-v3 on EC2: before b7adb9a3 (image 3b1a466605a1, tagged `pre-open510`); this brought only #52 (2 files; #49 and #51 were already there); ff to fe6532a9; rebuilt, `api` recreated by name (about 6 s out), health 200, new image f2a6fb38.
- SB 217 (ocd-bill/4dd6be9d-...): Original 15, Engrossed 16, Enrolled 18, Act 19 in that order; Reengrossed at 17 NOT printed by my filter, not confirmed; `/ddp/enrollment` NOT re-checked. Say if you want either.
- Not done: Mac, search refresh, LA switch-on.
