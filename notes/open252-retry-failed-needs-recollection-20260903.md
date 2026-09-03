# ma retry against the existing manifest failed identically -- OPEN-252's fix needs a re-collection, not just a re-load

*Replies to `notes/open252-ma-vote-dedupe-root-cause-20260903.md`.*

Retried `cloud_loader.py ma ma-f08d7646b9fe` directly (user confirmed no re-scrape involved --
verified the ECS cluster was empty throughout, nothing hit `malegislature.gov` again). It failed
with the **identical** error:

```
openstates.exceptions.DuplicateItemError: attempt to import data that would conflict with data
already in the import: {..., 'dedupe_key': 'https://malegislature.gov/Journal/House/194/2025/
RollCalls#29', ...} (already imported as Passed to be engrossed on H 4005 in Massachusetts 194th
Legislature (2025-2026))
{"source": "ma", "run_id": "ma-f08d7646b9fe", "status": "failed", "phase": "import", "duration_s": 1478}
```

Same `dedupe_key`, same H4005/#29 collision, same everything -- this is expected, not a new
bug. OPEN-252's fix (folding `bill.identifier` into the dedupe_key) runs at **scrape time**,
inside `HouseVoteRecordParser.createVoteEvent()` -- it changes what a *future* collection
writes into each VoteEvent's serialized JSON. The existing manifest's JSON files were written
by the *old*, buggy scraper code before the fix existed, so they still carry the old
(colliding) dedupe_key baked in. Re-running the import against that same, already-serialized
data can't pick up a fix that only changes what gets serialized in the first place.

**The commit's own claim -- "the load can be retried directly against it without re-running the
collection" -- doesn't hold**, confirmed by direct evidence now, not just reasoning about it.
MA genuinely needs a full re-collection (the ~8.2h Fargate run) with the fixed scraper code for
OPEN-252 to actually take effect. Once that's re-run and produces a fresh manifest, *that* one
should load cleanly.

Not re-triggering the collection myself without confirming that's actually wanted, given the
real cost (another ~8h Fargate run) -- your call on timing.
