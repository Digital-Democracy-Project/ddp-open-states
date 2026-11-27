# RESULT (prod agent): Maryland saved, Idaho recompute has nothing to save, v100 gates read. 2026-11-27 (production host)

**Maryland refresh COMMITTED 22:17 to 22:54 UTC** (Ramon's go): fresh pre-commit dry run equal to the earlier one (`stale_docs=955`, 951 bills, 886 comparisons), `[COMMITTED] bills_with_stale_docs=951 stale_docs=955 diffs_corrected=886 docs_skipped=0 docs_refused=0`, then a dry run reading `stale_docs=0 diffs_would_change=0`. Kentucky, Maine, Nevada and Georgia were reported earlier; **Missouri's commit is running** (pre-commit dry run first, then the commit, then a check-after dry run; I will post its lines when done).

**Idaho recompute (Ramon's go to commit):** the dry run still reads `unchanged=924 corrected=0 nulled=0; is_bill_version changed=0 not_a_version=56; diff_baseline_id changed=0` : **there is nothing to write** (the refresh commit already corrected the 23 comparisons), so I did not run a commit.

**v100 rebuild gates (Ramon's go; I start only when no save or load runs, so after Missouri):** image `v100` digest `sha256:bbb7b79df59ec8d94b4a3ec1b698c145a3057c82f77cb31e60cacc3392bb1ad0`; its recorded core commit (`DDP_CORE_COMMIT`) is exactly `0ade881650ca921b0d7f3d5e4a64dc25239ac5ce`; the md5 of `scrapers/or/bills.py` (`891402e3...`) and `scrapers/nc/bills.py` (`ffbfc1fd...`) in the image equal those files at scrapers `744f02125ff272080f98271d34f0104a436da72f`, which is also scrapers `main`'s tip, so I use it as `DDP_SCRAPERS_SHA`. Then api-v3 and ddp-sync at `0ade8816`, the pin check, and the Alabama re-import after the rebuild (Ramon's go too).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
