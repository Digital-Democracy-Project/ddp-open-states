# status: MD archive finished by itself (13:14 UTC); ME 5d still collecting

- MD pipeline end (ddp-sync log): "openstates_archive: fargate task done duration_seconds=5144.3", "archiver_triggered_legbot_skipped_legbot_replica_off jurisdiction=MD" (the SYNC-186 gate, so no LegBot trigger), "openstates_pipeline: done archived=True duration_seconds=12205.9 failed=0 sessions=2 status=completed". The archive started on its own at about 11:49 UTC; my hand-start at 12:09:33 was refused with 409 (pipeline lock held), so nothing doubled.
- Not seen: the archive task's own archived=/failed= counts (the ddp-sync log does not carry them); I have not read the CloudWatch stream for it.
- Other runs today on v86, for the record: UT (scheduled 12:00) done 12:37, archived, 0 failed; VA (scheduled 12:00) done 13:01, archived, 0 failed.
- ME 5d (me-98110acf6911, started 11:50:05): still collecting, session 132R1, no errors.
- Waiting on Ramon's go (not started): MD and MS remove-stale-documents (dry runs first), v87 core rollout.
