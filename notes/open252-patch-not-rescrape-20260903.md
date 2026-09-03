# Correction to my own correction: MA does NOT need a full re-collection

*Replies to `notes/open193-open252-two-corrections-20260903.md`.*

Ramon pushed back on "needs a full re-run" -- right to. Re-checked properly instead of assuming
the only fix was re-scraping: **you can patch the already-collected data and retry, no
Fargate re-run needed.**

## What's actually true

OPEN-252's fix changes exactly one thing: `dedupe_key` on each `VoteEvent`. Every
`vote_event_*.json` already sitting in `ma-f08d7646b9fe`'s manifest has both fields the fix's
new formula needs (`dedupe_key`, `bill_identifier`) already present. Re-downloaded all 504 real
files from S3 and verified directly, not just reasoned about:

- The transform is exactly `new_dedupe_key = old_dedupe_key + "#" + bill_identifier` for every
  one of the 504 files (House PDF-branch and Senate PDF-branch both fit this -- confirmed by
  checking each file's `dedupe_key` against its own `sources[0].url`, no exceptions, no missing
  `bill_identifier`).
- Applied the transform locally and checked for collisions across the full batch:
  **504 unique keys after, zero collisions** -- including H4005/H4010 (Supplement #29), the
  exact pair that broke the original load.
- Checked `cloud_loader.py`: no per-object checksum/hash verification against the manifest --
  it downloads whatever bytes currently exist at each listed S3 key and imports them. A patched
  file loads exactly like a freshly-scraped one; nothing in the pipeline would notice or reject
  the edit.

## What I'm asking you to do (I don't have safe write access for this myself)

I have `s3:PutObject` on `ddp-openstates-scraper-memory` but not `s3:DeleteObject`, so I didn't
want to test-and-litter production S3 with throwaway objects -- and this ultimately writes into
production RDS, same reasoning as everything else this session routes through you rather than me.

For every `vote_event_*.json` under `working-tier/ma/ma-f08d7646b9fe/ma/`:
1. Read the object.
2. Set `data["dedupe_key"] = f'{data["dedupe_key"]}#{data["bill_identifier"]}'`.
3. Write it back to the same key.

Then retry `cloud_loader.py ma ma-f08d7646b9fe` exactly as before -- no re-scrape, no new
run_id needed. Should take a few minutes total (S3 read/write for ~504 small JSON files, plus
the load itself, which your last attempt showed takes well under half an hour before it would
have hit the same collision point).

Sanity check before you commit to it: re-verify the "504 unique / 0 collisions" result
independently once you've pulled the real objects on your end, rather than trusting my count
alone -- cheap to redo, and this is exactly the kind of claim ("no re-collection needed") I got
wrong once on this same ticket already tonight.
