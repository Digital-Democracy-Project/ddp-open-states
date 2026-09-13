# OPEN-285: crontab confirmed (it was Ramon), and PR #149 is merged

Two updates:

1. **Crontab removal mystery solved**: Ramon confirmed directly he removed the legacy
   `refresh-openstates-people.sh` entry himself. Not something that happened unexpectedly --
   one of OPEN-285's three remaining items is now closed for real.

2. **`ddp-sync` PR #149 (the config override gap fix) is merged** -- saw it land at
   2026-09-13T16:06:08Z. Whenever you get a chance: could you confirm it's deployed on the EC2
   host and re-run the end-to-end check (`resolve_touched_sessions` against `US` since the
   recent archive completion) to confirm `mac_ddp_sync_base_url`/`rds_openstates_api_base` now
   come through correctly?

Still open on OPEN-285: a real confirmed clean `openstates_people_refresh` run on the EC2 host
(never actually verified after PR #146 deployed there), and the IAM/EventBridge visibility
question. And still watching for whatever you find on the duplicate-archive-runs check
whenever you get to it.
