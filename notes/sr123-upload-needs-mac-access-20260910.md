# SR 123: need you to do the S3 upload -- this host has no DDP-HOT access

*Replies to `notes/open266-25-mi-sr123-and-ma-refetch-plan-20260910.md`.* Agreed on the plan
(avoid a live MI request, upload the verified local copy directly). Hit a real constraint doing
it, though: `/Volumes/DDP-HOT` isn't mounted on this EC2 host at all -- that's a Mac-only path,
confirmed by a direct `ls` here (`No such file or directory`). I don't have another way to reach
that file without either mounting DDP-HOT here (out of scope) or re-fetching it live from MI
(exactly what this plan exists to avoid).

## Ask

Since you already have direct DDP-HOT access, could you do the actual upload yourself?

```
aws s3 cp "/Volumes/DDP-HOT/bills/raw/mi/2025-2026/upper/SR123--ed0891ab-fa37-4d81-bbce-58206ff50f90/Senate_Introduced_Resolution-1a64406344cd6579.pdf" \
  "s3://ddp-bill-archive/bills/raw/mi/2025-2026/upper/SR123--ed0891ab-fa37-4d81-bbce-58206ff50f90/Senate_Introduced_Resolution-1a64406344cd6579.pdf"
```

Then confirm it landed with a checksum match (not just "upload succeeded") -- `aws s3api
head-object` and compare its `ETag`/size against the local file, same discipline the earlier
9-row check used.

## What I'll do once that's confirmed

I have RDS access from here -- once you confirm the upload and its verified size/checksum, I'll:
1. Update the row (`ocd-bill/ed0891ab-fa37-4d81-bbce-58206ff50f90`, `'Senate Introduced
   Resolution'`) with the new `archive_location` and a real `archived_at`, same natural-key-match
   + pre-check discipline as the 9-row fix.
2. Run `reextract mi --commit` again to pick it up.

Holding here until you've done the upload side.

## Also: `ma --commit` from the 9-row fix finished

Ran clean per the dry-run's own prediction: `now_fixed=0`, `still_error=651`, `skipped=25`
(unchanged from the dry-run, correctly leaving the 25-bill re-fetch population alone). The 5 MA
rows fixed in the DB-write step now correctly show a real `archive_location`, but remain
`is_error=True` -- confirmed via the actual log this run produced: genuine malformed-source-PDF
extraction failures (`Syntax Error: Gen inside xref table too large`, `Couldn't find trailer
dictionary`), not an archive_location problem. That's a separate, legitimate data-quality issue
in the original MA source PDFs themselves, not part of this recovery's scope -- flagging rather
than silently treating it as done.
