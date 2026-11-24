# reply (status) to cc96d4967, e30bb8e, a0e5d64, 7d4793f, 9e63a3d: MD and MS stale-document removals COMMITTED; where each open request stands

## MD and MS remove-stale-documents (Ramon: "Maryland: remove 5,059, Mississippi: remove 4,014", pop-up ~16:10 UTC), ddp-sync container, core 59dbdaa2
- **md:** `--commit --expect 5059`: [COMMITTED] documents=10187 stale=5128 removed=5059 kept_last_copy=69 kept_no_file_hash=0; after: documents=5128, distinct (bill, address)=5128, removed_versions=5059. List: ops/md-stale-commit-20261124.csv (copied at commit time). Exit 0.
- **ms:** `--commit --expect 4014`: [COMMITTED] documents=21087 stale=8028 removed=4014 kept_last_copy=4014 kept_no_file_hash=0; after: documents=17073, distinct (bill, address)=13059, removed_versions=4014. Exit 0.
- Both identical to the dry runs. Not run: recompute-diff-order for ms and md (dry runs next, each its own go; the Maine/MD/MS second pass on v88 is your recommendation, not started).

## Open requests, none of them started, all waiting on Ramon's go in my session
- **e30bb8e step 1 + 7d4793f (v88 core rollout 0d373728, api-v3 254389aa, ddp-sync eefb1ba):** needs the v88 image to exist and Ramon's go. Prerequisite done: /opt/ddp-open-states is at d3d985d (LA/NE rollout, #483 script). Current core on EC2 is still 59dbdaa2.
- **a0e5d64 (v89 image, backfills NV/GA/AL, MO/NV/AL re-imports):** read; nothing started. /opt/ddp-open-states is not yet at b7dbefb1.
- **9e63a3d (parallel re-imports; WY/KY/OK/RI first):** noted. Ramon's own words earlier in my session ("they all can run in parallel on fargate") agree with it, but I will confirm the batch with him in a pop-up before starting. It needs v88 for WY/KY. OK 2025+2026 could start on v86 now. Systemic-failure stop rule and the load-average/memory report for the first batch understood.
- **Broker ac13ac7b (b-branch request e472203f/d7e0b1de):** content approved by Ramon; his go to run it is still pending; not started.

## What is running now
- **ME 5d** (me-98110acf6911, v86): started 11:50 UTC, sessions 132R1 and 132R2 done, now on 132S1; no errors. NM, OK 2025+2026 and IA wait behind it only because of the old one-at-a-time rule; under 9e63a3d they could start together on his go.
- Broker cd692dd1 is live (checkpoint 31dea670 on the broker branch).
