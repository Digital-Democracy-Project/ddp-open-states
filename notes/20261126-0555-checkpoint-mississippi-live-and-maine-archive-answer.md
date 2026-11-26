# Checkpoint 11-26 05:55 UTC: Mississippi is live (#500); Maine's archive answer

Ramon approved the Mississippi rollout in this session ("Yes, roll out now", not waiting for OPEN-899).

## Mississippi go-live - DONE 05:50 UTC
* Gate: the diff of the deployed copy against main touched only Mississippi (10 lines in `ms:`): status live and the four switches on. Notes fetched again just before: nothing new on any branch.
* Dry run exited 0 (I used the script's skip of its cloud-task check; the manifest is read by modification time, as at the OR/ID/WY rollout).
* Real run: checkout file, api-v3 copy and the file inside the container all `db4d3a7c...` (equal); api-v3 healthy, no restart; core-pin drift exit 0; jurisdiction drift exit 0; `/schedule` 35 jobs (unchanged); ddp-sync's own read: `ms status live`, embedding, search refresh, smoke test and QA sweep true, `replica_routing` and `legbot_replica` false. Maine is still `scraping` (not in this change). The pull moved the checkout from `f96d5a057` to `333c27686`. No ddp-sync restart.
* Owed: the first embedding and search-refresh pass for Mississippi (hours), and the smoke test and QA sweep result.
* Left open as you said: the two unmatched Mississippi voter names (OPEN-899).

## Maine's archive (the second pass, `me-archive-26ea21311b85`)
* Pipeline done 04:35:32 UTC; the archive task took 91 s. Read from the task's own log: **2,450 bills checked, fetched 0, skipped 5,131, archived 0, fetch_errors 0, blocked 0, extract_errors 0, persist_errors 0**, status `ok`.
* The 5,131 skipped are the versions Maine's earlier archive (on the image with your OPEN-871 fix) already saved: that earlier run read fetched 5,131, archived 5,131, 0 errors. So this pass added no new documents because nothing was left to archive; the archive holds all 5,131.
* I have not counted the archive documents on the production side myself.
