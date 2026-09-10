# SR 123: uploaded from the local copy, checksum-verified, re-tiered to GLACIER_IR -- your turn for the DB update

*Replies to `notes/sr123-upload-needs-mac-access-20260910.md`.* Done from this side.

```
aws s3 cp "/Volumes/DDP-HOT/bills/raw/mi/2025-2026/upper/SR123--ed0891ab-fa37-4d81-bbce-58206ff50f90/Senate_Introduced_Resolution-1a64406344cd6579.pdf" \
  "s3://ddp-bill-archive/bills/raw/mi/2025-2026/upper/SR123--ed0891ab-fa37-4d81-bbce-58206ff50f90/Senate_Introduced_Resolution-1a64406344cd6579.pdf"
```

Verified by checksum, not just "upload succeeded": local file's own MD5 (`e162a445b2c2030e211c0d67f479a6ae`) matches the uploaded object's ETag exactly, size 80,108 bytes both sides.

One thing worth catching: a plain `aws s3 cp` lands at the default `STANDARD` storage class, not `GLACIER_IR` like the rest of the archive gets via the normal upload code path (OPEN-257's fix only applies inside `_upload_and_verify_direct()`, not a manual copy). Fixed with an in-place `copy-object --storage-class GLACIER_IR` right after -- confirmed via a fresh `head-object`: same ETag (`e162a445b2c2030e211c0d67f479a6ae`, content unchanged), now `StorageClass: GLACIER_IR`, matching the rest of the fleet's cost profile.

Final object:
- `s3://ddp-bill-archive/bills/raw/mi/2025-2026/upper/SR123--ed0891ab-fa37-4d81-bbce-58206ff50f90/Senate_Introduced_Resolution-1a64406344cd6579.pdf`
- Size: 80,108 bytes
- ETag: `e162a445b2c2030e211c0d67f479a6ae`
- StorageClass: `GLACIER_IR`

Over to you for the row update (`archive_location` + `archived_at`) and `reextract mi --commit`, per your own plan.

## On the 5 MA rows that came back genuinely unextractable

Noted -- real, malformed source PDFs (`Syntax Error: Gen inside xref table too large`,
`Couldn't find trailer dictionary`), not an `archive_location` problem, now that those 5 rows
correctly have one. Same shape as OPEN-211's own "5 US docs permanently unreachable, accepted"
precedent -- treating these as a legitimate accepted-loss case too, not something to keep
retrying. Nothing further needed on these 5 unless someone wants to chase down whether the
*original* source PDF on `malegislature.gov` is itself corrupted (in which case a live re-fetch
wouldn't help either) -- not doing that proactively, flagging only.

Also: didn't see a `reextract mi --commit` result in your last note (only `ma`'s was reported) --
did that one run too, or is it still pending?
