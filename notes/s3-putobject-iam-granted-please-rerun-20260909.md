# IAM grant added -- please re-run the full batch once more

*Replies to `notes/rev21-persist-fixed-now-s3-putobject-iam-gap-20260909.md`.* Ramon added a new
statement to `ddp-scraper-task-role`'s policy granting `s3:GetObject`/`s3:PutObject` on
`arn:aws:s3:::ddp-bill-archive/bills/raw/*` (alongside the existing `ddp-openstates-scraper-memory`
statement, untouched). Confirmed added, not just requested.

## Please re-run

Same all-9-jurisdiction batch, task-definition `ddp-scrapers:21` (unchanged -- this was purely an
IAM gap, not a code/image issue, so no new build needed), fresh RUN_IDs.

## What to check this time

- `s3_verified` should finally come back nonzero for `az`/`ma`/`mi`/`us` (the four that had real
  `archived` counts last run) -- if it's still 0 or `s3_unverified` is still nonzero, capture the
  real error line the same way as last time, don't assume the grant alone fixed it.
- Spot-check at least one real uploaded object in `ddp-bill-archive` directly
  (`aws s3api head-object` or similar) and confirm its `StorageClass` is `GLACIER_IR` -- this is
  the literal end-to-end proof the original Step 3 ask has been chasing for two days.
- Whether `us` completes clean again (SYNC-58's dropped-connection crash didn't recur last run,
  but one clean run isn't confirmation it's fixed -- keep watching, don't declare it closed).

If this comes back clean, that closes out the OPEN-192 Fargate archive validation for real --
please write that up plainly as the final status for this whole thread if so, since a lot of
people/notes have been following it since yesterday afternoon.
