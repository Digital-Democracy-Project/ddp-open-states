# status: Maine archive STARTED on v89 (20:31:30 UTC); ND refresh-extraction and RI relabel/recompute DRY RUNS (core 70146fac, nothing written)

Ramon's "go" in my session (20:30 UTC), after my list of the three waiting items (Maine archive, ND dry run, RI dry runs).

## Maine archive (OPEN-871)
- POST openstates-archive/me at 20:31:30 UTC, 202. The archive task runs as **ddp-scrapers-db:18 (v89)**, started 20:32 (describe-tasks), no ME pipeline lock or other ME run at the time. I will post its counts line and duration when it ends (Maryland's took 5,144 s). Pass line is yours (`fetched=N archived=N` with N about 5,131, 0 blocked, few fetch_errors).

## ND refresh-extraction nd (dry run, core 70146fac in the ddp-sync container)
- `nd: [DRY RUN] bills_with_stale_docs=616 stale_docs=1431 diffs_would_change=850 docs_skipped=0 docs_refused=0`, exit 0. Your expectation: 1,431 changed, 0 errors. I did not see an "unchanged" figure (this tool's line has none) so I cannot compare your 1,259. The commit waits on Ramon's separate go.

## RI relabel ri (dry run)
- `ri: [DRY RUN] actions changed=2222 unchanged=12103 | bills changed=0 unchanged=0`; `action: committee-failure -> (none): 2222`; bills' computed fields: first_action_date=0 latest_action_date=0 latest_action_description=0 latest_passage_date=0; exit 0. List: ops/ri-relabel-dry-core70146fac-20261124.csv (2,222 rows, md5 432712e9884763cd4c9a5e6771735df2). Please tell me the range you expect; the commit (with --expect and --list) waits on Ramon's second go.

## RI recompute-diff-order ri (dry run)
- `is_bill_version set=0 changed=0 not_a_version=0`; `diff_baseline_id set=0 changed=0 cleared=0`; 0 documents. Nothing to recompute after the stale removal. Never run before the stale removal, as you said; the removal was committed earlier today (3,011 rows).

## Also running
- HI, MO, KY (rev 91), IA (rev 90) and OK's 2026 session (rev 91): all collecting, none loading, no errors.
