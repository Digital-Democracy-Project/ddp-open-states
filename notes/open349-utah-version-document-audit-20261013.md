# OPEN-349: Utah version-document audit (which note families belong in OPEN-224's exclusion)

Date: 2026-10-13. Read-only: queries against the local OpenStates Postgres (`openstates`, port 5433) and a read of `openstates-core` `origin/main`. Nothing was changed, no stored data touched. Follow-ups: OPEN-350 (add the entries), OPEN-351 (recompute), SYNC-110 (ddp-sync's old-text choice, ddp-sync PR #219).

## Answer

Add two families to Utah's entries in `openstates-core/openstates/utils/version_ordering.py`. Everything else in Utah's vocabulary stays in the diff lineage.

```python
# _PROCEDURAL_DOCUMENT_NOTE_PATTERNS["Utah"] today:
re.compile(r"\A(house|senate) amendment [1-9]\d*\Z", re.IGNORECASE)

# proposed (the dict holds one pattern per jurisdiction, so it is one alternation):
re.compile(
    r"\A("
    r"(house|senate) amendment [1-9]\d*"
    r"|comparison to (original bill|sub #[1-9]\d*)"
    r"|amended excerpts \d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2}:\d+"
    r")\Z",
    re.IGNORECASE,
)
```

The two families rest on **different evidence**, and the second is a judgment call that OPEN-350's reviewer should make with open eyes:

| Family | Meets OPEN-224's own standard (length)? | Other evidence |
|---|---|---|
| `Amended Excerpts <ts>` | **Yes.** Max 10,114 chars (bills) against full-text maxes around 1M; every classification stays under 10,200 | Named "Excerpts"; all 368 have a full `Amended <ts>` version with the identical timestamp in the same bill |
| `Comparison to Original Bill` / `Comparison to Sub #N` | **No.** Median 21,731 (bills) against 23,035 for `Substitute #N`; max 593,304 against 1,018,572. Length cannot separate them | Not a clean version (see below); collides with `Substitute #N` in the sort order; 32.6% of Utah's changelog targets |

## What is in Utah's archive

All 762 distinct Utah notes fall into exactly seven families; no note is left over. Counts are documents with non-empty text and `is_error = false`, bills and resolutions together; lengths are characters, bills only.

| Family | Documents | Stored diff | Min | Median | Max |
|---|---|---|---|---|---|
| `Introduced` (xml + pdf) | 2,042 | 0 (the lineage's first document) | 658 | 12,331 | 986,367 |
| `Substitute #N` (xml + pdf) | 2,328 | all | 865 | 23,035 | 1,018,572 |
| `Enrolled` (xml + pdf) | 1,094 | all | 865 | 17,466 | 1,014,787 |
| `Amended <ts>` (xml + pdf) | 736 | all | 1,193 | 16,513 | 1,017,710 |
| `Comparison to Original Bill` / `Comparison to Sub #N` (pdf only, 7 distinct notes) | 2,239 | all | 704 | 21,731 | 593,304 |
| `Amended Excerpts <ts>` (pdf only, 367 distinct notes) | 368 | all | 181 | 753 | 10,114 |
| `House/Senate Amendment N` (pdf only) | 563 | **0** | 114 | 738 | 13,232 |

- **OPEN-224's Utah entry is active.** All 563 `House/Senate Amendment N` documents carry no diff, matching the 563 that OPEN-224 recorded as nulled.
- **Resolutions** (concurrent, joint, plain) were checked separately, as OPEN-224 required. `Amended Excerpts` stay short in every classification (max 1,902 outside bills). `Comparison to …` resolution documents (67 in all) are smaller than the same classes' `Substitute #N` / `Enrolled`, by median: concurrent 648 against 5,137 / 3,500, joint 2,172 against 10,563 / 6,350, plain 9,066 against 10,067 / 3,498. That points the same way as the bills' content evidence below; it is a small population and not decisive on its own.
- **The adjacent family that must stay in** is `Amended <ts>` (full text, 736 documents, min 1,193, max 1,017,710). It shares a prefix with `Amended Excerpts <ts>` and is the Utah analogue of Virginia's "Substitute" next to its "Amendment". The excerpt pattern requires the literal word "excerpts" and does not match it.
- `Introduced`, `Substitute #N` and `Enrolled` match neither pattern. Checked against every distinct Utah note: the comparison pattern matches exactly 7 notes (2,239 documents), the excerpt pattern exactly 367 (368 documents), no note matches both, and no note naming "comparison" or "excerpt" is missed.

## The redline documents are not clean versions (evidence beyond length)

From a random sample of 250 bills that have `Introduced`, `Substitute #1` and `Comparison to Original Bill` as PDFs of 3,000 to 150,000 chars, the 220 with at least 20 changed 5-word shingles each way were compared against the two real drafts:

| What the Comparison document contains | Median | p10 | p90 |
|---|---|---|---|
| Wording only in the old text (deleted) | 29% | 0% | 54% |
| Wording only in the new text (inserted) | 43% | 16% | 63% |
| Wording in both (unchanged) | 58% | 48% | 72% |
| Its own wording found in **neither** draft | 17% | 14% | 23% |
| Length against `Substitute #1` | 0.68 | 0.56 | 1.21 |

It holds struck-out and inserted wording together, plus part of the unchanged text, with no markup to say which is which. It is neither the old text, the new text nor a clean diff, so a changelog built on it cannot tell added from removed. The 17% in neither draft is probably extraction and layout noise; the shingle method also under-counts matches across differently typeset PDFs, so read these as lower bounds. HB8's redline at about half the length (the prod agent's example) is within the spread, not the typical case.

## What it does to the changelogs

Of the 3,574 changelog targets api-v3 would offer for Utah (versions whose chosen document has a non-empty diff, one per version as api-v3 chooses it):

| Target | Count | Share |
|---|---|---|
| Real draft (`Substitute`, `Enrolled`, `Amended <ts>`) | 2,042 | 57.1% |
| `Comparison to …` | 1,164 | 32.6% |
| `Amended Excerpts <ts>` | 368 | 10.3% |

(The prod agent's 9% was a different measure: both sides of a pair real, over the 1,543 changelogs already written. This is the new side only, so it is higher.)

**Sort-key collisions.** `note_stage` and `version_sort_key` give `Comparison to Sub #N`, `Substitute #N` and `House Amendment N` the identical key `(1, '', N)`, and `Amended Excerpts <ts>` the same key as the `Amended <ts>` full text it sits beside. Their relative order in the lineage was whatever the database returned. Today **471 of Utah's 1,021 bills** have versions in the lineage that share a key (586 tied groups of `Comparison to Sub #N` with `Substitute #N`, and 368 of `Amended Excerpts` with `Amended <ts>`). With both families excluded, **0 of 1,021**. That is how the report's pairs came out in both directions (`Comparison → Substitute` 374, `Substitute → Comparison` 259).

## Cost of the entries (OPEN-224's AC5 count)

2,239 `Comparison to …` documents and 368 `Amended Excerpts` documents carry a stored diff today, so 2,607 diffs become `None` on a recompute; the diffs of the real drafts that followed them change too. How many is OPEN-351's dry run to report; the code change alone changes nothing already stored.

## Found on the way (not decided here)

1. **`Amended <ts>` versions are ordered by the wrong number.** `extract_ordinal` takes the last number in the note, which for `Amended 2/12/2026 10:02:409` is `409`. Of the 74 Utah bills with two or more `Amended <ts>` versions, **47** sort differently by that number than by the timestamp in the note. Excluding the two families does not touch this. Needs its own ticket; whether timestamp order is the true chronology is an assumption.
2. **"No diff" does not by itself mean "excluded".** The lineage's first document (Utah's `Introduced`) has no diff either. ddp-sync's SYNC-110 relies on that distinction when it works out which version a diff was taken against.

## How this was done

- Length distribution: the query documented in `version_ordering.py` (the block commented "Length-distribution audit query") for `j.name = 'Utah'`, with `array_to_string(b.classification, ',')` added to split bills from resolutions, and `percentile_disc(0.5)` for the median.
- Families: one `CASE` over `version_note` with POSIX versions of the patterns above; a zero-row `OTHER` branch confirmed nothing was left over.
- Changelog targets: `DISTINCT ON (bill_id, version_note, version_date)` ordered `text/xml` first, then `application/pdf`, as api-v3 chooses (`_archived_row_for`), keeping those with a non-empty diff.
- Collisions: `version_sort_key` and `is_procedural_document` imported from `openstates-core` `origin/main`, applied to every Utah (bill, note, date).
- Redline overlap: 5-word shingles, seed 349, as described above.
- A replay of `archive_bill_versions()`'s lineage rules over the stored documents reproduced which rows carry a diff for every Utah document (2,019 of 2,019 in bills without ties); it is described in ddp-sync PR #219.

## Not decided here

Whether `Comparison to …` should be excluded on content rather than length is for OPEN-350's review. The other seven jurisdictions are OPEN-352 to OPEN-360.
