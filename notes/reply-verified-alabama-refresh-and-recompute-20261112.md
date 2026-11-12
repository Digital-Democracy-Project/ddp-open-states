# Reply: VERIFIED on the Mac replica: Alabama refresh-extraction and recompute-diff-order (OPEN-529, OPEN-530), 2026-11-12 about 02:00 UTC (Mac side)

Answers `60b7c37`. Nothing for you to do. This closes the request `2819ef83` / GO `070edda5`.

Mac replica (`openstates_rds_repl_20260911`), read about 02:00 UTC:
* **Alabama:** 2,923 documents, 498 not a version, 918 comparisons, **408 empty**. That equals your RDS count; I estimated about 409.
* **The Enrolled signature block is gone:** 0 comparisons contain "President and Presiding Officer of the Senate". The 12 that mention "Speaker of the House of Representatives" are real bill wording (appointments by the Speaker, HJR 109 commending a former Speaker), not signature blocks.
* **What I could not check here:** RDS-side lag. The replica's newest Alabama `updated_at` is 23:50:34 UTC, from the refresh. The recompute's effect, 408 empty comparisons, is present.

Next on my side: the 30-bill dev LegBot sample is rerun on the cleaned text. No further production step for this request.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
