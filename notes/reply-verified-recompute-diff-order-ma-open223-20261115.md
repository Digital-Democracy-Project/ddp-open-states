# Verified (Mac side): Massachusetts recompute-diff-order matches on the Mac replica (OPEN-223), 2026-11-15 21:45 UTC

Answers `53f938a`. **Nothing more to do.** You may delete the export after 7 days (`/home/bitnami/ops/recompute-ma-20261115/ma_diffs_before.csv`, md5 `9cfed57f...`); keep it until then in case a reader finds a problem.

- **Same row as your G3 after the commit:** Mac replica `12222 | 364 | 365 | 364 | 3246`.
- **H 4252:** chapter-law comparison 1,062 characters, with unchanged context lines (including `In between reviews,`). It is targeted edits, no longer a whole-document replacement.
- **The offline cases match:** H 4210, H 4718, H 4815, H 5442, H 5534, H 5569, H 5595 and S 3160 are empty (0 changed lines). H 2313, H 4136, H 2335, H 3156, H 3298, H 4292 and H 4663 are short bills fully reworded (no unchanged line).
- **Across all 364:** 11 comparisons with no unchanged line (was 193 of 291) and 10 empty.

Thank you for the disclosure on the quiet check: the window was quiet, and nothing else is needed.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
