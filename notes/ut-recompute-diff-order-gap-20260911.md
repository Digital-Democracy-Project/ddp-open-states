# ut is not actually done -- recompute-diff-order was held and never resumed

Two notes in a row (`va-committed-verified-20260911.md` and its predecessor) list "mi, ut,
fl, va done" -- traced this through the actual ops-handoff history and `ut` genuinely isn't
done. Flagging before `wa`/`us` land and this gets treated as fully closed.

## What actually happened, in order

1. `refresh-extraction ut --commit` ran (Step 1 of the plan) -- but its own note
   (`ut-refresh-extraction-diff-count-discrepancy-20260910.md`) found a real, never-explained
   discrepancy: `diffs_corrected=4110` vs. the prior dry-run's `diffs_would_change=4671`, on
   an *identical* stale-document set (`bills_with_stale_docs`/`stale_docs` matched exactly).
   That note explicitly said: **"Not proceeding to recompute-diff-order ut until this is
   understood... Holding at ut -- not running recompute-diff-order ut (Step 2/3) or moving
   to fl until this is resolved one way or the other."**
2. The investigation that followed (poppler version, the corrected go/no-go check) answered
   a *different* question -- whether the old poppler vs. new poppler produced meaningfully
   different results on `ut`'s already-committed data (answer: no, it holds up). That's a
   real and useful finding, but it's not the same question as the original 4110-vs-4671
   count discrepancy, which was never actually explained.
3. The next note said "resuming the backfill with fl next" and moved straight to `fl` --
   `recompute-diff-order ut --commit` (Step 2/3, required by the plan for all six
   jurisdictions: fl/us/va/mi/wa/ut) was never run at all.

## What's needed

1. `recompute-diff-order ut --dry-run` -- this has never been run in this whole thread
   either (only `refresh-extraction ut` has). Whatever it reports, this is a genuinely new
   step, not a re-check of something already done.
2. Worth a look at whether the original 4110-vs-4671 discrepancy has an explanation now,
   with fresh eyes and the fixed toolchain -- not required to unblock recompute-diff-order,
   but it was a real, flagged, unresolved question and shouldn't just be dropped.

Please correct "ut" back to not-done in tracking, and treat it as still needing its own
dry-run -> spot-check -> go-ahead -> commit cycle, same as fl/va/wa/us.
