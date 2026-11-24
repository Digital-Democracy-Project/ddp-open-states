# status: ND refresh-extraction COMMITTED, RI relabel COMMITTED (21:00 UTC, core 70146fac); ND recompute dry run

Ramon's go in my session (pop-up ~20:58 UTC: "ND text refresh commit, RI relabel commit (2,222)"). I read your 64557d1 (dry runs match, commits on his go) before writing.

## ND refresh-extraction nd (ddp-sync container)
- **Backup first:** all ND documents, 2,690 rows (id, bill_id, version_note, sha256_hash, is_bill_version, diff_baseline_id, diff_from_previous_version, raw_text, updated_at), ops/nd-docs-backup-20261124.csv (42 MB, mode 600).
- Dry run again: `bills_with_stale_docs=616 stale_docs=1431 diffs_would_change=850 docs_skipped=0 docs_refused=0` (identical).
- Commit: `nd: [COMMITTED] bills_with_stale_docs=616 stale_docs=1431 diffs_corrected=850 docs_skipped=0 docs_refused=0`, exit 0. This tool has no --list or --expect, so I enforced the count by reading the dry run just before.

## ND recompute-diff-order nd (DRY RUN, after the refresh; nothing written)
- `nd: [DRY RUN] 1106 bills checked | unchanged=2690 corrected=0 nulled=0`; `is_bill_version set=0 changed=3 not_a_version=3`; `diff_baseline_id set=0 changed=0 cleared=0`; `change list ... (0 documents)`. Note the oddity I did not resolve: is_bill_version says changed=3 / not_a_version=3 but the list has 0 documents (md5 17ac60dd... is the empty list). Please read it against your range. I run no ND recompute commit.

## RI relabel ri
- Dry run again first: actions changed=2222, list md5 432712e9884763cd4c9a5e6771735df2 (same as before). `relabel ri --commit --expect 2222 --list ...`: `ri: [COMMITTED] actions changed=2222 unchanged=12103 | bills changed=0 unchanged=0`; `action: committee-failure -> (none): 2222`; bills' computed fields all 0. List ops/ri-relabel-commit-core70146fac-20261124.csv (2,222 rows, same md5, for --undo). Second dry run after: actions changed=0 unchanged=14325.
- RI recompute: nothing to commit (0), as you said.

## Maine archive
- Still running (started 20:31:30 UTC, ddp-scrapers-db:18); no end line yet at 21:00.
