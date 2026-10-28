# Amendment to the ddp-sync deploy request (`e2a18fa`): hold the restart until PR #251 is merged, so one restart also turns on the drift check

2026-10-28 (about 00:40 UTC). Ramon's instruction in this session. This **amends** `e2a18fa`; everything else in that note stands (wait for the 00:30 review, empty in-flight record, nothing due in 10 minutes, fast-forward only, rollback to `af6b098`, no secrets printed). **Nothing here is a new go for a different action.**

## What changed
* The drift check (OPEN-330) is a per-host flag, so it does **not** go in the shared `ddp-sync/credentials` secret (my earlier suggestion was wrong; SYNC-51 keeps those flags per host). It goes in this host's `infrastructure/docker-compose.prod.yml` `environment:` block, next to `OPENSTATES_PEOPLE_PULL_ENABLED`.
* **ddp-sync PR #251** adds `- JURISDICTION_DRIFT_CHECK_ENABLED=true` there (plus one sentence in `primitives.md`). It is open and **not merged yet**. Ramon merges it.

## Please do
1. **Do not pull and restart ddp-sync until PR #251 shows as merged** (`gh pr view 251 --repo Digital-Democracy-Project/ddp-sync --json state`), so the pull brings it in and one restart covers everything. If it has not merged by the time the 02:30 UTC WA launch is within 10 minutes, tell Ramon and wait; do not restart into a running scrape.
2. After the pull, confirm `git grep JURISDICTION_DRIFT_CHECK_ENABLED infrastructure/docker-compose.prod.yml` shows the line, then restart as in `e2a18fa`.
3. **Extra verification:** the live job list now includes the drift-check job (`OpenStates: jurisdiction list drift check`, 06:20 UTC) and the host's effective `jurisdiction_drift_check_enabled` is True. The restart also loses `session_pipeline_batch` (SYNC-135), as before. Do not trigger the check by hand; its first run is 06:20 UTC. After it, report what it logged (`jurisdiction_drift_check` lines and any Slack alert it caused: expect none if the lists agree; **note that this host's effective `DDP_OPENSTATES_JURISDICTIONS` includes MA and the broker's does not, so a finding about that list is possible and would be real, not a fault in the check**).
4. If the effective flag is still False after the restart, stop and report; do not edit the secret or `.env`.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
