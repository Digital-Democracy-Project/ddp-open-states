# Reply: ddp-sync `2ea2c06` is LIVE on the EC2-broker host, with SYNC-140 included (answers `1e2daf8d3f`), 2026-11-02 02:44 UTC

**The operator chose option C and also told me to restart** ("pull ddp-sync up to main and restart"), so SYNC-140's code is now deployed on this host along with the OPEN-318 line.

- **Before:** I saved the container log (`ddp-sync-pre-sync140-20261102T0241Z.gz`) and tagged the running image `ddp-sync:pre-sync140` (`0983a2244561`, the rollback). Washington's scheduled 02:30 run had finished cleanly at 02:37 (scrape and archive); only Massachusetts was in flight.
- **Pull:** `git checkout -- infrastructure/docker-compose.prod.yml` (my 4 local lines), then `git merge --ff-only` to `2ea2c06`. `git status` is clean and `docker-compose.prod.yml:84` reads `- JURISDICTION_MANIFEST_MODE=authoritative`.
- **Restart:** `sudo systemctl restart ddp-sync` at 02:41:56 UTC; healthy at about 02:44 (2 minutes). New image `d374619e205d`.
- **After:** the log says `jurisdiction_manifest_agrees ... mode=authoritative` (manifest mtime `2026-11-02T01:32:44`), `Scheduler started with 19 jobs`, and the routed list is AZ FL MA MI NC US UT VA WA. The SYNC-140 code is in the image (`request_id` is in `legbot_client.py`). 0 `Traceback` or `[error` lines since the start.
- **Massachusetts survived the restart:** `cloud_scrape: resuming a Fargate job orphaned by a previous restart jurisdiction=ma run_id=ma-d2c298dde063`, the same ECS task, still running. I did not launch it again. **From the code (not observed):** the saved record carries the per-state wait setting (86,400 s), and the resumed wait starts again from the restart, so it should be allowed up to 24 h from 02:43 UTC. I will watch it.

**Not run:** nothing exercising SYNC-140 itself (research-alone, the request id and redo through LegBot): no such trigger was requested. Tell me if you want a check.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
