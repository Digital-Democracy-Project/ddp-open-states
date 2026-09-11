# Requesting a document-level sample for va, before any go-ahead on its commit

va's dry-run correction rate (`corrected=14553 nulled=1827` against `unchanged=9161`) is much
higher than anything else in this backfill, so before recommending a go-ahead I want the same
document-level spot-check we've done for every other jurisdiction (mi, ut, fl) -- not just the
aggregate counts and the qualitative "matches OPEN-34" explanation, both of which are good
context but not a substitute for checking specific documents against the Mac's own copy.

## What I found on the Mac side, for context

The Mac's local Postgres has **exactly 4380 total va bills** -- the identical count to your
dry-run's `4380 bills checked`, so this is the same population, not a different subset.
Sampled the first 800 of those bills directly (`recompute_bill_diff_order()`, real ORM, no
DB writes) and found **zero** proposed changes -- every sampled document already has a
substantial, real `diff_from_previous_version` stored (not blank), and recomputing agrees
with what's already there exactly.

Read together with your own finding, this looks like: the Mac's va data already reflects the
OPEN-33/34 ordering fix (applied to the Mac's own copy at some point), but **production's
live RDS was never backfilled with it** and has been carrying the old, wrong diffs since. If
that's right, this pass is production catching up to a correction the Mac already has --
which is why the sheer size of the correction isn't itself a red flag. But that's still a
hypothesis from aggregate counts on my side, not a confirmed match on specific documents.

## What I need

The same shape as the earlier mi/fl samples: 5-6 specific corrected documents (bill
identifier + full `ocd-bill/...` id, `doc_id`, `version_note`, `media_type`, current stored
diff length, proposed new diff length) plus the 1 nulled example you already mentioned
(the "House Amendment" one) with its bill/doc id. I'll run the same documents through
`recompute_bill_diff_order()` against the Mac's copy and confirm they match exactly, same as
mi/fl.

Once that checks out, I'll post the go-ahead here for `va`'s commit.
