# Quick check: is OPENSTATES_SCRAPE_ENABLED actually persisted correctly on both hosts?

Ramon's manual stop of the Mac's openstates scraper runs, and kickstarting EC2's, earlier
tonight was ad hoc -- want to confirm it's actually reflected in each host's real, persisted
`.env`, not just a running-process state that reverts on the next restart.

`SYNC-51` already built exactly the mechanism for this: `OPENSTATES_SCRAPE_ENABLED` is a
per-host `.env` flag (`config.py`'s `_TASK_ENABLE_FLAG_ENV_VARS`), ANDed with the shared
checked-in YAML schedule. This is a config check, not a build -- filed as **OPEN-253** for
tracking, but this is exactly the kind of thing you can just check/fix directly rather than
wait on process, since you already have real access to both hosts.

Could you confirm and report back:

1. **Mac's `.env`**: is `OPENSTATES_SCRAPE_ENABLED=false` actually saved there (not just the
   process currently being stopped)? If not, set it.
2. **EC2's `.env`**: is `OPENSTATES_SCRAPE_ENABLED=true` actually saved there? If not, set it.

If both are already correctly persisted, just say so and I'll close OPEN-253 out. If either
needs fixing, go ahead and fix it directly -- no need to route back through here first for
something this small.
