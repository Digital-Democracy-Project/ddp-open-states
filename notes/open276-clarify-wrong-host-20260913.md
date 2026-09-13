# OPEN-276: hold on -- this looks like it's asking for the config change on the wrong host

Before making this change, checked where `replica_freshness_check_enabled`/
`legbot_rds_replica_jurisdiction_allowlist` actually get read
(`session_pipeline_runner.py`). The code's own docstring is explicit about what this
gates: "OPEN-275 (services/replica_freshness.py) adds a distinct, narrower check:
whether **the Mac's local Postgres replica** has caught up to RDS for the ONE bill about
to dispatch." This is checking freshness of the Mac's own local replica specifically,
not anything this EC2 host has.

This EC2 host doesn't have that local replica at all -- it reads RDS directly
(`RDS_DATABASE_URL`) -- and this host's own `docker-compose.prod.yml` already sets
`SESSION_PIPELINE_BATCH_ENABLED=false` deliberately (this host's mandate is
scraping/archiving, per SYNC-51's per-host task-flag design; LegBot artifact generation
itself runs where CAMS lives, which is the Mac, confirmed multiple times today --
`CAMS_BASE_URL` unset here, no CAMS server on this host). So on this host:
- The scheduled `session_pipeline_batch` job that contains this check never runs here at
  all (feature-flagged off).
- The on-demand route (`POST /trigger/bill-artifact-generation`) exists here, but
  invoking it would hit this same freshness-check code path expecting the Mac's local
  replica -- which doesn't exist on this host -- rather than actually testing anything
  meaningful.

Setting `REPLICA_FRESHNESS_CHECK_ENABLED=true` and the allowlist on THIS host's
`ddp-sync` looks like it would be either a pure no-op (scheduled path, flagged off) or
produce a misleading/broken result if manually triggered (on-demand path, wrong
database) -- not a real verification of anything either way.

Ramon's read (and mine, after checking the code): this config change belongs on the
**Mac's own ddp-sync instance**, where the local replica and CAMS/LegBot dispatch
actually live, not here. Could you confirm that's the intended target, and if so, ask
the Mac side to make this change and do its own real verification there? Happy to help
from this side if there's a piece of this that genuinely does belong on the EC2 host --
just flagging that as written, this doesn't look right for here.
