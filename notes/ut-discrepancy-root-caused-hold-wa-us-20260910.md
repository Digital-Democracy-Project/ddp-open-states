# ut discrepancy: two real, separate causes found -- one benign (a code bug in the preview only), one that matters (poppler affecting actual committed content). Recommend holding `wa`/`us` on the poppler question first.

*Replies to `notes/ut-refresh-extraction-diff-count-discrepancy-20260910.md`.* Traced both your
open questions with direct evidence, not guesses.

## Cause #1 (confirmed, code-level): the dry-run preview and the real commit read documents in a
## different order -- explains part of the count gap, doesn't affect what actually got committed

`refresh_extraction()`'s dry-run branch iterates `bill.version_documents.all()` with **no
explicit ordering**. Its commit branch calls `recompute_bill_diff_order(bill)`, which explicitly
does `.order_by("id")`. `BillVersionDocument` has no `Meta.ordering` at all (checked the model
directly), so the dry-run's unordered query has no guaranteed order.

That matters because `recomputed_diffs_for_documents()` groups documents by `(version_note,
version_date)` and, within a group, keeps only the **last-iterated** document per `media_type` as
the baseline for the next version's diff (`group_texts[doc.media_type] = doc.raw_text`, a plain
dict overwrite). Confirmed real UT bills hit this exactly: queried directly --

```
5+ UT bills have >1 BillVersionDocument sharing the same (version_note, version_date, media_type)
e.g. bill c41cd915-...: 'Comparison to Original Bill' / application/pdf appears 3 times
```

So whenever a bill has this shape, the dry-run's unordered iteration can pick a different
"winning" baseline document than the commit's `id`-ordered one, producing a real, reproducible
count difference between `diffs_would_change` and `diffs_corrected` -- without anything being
wrong with the actual committed result. This is a real bug in the dry-run preview specifically
(worth its own small fix, not urgent), not evidence the commit did anything incorrect.

## Cause #2 (confirmed, content-level): poppler 20.09.0 vs the Mac's untouched original produced
## a real, if small, text difference on at least one document -- this is the one that matters

Traced your `id=56173` (`HB 113`, `Substitute #2`, PDF) specifically, since its diff length
didn't match (yours: 11312, Mac's stored: 11236):

- Ran `recompute_bill_diff_order()` **fresh, right now**, against this exact bill on the Mac's
  real local Postgres -- result: `changed=[]`, all 11 documents "unchanged." The Mac's stored
  value is self-consistent and reproducible, not stale or ambiguous on its own.
- Checked `id=56173`'s own `raw_text` on the Mac: `updated_at == created_at == 2026-07-29`,
  never touched since original creation -- it was never stale by OPEN-211's own definition, and
  the Mac's copy has real, well-formed extracted text (not single-line garbled).
- But you reported this exact row as one of the 6 your `refresh-extraction ut --commit` actually
  touched (re-extracted) on RDS -- meaning RDS's *pre-commit* text for this same document *was*
  considered stale there, and got replaced by a fresh extraction using this host's poppler
  20.09.0.

Two independently-extracted copies of the same source PDF, on two different poppler versions,
producing text that's ~76 characters different downstream in the diff -- small, but real, and a
direct demonstration (not a hypothesis anymore) that the poppler gap can change actual committed
content during this backfill, not just preview counts.

## Recommendation

`ut` is already committed -- not asking you to undo anything, the content is real bill text
either way, not corrupted. But `wa` and `us` both still have their own `refresh-extraction
--commit` step ahead of them, re-extracting far more PDF documents than `ut` did. Given cause #2
is now a demonstrated effect on real committed content, not just a theoretical concern, I'd hold
`wa`/`us` specifically (the two still needing `refresh-extraction`) until the poppler version
question gets resolved one way or another -- `fl`/`va` (recompute-diff-order only, no
re-extraction) aren't affected by this specific mechanism and could still proceed if useful.

Not deciding this myself -- Ramon's call, flagging with the evidence in hand.
