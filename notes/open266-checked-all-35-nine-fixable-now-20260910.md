# OPEN-266: checked all 35 directly against DDP-HOT and S3 -- 9 are a safe, easy fix; 1 odd one; 25 need a real decision

*Replies to `notes/open266-35-row-identifiers-and-paths-20260910.md`.* Checked every one of the
35 paths against `/Volumes/DDP-HOT` directly (this Mac has it mounted), then checked all 35 again
against the real S3 bucket (`aws s3api head-object`, not inferred) since DDP-HOT is only a
downstream mirror of S3, not authoritative on its own. Full breakdown:

## 9 rows: already uploaded successfully -- the DB just never got told. Please fix these now.

Confirmed via `head-object` against `ddp-bill-archive`: real object, correct size, `GLACIER_IR`
storage class (only reached after `_check_etag()`'s own verification already passed at upload
time -- these were never unverified). All 9 uploaded in the same ~22-second window
(`2026-09-09T00:08:38Z` - `00:09:00Z`), strongly suggesting a single earlier batch run where the
upload step itself worked but something dropped the DB write that should have recorded
`archive_location` afterward -- worth someone's attention as its own root-cause question
separately, but not blocking the fix itself.

| bill | version_note | source_url | s3 key | size | uploaded (UTC) |
|---|---|---|---|---|---|
| WA HB 1344 (`ocd-bill/3cbdbbf0-cbcb-404a-bc73-c1542fdfdca3`) | Bill | `http://lawfilesext.leg.wa.gov/Biennium/2025-26/Pdf/Bills/House%20Bills/1344.pdf` | `bills/raw/wa/2025-2026/lower/HB1344--3cbdbbf0-cbcb-404a-bc73-c1542fdfdca3/Bill-5de6c758faf7a0ad.pdf` | 60473 | 00:11:15 |
| MA SD 2674 (`ocd-bill/b81b87c7-4fba-45a8-b6e2-6424f775e313`) | Bill Text | `https://malegislature.gov/Bills/194/SD2674.pdf` | `bills/raw/ma/194th/upper/SD2674--b81b87c7-4fba-45a8-b6e2-6424f775e313/Bill_Text-1cf8a4c0ace043f2.pdf` | 10411260 | 00:08:46 |
| MA HD 4496 (`ocd-bill/291095a5-2cda-47ad-b52d-bcacc04ebf6a`) | Bill Text | `https://malegislature.gov/Bills/194/HD4496.pdf` | `bills/raw/ma/194th/lower/HD4496--291095a5-2cda-47ad-b52d-bcacc04ebf6a/Bill_Text-710203bb4b6c35e6.pdf` | 8390408 | 00:08:38 |
| MA HD 4478 (`ocd-bill/5b906c08-74c8-48cc-b4e0-2ed129d92fa8`) | Bill Text | `https://malegislature.gov/Bills/194/HD4478.pdf` | `bills/raw/ma/194th/lower/HD4478--5b906c08-74c8-48cc-b4e0-2ed129d92fa8/Bill_Text-0f0bffbb74616ad0.pdf` | 10137105 | 00:08:39 |
| MI HB 5619 (`ocd-bill/77d4f464-2c1d-4ba3-90c5-ee37bd920711`) | As Passed by the House | `https://legislature.mi.gov/documents/2025-2026/billengrossed/House/pdf/2026-HEBH-5619.pdf` | `bills/raw/mi/2025-2026/lower/HB5619--77d4f464-2c1d-4ba3-90c5-ee37bd920711/As_Passed_by_the_House-6c27ca9e3fa9b34d.pdf` | 10052155 | 00:08:43 |
| MI SB 878 (`ocd-bill/3f025cc5-541e-4432-a3ad-0e2b1ba52c69`) | As Passed by the Senate | `https://legislature.mi.gov/documents/2025-2026/billengrossed/Senate/pdf/2026-SEBS-0878.pdf` | `bills/raw/mi/2025-2026/upper/SB878--3f025cc5-541e-4432-a3ad-0e2b1ba52c69/As_Passed_by_the_Senate-a38461efdf9e837c.pdf` | 9533668 | 00:08:51 |
| MA SD 3423 (`ocd-bill/e925b909-f662-4281-ab15-0b888b9f3c9d`) | Bill Text | `https://malegislature.gov/Bills/194/SD3423.pdf` | `bills/raw/ma/194th/upper/SD3423--e925b909-f662-4281-ab15-0b888b9f3c9d/Bill_Text-fa4da0e3d7fdc12b.pdf` | 11039773 | 00:08:40 |
| MI SB 2 (`ocd-bill/d5700e15-5da2-431e-801c-fe96ffb77285`) | Substitute (S-1) | `https://legislature.mi.gov/Home/GetObject?objectName=2025-SCVBS-0002-0J218.pdf` | `bills/raw/mi/2025-2026/upper/SB2--d5700e15-5da2-431e-801c-fe96ffb77285/Substitute_S-1-87b1f776cf1c92df.pdf` | 11254008 | 00:09:00 |
| MA SD 2680 (`ocd-bill/ea1beb3f-3881-463c-b489-1208fee102b6`) | Bill Text | `https://malegislature.gov/Bills/194/SD2680.pdf` | `bills/raw/ma/194th/upper/SD2680--ea1beb3f-3881-463c-b489-1208fee102b6/Bill_Text-b586058c8bf01010.pdf` | 8729453 | 00:08:45 |

**Requested fix, two steps, no code change, no live traffic:**

1. For each of these 9 rows (matched on the row's own existing natural key -- `bill` +
   `version_note` + `version_date` (as currently stored, not assumed) + `source_url`, exactly as
   given above), set `archive_location = "s3://ddp-bill-archive/<key>"` (the key above) and
   `archived_at` to the object's real `LastModified` timestamp shown above -- a direct DB write,
   nothing re-uploaded, nothing re-fetched. Please diff/dry-run this against the real rows first
   (confirm each one's current `archive_location` is still `None` and the natural key still
   matches before writing) rather than trusting this table blindly.
2. Once step 1 lands, run `reextract ma --commit` and `reextract mi --commit` (no `--session`
   filter needed, or filter to `194th`/`2025-2026` if you'd rather be narrow) -- this is the
   existing OPEN-49 command, unmodified, and it'll only touch rows with `is_error=True` AND a
   real `archive_location`, so it's safe to run broadly; it'll naturally pick up these freshly-
   fixed rows (and leave every other still-null-`archive_location` row alone, untouched, exactly
   as it did before). `wa` has no `reextract` need here since WA's HB 1344 is the only WA row in
   this batch and doesn't need extraction re-run unless it's also `is_error=True` on the DB side
   -- check that first; if it's already `is_error=False`, step 1 alone finishes it.

## 1 row: on DDP-HOT locally, but NOT in S3 -- genuinely unclear, not part of this fix

MI SR 123 (`ocd-bill/ed0891ab-fa37-4d81-bbce-58206ff50f90`, 'Senate Introduced Resolution',
`https://legislature.mi.gov/documents/2025-2026/resolutionintroduced/Senate/pdf/2026-SIR-0123.pdf`)
-- the local file exists on DDP-HOT (a real, valid 80KB PDF) but a direct `head-object` against
the expected S3 key comes back not-found. Don't know why yet (deleted from S3 since upload?
never uploaded but locally persisted some other way? DDP-HOT sync picked it up from somewhere
else?) -- leaving this one alone for now, being looked at separately, not part of the 9-row fix
above.

## 25 rows: genuinely missing everywhere checked -- not part of this fix either

All MA. Not on DDP-HOT, not in S3. These would need an actual re-fetch from `malegislature.gov`
if recovery is wanted at all -- using the jurisdiction's existing single-bill scrape targeting,
not new code, per Ramon's explicit direction. Not deciding on that here; being looked at
separately. Full identifier list already in `notes/open266-35-row-identifiers-and-paths-
20260910.md` (everything in that note not listed in the 9-row or 1-row tables above).

## Please only touch the 9 for now

Ramon's instruction: fix the 9 easy ones now, hold off on the SR 123 anomaly and the 25 missing
ones while we look at those separately.
