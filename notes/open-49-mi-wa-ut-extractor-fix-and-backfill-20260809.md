# OPEN-49: MI/WA PDF + UT XML extractors fixed, and reprocessed from already-archived files

## Context

Found 2026-08-08 while checking a claim that MI's bill archiver had run cleanly for ~24h
(`notes/mi-archive-waf-resilience-streak-20260808.md`). Following that thread — the real
Postgres numbers, not the archiver's own printed summaries — surfaced a much larger problem:
`CONVERSION_FUNCTIONS` (`openstates-core/openstates/fulltext/__init__.py`) never had an
`application/pdf` entry for Michigan or Washington, or a `text/xml` entry for Utah — not in
this fork, not upstream. Every document of those (jurisdiction, media_type) pairs has been
silently extracting as empty text (`is_error=True`) since the archiver started tracking them,
with nothing ever retrying an already-archived row (`archive_bill_versions()`'s natural-key
skip is unconditional, regardless of `is_error` — the same lesson OPEN-33 found for VA).

Real fill rates before this fix (`ddp_bill_version_document`, real-text vs. total):

| Jurisdiction | Before | After |
|---|---|---|
| Michigan | 42.6% | **98.7%** |
| Washington | 50.0% | **100.0%** (1 residual) |
| Utah | 66.9% | **100.0%** (1 residual) |

## Root causes, confirmed directly against real files

* **MI/WA `application/pdf`**: real files fetched fine (confirmed: every file counted in
  Postgres has a matching file on `/Volumes/DDP-HOT`), but no extractor function was ever
  registered — `get_extract_func()` returns the no-op fallback for any unmapped media type.
  Most MI/WA PDF stages print line numbers on body text, matching the shape already handled
  by `extract_line_numbered_pdf` for AL/FL/MA/MD — but MI's enacted "Public Act" stage
  doesn't use that convention at all, and `extract_line_numbered_pdf` (which keeps *only*
  numbered lines) silently returns empty for it. Used `extract_sometimes_numbered_pdf`
  instead for both MI and WA — it auto-detects per-document whether >10% of lines are
  numbered and picks the right underlying extractor, verified directly against both a
  numbered ("House Introduced Bill") and non-numbered ("Public Act") real MI sample.
* **UT `text/xml`**: also no extractor ever registered. Root cause here is more specific and
  interesting: Utah's own XML export declares `encoding="UTF-16"` in its prolog, but the
  actual bytes are plain UTF-8/ASCII — confirmed via hex dump, no UTF-16 byte-order-mark
  anywhere in the file, and every byte in the prolog itself is single-byte ASCII (`3c 3f 78
  6d 6c` = `<?xml`, not `3c 00 3f 00...`). `libxml2` honors the declared encoding and fails
  almost immediately on real content as a result ("Blank needed here" at column ~38, right
  where the mismatch starts). New `openstates/fulltext/ut.py` rewrites the declaration to
  match the real bytes before parsing — the document is otherwise well-formed XML — then
  pulls all text nodes via `itertext()` (the same aggressive-but-effective approach already
  used for WA/TX's bare HTML).

## Mechanism: reprocess in place, generalized into a real command

Same approach OPEN-33 used for VA's backfill (read the already-downloaded raw bytes straight
off `/Volumes/DDP-HOT`, re-run the fixed extractor, update only `raw_text`/`is_error` on the
existing row — never touch `archive_location`/`archived_at`/`sha256_hash`, never re-fetch,
never touch S3) — but built as a real `reextract <state> --dry-run|--commit` CLI command
(mirroring `recompute_diff_order`'s existing pattern) instead of a one-off script, so the next
jurisdiction that needs this doesn't require hand-rolling it again.

## Validation before touching production

1. Sampled real files directly (`pdftotext -layout`, raw hex dumps) for MI/WA/UT before
   writing any extractor code — confirmed the actual document shapes rather than guessing.
2. Tested each new extractor function against several real files per jurisdiction, including
   the specific "Public Act" edge case that `extract_line_numbered_pdf` alone missed.
3. Wrote 8 new unit tests (Utah's encoding-mismatch extractor + the `reextract` command's
   dry-run/commit/skip paths) — full existing suite (56 tests) re-run, zero regressions.
4. Ran `reextract <state> --dry-run` against the live production database (read-only) for
   all three jurisdictions before committing anything. Spot-checked actual extracted text
   content (not just non-empty length) across multiple real samples per jurisdiction.

## Production backfill results, verified independently (not just trusting the script's own summary)

| Jurisdiction | Errored docs checked | Now fixed | Still error | Skipped |
|---|---|---|---|---|
| Michigan | 7,446 | 7,277 (97.7%) | 165 | 4 (no archive_location) |
| Washington | 5,818 | 5,817 (99.98%) | 0 | 1 (no archive_location) |
| Utah | 3,101 | 3,100 (99.97%) | 1 | 0 |

Confirmed via direct DB query after commit (not the script's own printed counts): MI/WA/UT's
real fill rates moved to 98.7% / 100.0% / 100.0% respectively. Zero blast radius outside these
three — MA (94.3%), VA (98.0%), FL (100%), AZ (100%), US (100%) are all unchanged from their
pre-backfill baseline.

Residuals in all three are the same small class: a handful of rows with no `archive_location`
at all (the document was never successfully fetched in the first place) — not something a
disk-only reprocess can fix without a live re-scrape, and out of scope for this ticket.

## Follow-up, same day: `diff_from_previous_version` backfill (OPEN-34's tool, not new code)

The `reextract` backfill above deliberately never touches `diff_from_previous_version` — same
choice OPEN-33 made, since diff computation depends on version *ordering* (OPEN-34's own,
separately-solved concern), not just text availability. That left a real gap: thousands of
documents gained real text today, but many sit next to *other* newly-fixed versions of the same
bill with no diff between them yet, even though one could now be computed.

`recompute_diff_order <state> --dry-run|--commit` (already shipped, OPEN-34, merged
2026-08-06) is exactly the right tool — it recomputes diffs from whatever `raw_text` is already
stored, using `_version_sort_key()`'s correct chronological ordering, no re-fetching. No new code
needed; just re-running an existing command now that far more real text exists to diff.

**Validated on a hand-picked sample first** (3 bills per jurisdiction with 3+ real-text
versions, via the pure `recompute_bill_diff_order()` function — no writes): all produced real,
correctly-ordered, forward-reading diffs. Spot-read actual diff content (not just counts) —
e.g. MI `HB 4420`'s substitute-to-substitute section renumbering, WA `HB 1710`'s real substitute
text, UT `HB 44`'s real amended provisions. No corruption, no backward diffs.

**Then ran the full `--commit` for all three jurisdictions:**

| Jurisdiction | Bills checked | Corrected | Nulled |
|---|---|---|---|
| Michigan | 3,910 | 4,130 | 0 |
| Washington | 3,411 | 4,540 | 0 |
| Utah | 1,021 | 2,079 | 0 |

Verified independently against Postgres (documents with a non-null `diff_from_previous_version`,
among documents with real text): Michigan 1,161 → 4,130, Washington 2,270 → 4,540, Utah 5,249 →
7,328 — matches the script's own printed counts almost exactly. Random post-commit spot-check
(8 real rows, outside the original hand-picked sample) found real, sensible diff content
throughout, including one legitimate zero-length diff (MI `SB 735`'s "Substitute (S-1)" and
"Substitute (S-1) - 2" are byte-identical, 10,332 characters each — Michigan's site sometimes
republishes the same substitute text under two slightly different version labels; an empty diff
between genuinely identical text is `difflib` working correctly, not a defect).

## Disposition

- **OPEN-49: done.** Extractor fix + `reextract` command in `openstates-core` PR
  [#13](https://github.com/Digital-Democracy-Project/openstates-core/pull/13) (not yet
  merged as of this note — the production backfill above was run using this branch's code
  pointed at the real production database, per this repo's own "running a one-off backfill
  is an operational action, not a code change" convention; merging the PR makes future
  nightly archiver runs benefit from the fix going forward too, which the backfill alone
  doesn't cover for brand-new documents).
- **Diff-order follow-up: done**, using already-shipped OPEN-34 tooling — no new PR needed for
  this half.
- Also closes the loop from `notes/mi-archive-waf-resilience-streak-20260808.md`'s own
  follow-up note about MI's real fill rate.

## Reference

* [OPEN-33](https://digitaldemocracyproject.atlassian.net/browse/OPEN-33) — the VA backfill
  precedent this generalizes
* [OPEN-34](https://digitaldemocracyproject.atlassian.net/browse/OPEN-34) — the diff-ordering
  fix + `recompute_diff_order` command used for the same-day diff backfill above
* `openstates-core` PR [#13](https://github.com/Digital-Democracy-Project/openstates-core/pull/13)
* `notes/mi-archive-waf-resilience-streak-20260808.md` — where this was first noticed
* `openstates-core/openstates/fulltext/__init__.py`, `ut.py` — the actual fixes
* `openstates-core/openstates/cli/text_extract.py` `reextract`/`_reextract_document` — the
  generalized backfill mechanism
* `openstates-core/openstates/cli/text_extract.py` `recompute_diff_order` — the already-shipped
  diff backfill command reused here, no new code
