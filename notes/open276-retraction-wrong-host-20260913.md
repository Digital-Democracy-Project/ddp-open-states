# Retraction: OPEN-276's freshness-check env vars are Mac-side, not EC2 -- please disregard my earlier request

My earlier note (3a0ebee) asked for `REPLICA_FRESHNESS_CHECK_ENABLED` and
`LEGBOT_RDS_REPLICA_JURISDICTION_ALLOWLIST` to be set on ddp-sync/EC2. That was wrong --
Ramon caught it directly. Confirmed against the actual code
(`session_pipeline_runner.py:30-34`): this freshness check is specifically "whether the
Mac's local Postgres replica has caught up to RDS" for LegBot's own dispatch -- the whole
pipeline it gates (`_process_bill_inner`, tied to CAMS) runs on the Mac Studio's own
`ddp-sync` process, not on EC2. Nothing on the EC2 side needs to change for this.

No action needed from you on this one -- please disregard the earlier request. Handling
the actual Mac-side `.env` edit + restart directly with Ramon instead.
