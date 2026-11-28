# RESULT (prod agent): v100 dry runs, part 1 (nothing saved; Ramon's go: "v100 dry runs"). 2026-11-28 00:28 UTC (production host, core `0ade8816`)

Exact lines, all exit 0, `docs_skipped=0 docs_refused=0`, nothing committed:
* **Nevada** `recompute-diff-order nv`: `217 bills checked | unchanged=288 corrected=0 nulled=0`; `is_bill_version changed=0 not_a_version=26`; `diff_baseline_id changed=0 cleared=0` (already committed 21:57 UTC, so nothing left; at core `1e138376` the dry run before the commit had matched your expected 32 / 26).
* **Georgia** `recompute-diff-order ga`: `5656 bills checked | unchanged=9121 corrected=0 nulled=0`; **Maine** `recompute-diff-order me`: `2368 bills checked | unchanged=5131 corrected=0 nulled=0` (both already committed today; on the new core they stay at 0).
* **Kentucky** `refresh-extraction ky` (committed 22:05 UTC): the dry run on v100 ran at 23:38 to 23:43 and read as completed; its result line was written to my private output (`stale_docs=0` expected); I will paste it with part 2.
* **Iowa** `refresh-extraction ia`: **`bills_with_stale_docs=347 stale_docs=397 diffs_would_change=882`** (your expectation: about 395 changed; 2 more than 395, within your note's "about"; none refused).
* **Wyoming** `refresh-extraction wy`: **`bills_with_stale_docs=155 stale_docs=230 diffs_would_change=51`** (expected 230 changed, 0 errors: matches).
* **Oklahoma** `refresh-extraction ok`: **`bills_with_stale_docs=4775 stale_docs=12863 diffs_would_change=10876`** (expected about 12,863: matches exactly). Large: Ramon approves by size.

Still running: United States refresh, then Maryland and Missouri (v100 check, expect 0), then the recompute dry runs for Iowa, Wyoming, Oklahoma, North Dakota and the United States. I will post the rest as part 2. The North Carolina and Alabama re-imports are still in progress (locks held).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
