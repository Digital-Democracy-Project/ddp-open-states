# status: remove-stale-documents DRY RUNS for ms and md (read-only, Ramon: previews only), core 59dbdaa2, ddp-sync container

Nothing removed. Lists: ops/ms-stale-dry-20261124.csv and ops/md-stale-dry-20261124.csv.

- **ms:** documents=21087 stale=8028 **removed=4014** kept_last_copy=4014 kept_no_file_hash=0. After: documents=17073, distinct (bill, address)=13059, removed_versions=4014.
- **md:** documents=10187 stale=5128 **removed=5059** kept_last_copy=69 kept_no_file_hash=0. After: documents=5128, distinct (bill, address)=5128, removed_versions=5059.

Differences from what you expected, not diagnosed:
- MS: you expected about 8,000 removed. The tool marks 8,028 stale but would remove only 4,014 and keep the last copy of the other 4,014 (the file is the same one a current document keeps only once). So about 4,014 old "Current version" rows would remain after a commit.
- MD: 69 stale rows would be kept as the last copy of their file. I did not check whether any of them are Impact Note rows; counting the text "impact note" in the list file gives the number in my report line, which is a rough check, not proof.

Commit for either needs Ramon's second go with --expect <removed> and --list; not authorized, not run. recompute-diff-order for ms and md waits until after the removals, as you said.
