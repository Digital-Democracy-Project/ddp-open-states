# status: WA nightly 11-25 02:30 UTC finished CLEAN; read effc219

- **WA nightly (wa-e268235309d6, scheduled 02:30 UTC; the first nightly since the 11-24 failure on the 2027-28 session):** collection done 02:36:04, `cloud_scrape: done duration_seconds=368.1` at 02:36:09 (the load took about 5 s: nothing changed), archive task 121.2 s at 02:38:12, knowledge-base embedding `bills=0 chunks=0 complete=True` (3,411 listed, 0 to check), then `openstates_pipeline: done archived=True duration_seconds=507.8 failed=0 sessions=1 status=completed`. No SSLError, CERTIFICATE_VERIFY_FAILED or other error line for wa. It ran on the revision that was newest at launch (the one the 02:30 trigger picks).
- So the 2027-28 session no longer breaks the nightly. I did not read the task's own log for its session list; the pass line is "failed=0".
- Read effc219 (running list: v95 built, RI started, ddp-sync image staged): matches what I posted. Nothing for me.
- Running: RI (rev 97), HI second re-import and the OK 2025 retry (rev 96), IA 2025 (rev 95), UT (rev 92). The guarded ddp-sync restart waits for 04:45 UTC.
