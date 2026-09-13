# SYNC-65: config override gap fixed (ddp-sync PR #149)

Thanks for finding this one and doing the full live diagnosis yourself (env vars set correctly
in the container, get_settings() returning empty anyway, the exact httpx.UnsupportedProtocol
failure mode) -- made this a fast fix.

**PR: https://github.com/Digital-Democracy-Project/ddp-sync/pull/149** (not merged -- same as
#148, want your read given you're the one with live access to confirm it actually resolves
what you found).

Adds `mac_ddp_sync_base_url` and `rds_openstates_api_base` to `get_settings()`'s existing
per-host override loop (the same one `REDIS_URL` already has since OPEN-193). pm-review approved;
I also audited every other `SyncSettings` field for the same gap -- found a few other
pre-existing candidates shaped the same way (`cams_base_url`, `local_openstates_api_base`,
`ddp_broker_api_base`, `ondemand_broker_api_base_dev`/`_prod`), but no live evidence any of them
are actually broken today, so left those for a separate audit rather than guessing at a fix.
Full suite: 1243 passed.

Once this deploys, could you re-run the same end-to-end check you did before (`resolve_touched_
sessions` against `US` since the recent archive completion) to confirm `mac_ddp_sync_base_url`/
`rds_openstates_api_base` actually come through correctly now?

Separately: still watching for anything on the duplicate-archive-runs question
(`notes/duplicate-archive-runs-check-20260913.md`) whenever you get to it -- not urgent, archiving
is off on the Mac now so no new exposure, just want to know the actual blast radius from the last
few days.
