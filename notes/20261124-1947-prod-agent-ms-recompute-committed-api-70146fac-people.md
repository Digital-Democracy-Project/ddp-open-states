# status: MS recompute COMMITTED; KY people loaded, NE people load FAILS on a 350-character note; RI stale preview; EC2 api-v3 at core 70146fac (ddp-sync waits for OK/IA loads)

Ramon's go in my session (pop-ups ~19:35 UTC: MS recompute commit, previews, people loads, core rollout; and "70146fac, once" for the core target, replacing 0d373728 as in ea0ef64).

## MS recompute-diff-order (core 59dbdaa2)
- Dry run again first: identical numbers (4,014 bills checked, unchanged 15198, corrected 453, nulled 1422, is_bill_version changed 1429 / not_a_version 1429, cleared 1422, 1,875 documents; the list has the same rows, only the order differs).
- Backup before commit: ops/ms-stored-comparisons-backup-20261124.csv (1,875 rows, mode 600).
- Commit: [COMMITTED] with the same lines, 1,875 documents. List: ops/ms-recompute-commit-core59dbdaa2-20261124.csv. Exit 0.

## RI remove-stale-documents (dry run only, nothing removed)
- ri: documents=6389 stale=3011 removed=3011 kept_last_copy=0 kept_no_file_hash=0; after: documents=3378, distinct (bill, address)=3378, removed_versions=3011. List: ops/ri-stale-dry-20261124.csv. The commit waits on Ramon's second go. ND refresh-extraction dry run: not run, because it needs the core with OPEN-836 on the host (loader is still 59dbdaa2).

## People (people checkout fast-forwarded 05d7e4cc -> 37bcb364, as you asked)
- **KY:** safe run: "updated person from .../ky/legislature/Chris-Lewis-7da80b33-....yml", processed 347 person files, 0 created, 1 updated. Real run: same, exit 0.
- **NE: the safe run FAILS**, nothing written: `django.db.utils.DataError: value too long for type character varying(300)` on an INSERT. The only Nebraska change in 37bcb364 is Fred Meyer's file: start_date 2026-01-15 plus a new source link whose `note:` is **350 characters** (measured on the diff line); I think that is the value, but I did not see the column name in the traceback. I did not edit the file, shorten anything or touch the schema, and I did not run a real NE load. Please shorten the note to 300 characters or less (or tell me what you want).
- ME's people file (Theriault, OPEN-854) also changed in 37bcb364; Ramon's go named NE and KY only, so I did not load ME people.

## EC2 api-v3 (core rollout part 1)
- /opt/ddp-open-states/api-v3 fast-forwarded 7a2e5e0 -> 254389aa (#77, #78, #79, #80; no schema change). Rollback tag ddp-openstates-api:pre-core70146fac = b78c0e6e2d3f. Rebuilt with DDP_CORE_SHA=70146facdb8493d990415ee9deff19200c4e4777: compose exit 0, 20 s, down about 8 s, healthz 200 at 19:46:49 UTC.
- I read the two newer notes (aabe9b8, 8af412c) only after starting the rebuild; neither changes the core target.
- check-core-pin-drift --image-core 70146fac...: exit 1 for now. Only ddp-sync's loader (59dbdaa2) disagrees; it exits 0 after the ddp-sync rebuild.
- **ddp-sync rebuild (eefb1ba+, DDP_CORE_SHA=70146fac..., DDP_SCRAPERS_SHA=b2aa844d...) is NOT done**: OK 2025+2026 and IA 2026,2026s1 are still running on rev 90 (a restart during a load leaves an orphan 24 h lock). I wait until both have finished loading, and I hold IA 2025 until after the rebuild. Not between 02:15 and 04:45 UTC.
- Mac api-v3 is yours.

## Not started
- v89 steps (backfills, re-imports on rev 91), Maine archive (after the ddp-sync rebuild), WY (waits for the OPEN-874 image), RI stale commit, and the ND dry run.
