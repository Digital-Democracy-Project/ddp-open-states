# RESULT (prod agent): v100 dry runs, part 2 (nothing saved; core `0ade8816`; all exit 0, none refused). 2026-11-28 04:12 UTC (production host)

Part 1 is in `270b6c1`. **These ran on v100; v101 supersedes them, so I will re-run what you list on v101 after the rebuild** (the rebuild waits: Pennsylvania's nightly run holds its lock from 04:00 UTC).
* **United States** `refresh-extraction us`: **my capture lost the result line** (the script's filter kept only `EXIT 0`; the run took 00:27 to 03:28 UTC). I will re-run it on v101 and save the raw output.
* **Maryland** `refresh-extraction md`: `stale_docs=0 diffs_would_change=0` (committed earlier today). **Missouri** `refresh-extraction mo`: `stale_docs=0 diffs_would_change=0` (committed earlier).
* **Iowa** `recompute-diff-order ia`: `4284 bills checked | unchanged=6189 corrected=442 nulled=0`; `is_bill_version changed=0 not_a_version=0`; `diff_baseline_id set=290 changed=152 cleared=0`; change list 442 documents. (Run before any Iowa refresh commit.)
* **Wyoming** `recompute-diff-order wy`: `335 bills checked | unchanged=1295 corrected=0 nulled=0`; `not_a_version=845`; baselines 0 (also before the refresh commit, so nothing to change yet).
* **Oklahoma** `recompute-diff-order ok`: `6005 bills checked | unchanged=7682 corrected=7261 nulled=2631`; `is_bill_version changed=3272 not_a_version=3272`; `diff_baseline_id set=3882 changed=3379 cleared=2631`; change list 9,892 documents.
* **North Dakota** `recompute-diff-order nd`: `1106 bills checked | unchanged=2042 corrected=648 nulled=0`; `not_a_version=3`; baselines 0; change list 648 documents: **matches your expected 648 Enrollment changelogs, no others.**
* **United States** `recompute-diff-order us`: `39449 bills checked | unchanged=92819 corrected=999 nulled=0`; `is_bill_version changed=0`; `diff_baseline_id set=752 changed=316 cleared=0`; change list 1,068 documents.
Also done since my last note: your four Florida reads (`f73a125`), the readiness checks, and the v101 read: digest `sha256:93c79600...`, core `1f6b4ca86e0ad780e259bc6495f2a77549d59eae`, and the md5s of `scrapers/mt`, `ia` and `nv` `bills.py` equal scrapers `cb8aef70...` exactly. Ramon approved the v101 rebuild and the dry runs; I start when Pennsylvania's lock clears.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
