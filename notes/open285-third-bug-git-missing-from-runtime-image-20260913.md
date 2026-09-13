# OPEN-285: PR #251 deployed, but a third, separate bug still blocks a real success -- `git` isn't in ddp-sync's runtime image at all

Deployed #251 for real (fast-forwarded this host's `ddp-open-states` checkout to `main`,
confirmed the fix landed and matches `HEAD` exactly -- this repo is bind-mounted into
`ddp-sync`, so it took effect immediately, no rebuild needed for that part).

**Triggered a real run to get real evidence**, not just "no crash": `POST
/ddp-sync/v1/trigger/openstates-scrape/people`. It failed again --
`exit_code_127, duration_seconds=0.0`. Different error than before (was `exit_code_1`
pre-fix), so the path bug is confirmed fixed, but something else breaks immediately after.

**Root-caused directly**: ran `run-people-refresh.sh` by hand inside the container. It dies
right after `cd "$SCRIPT_DIR/people"`, at the very next line, `git pull --ff-only`:

```
bash: line 1: git: command not found
```

Confirmed for real, not assumed: `which git` inside `ddp-sync-ddp-sync-1` finds nothing, and
`apt list --installed` shows no `git` package at all. Checked `infrastructure/Dockerfile`:
`git` IS installed in the earlier **builder** stage (to clone `openstates-core`/
`openstates-scrapers`), but the **final runtime stage**'s own `apt-get install` (currently just
`libgdal32 poppler-utils`) never carries it over. Same class of gap as this same file's own
documented `poppler-utils` miss (found 2026-09-09) -- a build-stage dependency assumed to be
"only needed at build time" that's actually also needed at runtime, for a different reason
(git pull, not a build-time clone).

**Did not attempt to hack around this by installing `git` into the live running container** --
that's not durable (lost on next recreate) and isn't the right fix. This needs
`infrastructure/Dockerfile`'s final stage to add `git` to its `apt-get install` line, then a
real rebuild + redeploy + a real successful trigger to confirm.

**Still holding on the legacy crontab removal** -- three real failures in a row now (original
dubious-ownership error, then the hardcoded-path bug, now this) mean `openstates_people_refresh`
has *never once* succeeded on this host. Removing the cron before a real success would leave
zero working people-refresh path here, same reasoning as before.

Ramon asked me to let you know rather than have me rebuild/redeploy `ddp-sync`'s image myself
this time, since it's a bigger change than the two already-authorized fixes. Your call on
whether to fix it directly or want me to take it from here once you've made the Dockerfile
change.
