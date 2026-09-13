# OPEN-283 (MA recovery): Ramon's decision + PR #144 merged

## MA vote-event dedupe conflict -- Ramon's decision: manually patch the one saved record

Ramon chose option 2 (not a full re-scrape): manually patch the one saved record, then retry
the load.

**Root cause, confirmed from the actual code** (not a guess anymore -- traced through
`openstates-core`'s `VoteEventImporter.get_object()`/`base.py`'s `import_item()`, and
`openstates-scrapers`' `ma/bills.py`):

- `_house_vote_dedupe_key()` in `ma/bills.py` already has a fix for this exact bug class
  (OPEN-252): the key format is `"{housevote_pdf}#{n_supplement}#{bill_identifier}"` --
  3 segments, folding in the bill identifier specifically because MA's House Supplement #29
  (2025-04-09) is legitimately cited by BOTH H4005's and H4010's "Passed to be engrossed"
  actions, and `VoteEvent.bill` is a single FK so each bill needs its own row.
- The conflicting record in your staged manifest (`ma-cabb8f2478b7`, from the 2026-09-06
  collection) has `dedupe_key: 'https://malegislature.gov/Journal/House/194/2025/RollCalls#29'`
  -- only **2** segments (URL + supplement number), missing the bill-identifier segment
  entirely. That's the pre-OPEN-252-fix format. So this specific run's staged data was
  collected with scraper code that predates the fix (even though the fix has since landed and
  even patched the *historical* S3 objects already imported before it -- this run's data just
  wasn't part of that patch and wasn't recollected with the fixed scraper).

**The patch**: find the specific manifest object(s) for this vote event in
`s3://ddp-openstates-scraper-memory/working-tier/ma/ma-cabb8f2478b7/` and rewrite their
`dedupe_key` field to the correct 3-part format, folding in the actual bill identifier each
one belongs to (H4005 vs H4010, whichever the conflicting pair turns out to be -- confirm from
the record's own bill reference, don't assume). Same technique as the original OPEN-252
in-place S3 patch. Then retry `cloud_loader.py ma ma-cabb8f2478b7`.

## PR #144 (git-missing-from-runtime-image fix): merged

Confirmed via GitHub directly: merged (`bd4fe5b7`). Please rebuild/redeploy `ddp-sync`'s image
and trigger `openstates_people_refresh` for real again -- fourth attempt, hopefully the clean
one. Same as before: hold on removing the legacy crontab until a real success is observed.
