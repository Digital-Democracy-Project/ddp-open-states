# Reply: recompute-diff-order la, Part 1 (dry run) — STOPPED, not committed (2026-11-09 02:13 UTC, prod agent)

Answers request 847405cf. Ramon's go (relayed) and the user's own go in this session were both given; the stop condition fired, so nothing was committed.

**G1 code:** run from openstates-core `6641dda7` (worktree on PYTHONPATH; `note_stage` gives (2,0.0) (2,1.0) for Engrossed / Reengrossed). Not the v50 task image.
**G3 baseline (read-only):** 10,468 docs; is_bill_version true 7,140 / false 3,328 / null 0; 2,599 bills; 4,541 with a diff; fingerprint b2fd5c70e579d17b4e315b1c6e91d2b6. All as expected.

**Dry run (13 s):**
- `la: [DRY RUN] 2599 bills checked | unchanged=9147 corrected=1266 nulled=55`
- `la: [DRY RUN] is_bill_version: set=0 changed=55 not_a_version=3383`

**Against your stop conditions:**
- not_a_version 3,383: OK
- nulled 55 (limit 80): OK
- **corrected 1,266: BELOW the allowed 1,411–2,400 → STOP.** The order fix alone was predicted at about 1,411, so the footer cleaner should only have added to it. Possibly the order fix is not applying to all comparisons, or the 55 nulled reports overlap the corrected set. I did not guess.
- No other state mentioned, no error or Traceback.

**Not done:** no commit, no api-v3 update (Part 3 follows Part 2). Nothing changed on production. Waiting for the dev's call on whether 1,266 is acceptable.
