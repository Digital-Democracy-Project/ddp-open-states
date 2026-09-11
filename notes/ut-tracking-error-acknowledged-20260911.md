# Acknowledged: ut tracking error, thank you for catching it

Confirmed by tracing the actual note history myself (didn't just take your word for it):
you're exactly right. `notes/ut-refresh-extraction-diff-count-discrepancy-20260910.md`
explicitly held `recompute-diff-order ut` pending investigation; the follow-up root-cause
note only cleared `wa`/`us`'s hold, never `ut`'s; the next note moved straight to `fl`. I
never re-checked that `ut`'s hold had actually been lifted before reporting it as done, and
kept carrying that error forward through fl and va's completions. Corrected my own tracking
now (not retroactively rewriting what happened, just marking it correctly going forward).

`ut` goes back into the queue with its own full cycle: `recompute-diff-order ut --dry-run`,
spot-check sample, go-ahead, commit, verify -- same as every other jurisdiction. Will run
the dry-run once the current `us refresh-extraction` dry-run clears (don't want to add more
concurrent Fargate load than necessary while that's still running, though it's isolated so
not strictly blocking).

Also noting your second ask -- whether the original 4110-vs-4671 discrepancy has a cleaner
explanation now, with fresh eyes and the fixed toolchain. Will take a look once `ut`'s new
dry-run is in, since that'll be the first fresh signal on `ut`'s data since the fix landed.

Thank you for tracing this all the way through instead of just flagging the discrepancy --
this kind of "a later note about a different question gets mistaken for clearing an earlier
hold" error is exactly the kind of thing that's easy to miss under a stack of increasingly
recent context.
