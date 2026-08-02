# Virginia bill-text extraction: confirmed root cause and fix (2026-08-02, OPEN-15)

## What was broken

Every archived Virginia bill-version document was `is_error=True` with empty `raw_text` — 11,100
`application/pdf` rows and 12,899 `text/html` rows, all of them, per the real archive query in
OPEN-15. Found while verifying OPEN-9 (Virginia's `diff_from_previous_version` noise-cleaning
ticket), which is blocked on this.

## Root cause, confirmed against real data (not guessed)

`CONVERSION_FUNCTIONS["va"]` (`openstates-core/openstates/fulltext/__init__.py`) only ever mapped
`text/html` to `extractor_for_element_by_id("mainC")`, and had no `application/pdf` entry at all.

Fetched real, current 2026 Regular Session documents directly from `lis.blob.core.windows.net`
(via `lis.virginia.gov`'s public `LegislationText/api/GetLegislationTextByIDAsync` endpoint —
no production DB access needed) for three bills spanning both chambers and a resolution: **SB56**,
**HB1**, **HJ1**.

1. **VA's HTML is now a bare `<p>`-tag fragment.** All three real HTML documents have no
   wrapping `<html>`/`<body>`, and no `id` or `class` attribute anywhere on the page at all —
   `id="mainC"` doesn't exist, confirming the site was rebuilt (VA's whole LIS system moved to a
   React SPA over `lis.virginia.gov` backed by Azure blob storage — the old
   `lis.virginia.gov/cgi-bin/legp604.exe` URLs, still the only thing in
   `openstates/fulltext/raw/va.csv` before this fix, are dead). `extractor_for_element_by_id`'s
   underlying `text_from_element_lxml` (`openstates/fulltext/utils.py`) asserts exactly one match
   for `.//*[@id='mainC']` and raises on every real page — caught by `archive_bill_versions()`'s
   per-document `except Exception`, producing `is_error=True`/empty `raw_text`.

2. **A second, real bug found during diagnosis: mojibake.** Because these fragments declare no
   charset anywhere, `lxml.html.fromstring(bytes)` falls back to guessing an 8-bit encoding and
   mangles every non-ASCII character. Confirmed directly: a real `§` citation and real em-dashes
   in patron lines came back as `Â§` / `â€”`-style sequences unless the bytes are decoded as UTF-8
   *before* parsing. This would have silently corrupted `raw_text` for nearly every VA bill even
   after fixing the missing-element problem above.

3. **The PDF gap is real, and VA's PDFs are genuinely line-numbered.** Downloaded a real VA PDF
   and ran it through the actual `pdftotext -layout` binary `pdfdata_to_text()` shells out to —
   confirmed sequential line numbers continuing across pages, matching the existing
   `extract_line_numbered_pdf` pattern already used for seven other states (al, id, ky, ma, md,
   mo, ut, pa, fl). The PDFs were already being fetched and archived to S3 (per
   `archive_bill_versions()`), just never extracted — `get_extract_func()`'s `KeyError` fallback
   for an unmapped media type always returns `""`.

## Fix

- New `openstates-core/openstates/fulltext/va.py` — `handle_virginia_html()`, following the same
  per-state-module precedent as `de.py`'s `handle_delaware`. Decodes as UTF-8 before parsing (the
  fix for the encoding bug), walks `.//p`, joins `text_content()`. Deliberately not implemented by
  reusing the shared bytes-typed `extract_from_p_tags_html`/`text_from_element_siblings_lxml`
  helpers, so the UTF-8 decode is fully isolated to Virginia and cannot change behavior for any
  other jurisdiction's HTML extraction.
- `CONVERSION_FUNCTIONS["va"]` now maps `text/html` to `handle_virginia_html` and
  `application/pdf` to the existing `extract_line_numbered_pdf` (no new PDF-extraction code
  needed).
- `openstates-core/openstates/fulltext/raw/va.csv` (previously all dead 2017 URLs) got 6 new
  rows — HB1/SB56/HJ1, HTML + PDF each — using the real, current FileURLs captured above, so the
  repo's own `os-text-extract sample va` / `test` self-check exercises real current data.
- New `openstates-core/openstates/fulltext/tests/` (no test coverage existed for
  `openstates.fulltext` before this) with real-fixture-backed tests pinning both the missing-
  element fix and the encoding fix.

## Verification limits in this environment

This work was done in a disposable CodeBot workspace clone with no live production Postgres and
no working `poetry`-managed venv for `openstates-core` (only Python 3.14 available; the project's
pinned dependency stack — Django, `influxdb-client`'s `dateutil`/`six` chain, `black` 23.1.0 —
doesn't resolve cleanly against it). Verified instead via: a lightweight direct import of
`openstates.fulltext` (no Django/instrumentation import chain) proving `get_extract_func()`
resolves correctly end-to-end for all 6 real fixtures; the new pytest suite (5/5 passing); `flake8`
clean; and a `git diff` confirming only Virginia's `CONVERSION_FUNCTIONS` entry changed. Could not
run the full `os-text-extract sample/test` CLI or a real `os-text-extract archive va` pass in this
workspace — that (and the final confirmation of `is_error=False` rows in the live
`ddp_bill_version_document` table) should happen on the next real archive run after this ships.

## References

- Jira [OPEN-15](https://digitaldemocracyproject.atlassian.net/browse/OPEN-15)
- Jira [OPEN-9](https://digitaldemocracyproject.atlassian.net/browse/OPEN-9) — blocked on this,
  can now proceed once this ships
- `openstates-core/openstates/fulltext/__init__.py`, `va.py`, `common.py`, `utils.py`
