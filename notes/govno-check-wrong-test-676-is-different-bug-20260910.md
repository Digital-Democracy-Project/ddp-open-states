# Go/no-go check result: 0/676 fixed — but the check itself was testing the wrong thing

Ran the proposed go/no-go check (`reextract ma --dry-run`) against the fixed toolchain
(Python 3.10.21 / poppler-utils 22.12.0, via a local throwaway build from `main` post-merge
`9b1651e` — see [[bare-host-venv-stale-too-plus-ecr-ask-20260910]] for why local-build
instead of pulling the real `v20`).

**Result: `ma: [DRY RUN] 676 errored docs checked | now_fixed=0 still_error=676 skipped=0`.
Zero improvement.**

## Root-caused directly, not taken at face value

Pulled 3 real sample documents from this population and traced the pipeline by hand inside
the container (raw bytes -> `pdftotext -layout` -> MA's `extract_line_numbered_pdf` regex
filter). All 3 are genuinely NOT bill text: a "Massachusetts Gaming Commission Revenue
Reports" cover letter and a "[County] Sheriff's Office Quarterly Population Report" (a data
attachment MA bills sometimes carry). Raw `pdftotext -layout` extraction with the NEW
poppler works completely fine on all 3 -- 82,533 / 392,495 / 74,978 characters of real,
readable text, confirmed by printing the actual content. But MA's
`extract_line_numbered_pdf` then runs `text_after_line_numbers` (a regex keeping only lines
that start with `\s*\d+\s+`, since real MA bill text is printed with left-margin line
numbers) -- and these 3 documents have ZERO such lines, because they aren't bill text and
were never going to have any, regardless of poppler version. `new_raw_text` is empty ->
`is_error` stays `True` for reasons that have nothing to do with PDF parsing quality.

**Conclusion: `reextract ma --dry-run` is not a valid go/no-go signal for PR #233.** The
676-row `is_error=True` MA population's real cause is a wrong-extractor-for-document-type
bug (these need a "non-bill-text attachment" handling path, or to be excluded from MA's
line-numbered extractor entirely) -- separate, pre-existing, and NOT something any poppler
version fixes. This is presumably the same "676 MA failures" population flagged earlier
this session as needing its own ticket/disposition, now root-caused.

## What this does NOT tell us

This is not evidence the Dockerfile fix is wrong -- it's evidence this specific check was
never capable of passing, for either poppler version. The actual poppler-version-sensitive
finding that started this whole hold (the `ut` `refresh-extraction` diff-count discrepancy,
and the `id=56173` before/after proof) lives in a DIFFERENT code path:
`refresh-extraction`/`recompute-diff-order`, which touches documents that are already
`is_error=False` (successfully extracted) but whose extracted *content* subtly differs
between poppler versions, affecting diff computation. `reextract` only ever looks at
`is_error=True` rows, which is a disjoint population.

## Holding, not resuming fl/va/wa/us

Need the go/no-go check re-specified against the actual mechanism the hold was about --
likely re-running `refresh-extraction ut --dry-run` (or similar) inside this fixed
toolchain and comparing against the original 4671/4110 discrepancy numbers, or directly
re-locating whatever document `id=56173` was and confirming which command flags it as
fixed. Not doing that unilaterally without checking in first, given the last time I acted
on a plausible-looking next step without asking (`ut`) it's exactly what prompted Ramon to
ask whether I'd gotten approval.
