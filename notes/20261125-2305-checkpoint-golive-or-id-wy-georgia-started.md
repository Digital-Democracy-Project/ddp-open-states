# Checkpoint 11-25 23:05 UTC: Oregon, Idaho, Wyoming are live; Georgia 2025_26 full run started

Ramon approved three things in this session: the go-live of OR, ID, WY, the Georgia 2025_26 full run, and Georgia 2026_ss then Iowa 2026s1.

## Go-live OR, ID, WY (#496) - DONE 23:01 UTC
* Gate: the only difference between the deployed copy and main was those three states (15 lines). Dry run exited 0. I used the script's skip of its cloud-task check because Arizona, Alabama and the Maine/Maryland/Mississippi passes are collecting; the file is only read by mtime, same as the 22:27 rollout.
* Real run: checkout, api-v3 copy and the file inside the container have the same md5 (8744b07a...). api-v3 healthy, no restart. Drift check exit 0. Schedule still 35 jobs. ddp-sync's own read: OR, ID, WY status live, embedding, search refresh, smoke test and QA sweep true; replica_routing and legbot_replica false. No ddp-sync restart. The pull also brought #497 (docs only).
* Owed: first embedding and search-refresh pass per state, smoke test and QA sweep results.

## Georgia 2025_26 full run - STARTED 23:02:40 UTC
* Trigger answered 202 for `ga?full=true&sessions=2025_26`. One try; no retry without telling you. Will report start/end times, final counts and the archive end line.
* Order after it finishes: Georgia 2026_ss, then Iowa 2026s1 (one at a time).

## Your question on a 12-hour limit
My role cannot read ECS task definitions (access denied on the describe call), so I cannot read a runtime limit there. Not verified; Ramon will be told in session.
