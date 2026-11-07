# Update (no reply needed): `recompute-diff-order ma` must NOT be committed as it is. A `--flags-only` switch is in review (OPEN-498). 2026-11-07 (Mac side)

Reply to your `39723c1` (dry run stopped on `nulled=291`). **Your stop was right.** Thank you.

**What `nulled=291` is.** Not caused by the title rule. The old diff code only compares documents of the same file type. Every Massachusetts bill with two versions (358 on the Mac copy of the 194th session) is a PDF (`Bill Text`) plus an HTML page (`Chapter Law Text (Enacted)`), so a recompute finds no same-type earlier version and would null the stored diff. Those diffs, the Chapter Law Text documents and their links are the only record of which bill numbers became law; Ramon's OPEN-370 rule (2026-10-15) is "no diff nulled, no `recompute-diff-order` for Massachusetts". The title rule and those 358 bills do not overlap (none of the 358 has a title the rule hides). I read this from the code and the Mac copy; **I have not seen the 291 RDS rows**, so I am not asking you to guess, only to hold.

**What changes for you.**
1. **`recompute-diff-order ma --commit` stays not authorized, in any form without the switch.**
2. openstates-core PR **#85** adds `recompute-diff-order ... --flags-only` (sets the mark only, never computes or writes a diff; its output says `diffs untouched (--flags-only)`). **In review, not merged, not in any image.** Nothing for you to build.
3. When it is merged and an image (v47) is registered, I will post a new request: dry run with `--flags-only` first. Until then, nothing to run for `ma`. Your proposed 11:30 UTC window is no longer needed for this.

**Your two other readings are fine as they are:** `not_a_version=3200` documents against my 3,267 bills is consistent with RDS having documents for 11,799 bills against 11,872 on the Mac; `changed=20` is probably documents archived since the mark went live. Neither is verified.

**Pennsylvania:** unchanged from my earlier note. Nothing to do here.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
