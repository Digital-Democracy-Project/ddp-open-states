# RESULT (prod agent): dry runs for Kentucky, Maryland, Missouri, Maine, Georgia (nothing committed) and the Idaho refresh (committed). 2026-11-27 (production host, v99 core `1e138376`)

Ramon's go in my session: "GO for dry runs" (the five below) and "GO for Idaho" (re-run on v99, commit if the same). Dry runs wrote nothing; exact lines below.

**Idaho: COMMITTED 19:14 UTC** (restore point 19:11 UTC; no Idaho task, nothing near a trigger). The dry run on v99 was the same as the earlier one: `bills_with_stale_docs=400 stale_docs=438 diffs_would_change=23 docs_skipped=0 docs_refused=0`. Commit: `[COMMITTED] bills_with_stale_docs=400 stale_docs=438 diffs_corrected=23 docs_skipped=0 docs_refused=0`. A fresh dry run after: `stale_docs=0 diffs_would_change=0`. `recompute-diff-order id --dry-run` (not committed): `817 bills checked | unchanged=924 corrected=0 nulled=0`, `is_bill_version set=0 changed=0 not_a_version=56`, `diff_baseline_id set=0 changed=0 cleared=0`.

**Dry runs (all docs_refused=0, docs_skipped=0, exit 0):**
* **Kentucky** `refresh-extraction ky`: `bills_with_stale_docs=204 stale_docs=210 diffs_would_change=205` (your expectation: about 210).
* **Maryland** `refresh-extraction md`: `bills_with_stale_docs=951 stale_docs=955 diffs_would_change=886`.
* **Missouri** `refresh-extraction mo`: `bills_with_stale_docs=2205 stale_docs=2756 diffs_would_change=543` (your expectation: about 2,740).
* **Maine** `recompute-diff-order me`: `2368 bills checked | unchanged=2519 corrected=820 nulled=1792`; `is_bill_version changed=1792 not_a_version=1792`; `diff_baseline_id changed=820 cleared=1792` (matches your expectation exactly). Change list: 2,612 documents.
* **Georgia** `recompute-diff-order ga`: `5656 bills checked | unchanged=8472 corrected=649 nulled=0`; `is_bill_version changed=0 not_a_version=927`; `diff_baseline_id changed=0 cleared=0` (matches: 649, nulled 0, no version or baseline change).

Noise in the logs (PDF "Syntax Error/Warning" lines from the reader) did not affect any result. I have not committed any of these five; each commit holds for Ramon's go per state.

**Also to know:** the Iowa and Virginia loads logged "no usable filing figures for a successful run" (the `.imported` marker file is missing; the runs themselves reported success with 0 failed). Virginia `2026` finished 19:55 UTC (0 failed); `2026S1` is running.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
