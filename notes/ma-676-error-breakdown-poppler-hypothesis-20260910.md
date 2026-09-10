# Quantified: the MA 676 error breakdown strongly supports the poppler-version hypothesis

*Follow-up to `notes/poppler-version-confirmed-old-fleet-wide-implication-20260910.md`.* Ran a
full `reextract ma --dry-run` (all 676, this host's poppler 20.09.0) and counted every distinct
`Syntax Error`/`Syntax Warning` line across the whole run rather than just the first few:

```
122 x Syntax Error: Gen inside xref table too large (bigger than INT_MAX)
122 x Syntax Error: Couldn't find trailer dictionary
 61 x Syntax Error: Couldn't read xref table
 40 x Syntax Warning: Invalid Font Weight
  1 x Syntax Warning: Invalid number of shared object groups
  1 x Syntax Error: Expected the optional content group list, but wasn't able to find it, or it isn't an Array
```

`now_fixed=0 still_error=676` on this poppler -- every single one still fails here, no change
from your earlier per-document check.

## Why this matters for scope

The three big buckets (xref-table/trailer-dictionary parsing, ~200+ of the 676) are exactly the
class of poppler bug your two working examples hit -- and that last one-off line
(`Expected the optional content group list...`) is the *exact same warning* you saw on `SD 3423`,
which extracted fine for you anyway (poppler recovered and continued). That's a real signal, not
a coincidence: this isn't "these happen to also be malformed," it's the same failure signature
across a large share of the 676.

## What this suggests, not a conclusion

If the xref/trailer-dictionary bucket behaves like your two confirmed examples, a real fraction
of these 676 -- plausibly a large one, not just 2/5 -- may not be permanently dead content, just
poppler-version-sensitive. The remaining ~40 "Invalid Font Weight"-only warnings and the 3
confirmed genuine scans (no text layer at all) are a different, smaller, more clearly-real
population. Not re-testing all 676 against `26.04.0` myself -- that's your side to confirm at
whatever scale makes sense, given you're the one with the newer poppler and DDP-HOT access.

Still not proposing the upgrade path myself, same reasoning as before -- just making sure the
scale of what's potentially recoverable here is visible before anyone decides these 676 (or the
25+9 already handled) are truly a closed, accepted-loss case.
