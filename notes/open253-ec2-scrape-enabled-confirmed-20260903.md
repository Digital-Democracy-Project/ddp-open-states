# OPEN-253: EC2 half confirmed + fixed. Mac's side needs the dev agent -- can't check it from here.

*Replies to `notes/open253-confirm-scrape-enabled-flags-20260903.md`.*

## EC2

Was **not** actually persisted correctly. `docker-compose.prod.yml`'s `environment:` block hardcodes
`OPENSTATES_SCRAPE_ENABLED` as a literal value (`- OPENSTATES_SCRAPE_ENABLED=false`), not a
`${VAR}` substitution -- so it overrides whatever `.env` says for that same key, silently.
The user set `.env`'s copy to `true` first; had nothing else changed, that edit would have had
**zero effect**, since the compose file's literal `false` wins.

Fixed by flipping the compose file's literal value to `true` directly (kept as a host-local
change, same as `sync_schedule.yaml`/`ddp-sync.service` already are -- the committed default on
`main` is still `false`, which is the right default for a fresh deploy of this template; only
this host's real value needed to diverge). Confirmed no in-flight Fargate tasks first
(`ecs:ListTasks` on `ddp-scrapers`, empty), rebuilt, restarted via `systemctl restart
ddp-sync.service` (not raw `docker compose up`, which the first attempt tried and created a
wrongly-named container under the wrong compose project -- `ddp-sync.service` runs `docker
compose -p ddp-sync ...` explicitly). Verified live in the running container:

```
Scheduler started with 6 jobs
```

...and `OPENSTATES_SCRAPE_ENABLED=true` while all other eleven per-task flags (`BILL_SYNC_ENABLED`
etc.) remain `false`, confirmed directly against the container's own env, not just the compose
file. Health check passed (`GET /ddp-sync/v1/health` -> `200`) within the normal 30s interval.

**`.env`'s `OPENSTATES_SCRAPE_ENABLED=true` is now dead config** -- harmless (the compose file's
literal value is what actually governs it), but worth knowing so a future `.env`-only edit here
doesn't silently do nothing again, same shape as the SYNC-51 precedent.

## Mac

Can't check or fix this from the EC2 host -- no access. Ramon/dev agent: please confirm
Mac's own `.env` (wherever that host's scrape-scheduling flag actually lives -- may not be the
same `ddp-sync` compose mechanism at all, since Mac scrapes run via `run-scrape.sh`/cron rather
than through `ddp-sync`) has `OPENSTATES_SCRAPE_ENABLED=false` (or whatever its real equivalent
is) actually saved, not just the process stopped tonight.
