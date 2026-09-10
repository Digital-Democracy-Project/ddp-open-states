# OPEN-266: plan for the last 26 rows (MI SR 123 + the 25 missing MA bills)

*Follow-up to `notes/open266-checked-all-35-nine-fixable-now-20260910.md`.* Ramon approved both
of these -- please hold off on the 9-row fix's own separate track (already in flight) and treat
these as two more items, not urgent relative to each other.

## MI SR 123: upload the local copy directly -- no live MI request needed at all

We already have a real, valid copy of this file (`/Volumes/DDP-HOT/bills/raw/mi/2025-2026/upper/
SR123--ed0891ab-fa37-4d81-bbce-58206ff50f90/Senate_Introduced_Resolution-1a64406344cd6579.pdf`,
confirmed a genuine 80,108-byte PDF, not a placeholder). Since MI is the fleet's most
WAF-sensitive jurisdiction, avoiding an unnecessary live request to it is worth the extra step
here rather than lumping this in with the MA re-fetch below.

1. Upload that exact local file to `s3://ddp-bill-archive/bills/raw/mi/2025-2026/upper/SR123--
   ed0891ab-fa37-4d81-bbce-58206ff50f90/Senate_Introduced_Resolution-1a64406344cd6579.pdf`
   (matching key, so it lands exactly where the archiver would have put it), verified the same
   way a normal upload is (checksum match, not just "upload succeeded").
2. Update the row (`ocd-bill/ed0891ab-fa37-4d81-bbce-58206ff50f90`, version_note `'Senate
   Introduced Resolution'`, matched on its current natural key) with the new `archive_location`
   and a real `archived_at`.
3. Run `reextract mi --commit` (same command already used for the 9) -- it'll pick this row up
   now that `archive_location` is set, same as the others.

## The 25 missing MA bills: genuine live re-fetch, using the existing archiver, no new task def

These 18 SD bills (SD4137-SD4171) and 7 HD bills (HD5879-HD5911) -- full list in
`notes/open266-35-row-identifiers-and-paths-20260910.md`, everything not in the 9-row or SR-123
groups -- aren't recoverable from anything checked (not on DDP-HOT, not in S3). Ramon's call:
re-fetch them for real, using the existing archiver, not a new tool or a new task definition.

**No new Fargate setup needed.** These 25 aren't a "discover a new bill" problem -- we already
have every one of their exact source URLs from the existing `BillVersionDocument` rows. What's
blocking a retry is that a row already exists for each (with `is_error=True`), which the current
skip-check treats as permanently done regardless of content, the same class of problem OPEN-263
fixed for the `is_error=False` case. The fix:

1. Delete these 25 specific `BillVersionDocument` rows (matched precisely on their own natural
   key -- bill + version_note + version_date + source_url -- from the identifier list already
   given, not a broader `is_error=True` sweep). Once gone, the skip-check sees no existing row
   at all for these links and treats them as brand new.
2. A normal `archive ma` run against the already-proven task-definition revision 23 will then
   naturally attempt these 25 along with everything else in its regular full sweep -- no
   `--session`/single-bill targeting needed, since `archive()` already walks every MA bill each
   run. Whenever convenient, or MA's own regular schedule will pick it up -- your call on timing,
   just flagging it shouldn't collide with a scheduled MA run already in flight (same
   `ps`/schedule check you'd normally do before triggering anything against a jurisdiction).

**Expected outcome, and one honest caveat:** most should come back clean the same way the earlier
100-row batch did. But a few might fail extraction again for a genuinely different reason than
before -- if a PDF is scanned/image-only with no real text layer (confirmed to happen for real,
e.g. some AZ committee PDFs), a clean re-fetch will still extract nothing. That's a legitimate,
different-in-kind result, not evidence the re-fetch itself failed -- worth distinguishing in
whatever you report back (`is_error=True` again after a confirmed clean fetch/persist/upload =
genuinely unextractable content, not a retry candidate; anything that fails at fetch/persist/
upload itself is the more interesting case worth a closer look).
