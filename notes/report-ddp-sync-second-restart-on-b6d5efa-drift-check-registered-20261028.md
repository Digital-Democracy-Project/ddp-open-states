# Report: ddp-sync pulled to b6d5efa and restarted a second time (00:43 UTC); the drift check is registered for 06:20 UTC

Prod agent, Wed 2026-10-28 00:50 UTC. The operator said "Option A, do both now" in my session, after my earlier report that I had restarted before seeing your amendment. Before acting I re-read all four branches (nothing new that touched this) and re-ran the gates: in-flight 0, no ddp-sync activity beyond its own cadence catch-up, no broker writers, next launch WA 02:30. Output in `/home/bitnami/ops/ddp-sync-restart-20261028T0017Z/`.

* Pulled (fast-forward only): `334f2df` to **`b6d5efa42cca64bed04aba19c5722043f6b07931`** (PR #251). `git grep JURISDICTION_DRIFT_CHECK_ENABLED infrastructure/docker-compose.prod.yml` shows the line. Old log saved.
* Restart issued **00:43:11**; `systemctl` returned after 6 s; container started 00:43:17; **healthy after 71 s**.
* **Live jobs: 18 before, 19 after; the one new job is `jurisdiction_drift_check` ("OpenStates: jurisdiction list drift check"), next run 2026-10-28 06:20:00 UTC.** Log: `jurisdiction_drift_check: registered sync_time=06:20`; effective `jurisdiction_drift_check_enabled` = **True**.
* No traceback, ERROR or warning since the restart; `jurisdiction_manifest_agrees manifest_mtime=2026-10-28T00:13:35.470006+00:00 mode=shadow`. Effective `ddp_openstates_jurisdictions` unchanged (FL, WA, US, VA, MI, MA, UT, AZ, NC). No scrape launched; in-flight 0; no cadence override for any state.
* I did not trigger the drift check. I will report what it logs after 06:20 UTC (including any Slack alert and any finding about the MA difference you described) if the operator wants me to look then.
* Still not observed: ddp-sync reading the broker's bill-topics endpoint (it logs when a run needs the list).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
