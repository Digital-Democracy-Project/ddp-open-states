# Please correlate the 747 stuck rows against yesterday's runs before anyone decides on a backfill

*Replies to `notes/serious-finding-failed-uploads-permanently-stuck-20260910.md`.* Real, serious
finding -- filed on OPEN-263 (expanded its scope and acceptance criteria to cover both the
counter-visibility gap and this retry-eligibility gap, same root design issue, not fragmented
into a second ticket).

**Not deciding on a backfill yet, on purpose** -- per your own note, that's a real production
data-recovery call, not something to fold into the code-fix ticket or do without understanding
scope first.

## What to check before that decision can even be made

`BillVersionDocument.objects.filter(archive_location__isnull=True).count()` = 747, all-time. Please
narrow this down:

1. How many of the 747 have a `created_at` (or whatever timestamp reflects when the row was first
   inserted, not `archived_at` which is null for all of them by definition) falling within
   yesterday's two failed batches specifically -- roughly the windows covered by
   `notes/all-jurisdictions-batch-results-20260909.md` and
   `notes/rev21-persist-fixed-now-s3-putobject-iam-gap-20260909.md`.
2. For whatever remains (pre-existing nulls from before yesterday), a rough breakdown of *why* --
   extraction failures, older infra issues, anything you can tell from a quick group-by on
   jurisdiction/date, not a deep investigation. Enough to tell Ramon "X are yesterday's incident,
   Y are older and probably a different cause" rather than one undifferentiated number.

## Once that's back

That's the input Ramon needs to actually decide the backfill's scope (yesterday's subset only,
vs. all 747, vs. something else) -- not a decision to make from here. Hold on both the code fix
and the backfill until that's decided; re-running the validation batch again isn't useful right
now either, since the stuck rows will keep suppressing `fetched` for those jurisdictions until
either the skip-check is fixed or the backfill runs.
