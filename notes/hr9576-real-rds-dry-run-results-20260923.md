# ddp-sync rebuilt, real RDS dry-run done -- here are the actual numbers

**Re:** `hr9576-ddp-sync-rebuild-instructions-20260922.md` / `hr9576-ddp-scrapers-v26-deployed-
20260922.md` (this branch).

## ddp-sync rebuild: done

Confirmed no in-flight jobs first (zero running ECS tasks, zero trigger activity in the prior
6h of logs). `git pull origin main` on this host fast-forwarded `a2c4437 -> e097e9b` (11 commits,
includes #164 + its pm-review follow-up `fb7590a` adding the route-level test file I'd flagged as
missing -- that gap is closed). Local rendered config (`infrastructure/docker-compose.prod.yml`/
`ddp-sync.service`) untouched, confirmed origin/main's incoming commits don't even touch
`infrastructure/`.

**One real correction for whoever writes the next set of manual-restart instructions**: plain
`docker compose -f infrastructure/docker-compose.prod.yml up -d --force-recreate ddp-sync` (as
given) creates a container under project name `infrastructure-ddp-sync-1` -- wrong project,
collides on the port with the real `ddp-sync-ddp-sync-1`. The actual systemd unit
(`ddp-sync.service`) always passes `-p ddp-sync` explicitly and runs `render-env.sh` first. Used
`sudo systemctl restart ddp-sync` instead (the canonical, already-correct path) -- clean restart,
`render-env.sh` succeeded, container recreated correctly, healthy within seconds.

## Real RDS dry-run: done

```
Loaded 837 distinct person identifiers.
Found 75,887 unresolved vote records with a usable note/identifier.
Dry run complete. Would resolve 72,550 records (3,337 still unresolvable).
```

Called via `POST /ddp-sync/v1/trigger/vote-person-backfill?mode=dry-run` (note the
`/ddp-sync/v1` prefix -- `app.py` mounts the trigger router under `API_PREFIX`; the earlier notes'
bare `/trigger/...` examples 404 without it). `run_id=vote-person-backfill-dry-run-ea2ae82aef20`,
real Fargate task `f0f133373daa425b9968140b0e6dd555`, 95.8s runtime, exit 0.

Real RDS scope is much larger than the local-replica test suggested: 75,887 unresolved here vs.
23,047 on the replica (~3.3x), and a noticeably higher resolve rate (72,550/75,887 = 95.6% vs.
19,803/23,047 = 85.9% locally) -- makes sense given real production has accumulated far more
history than a replica snapshot.

**One anomaly, not chased further**: a first trigger call (`run_id=...fa4322080c76`) returned a
normal 202 but never actually launched a Fargate task or logged anything at all -- confirmed via
both `docker logs` (nothing) and `aws ecs list-tasks` (nothing running under that attempt). Retried
immediately after and it worked cleanly the second time (`ea2ae82aef20`, above). Didn't reproduce
on a third attempt (didn't try one). Flagging in case it recurs -- a `background_tasks.add_task`
call that returns 202 but silently never fires is worth knowing about even as a one-off.

## Status: not running --commit

Per this thread's established discipline, holding here for Ramon's explicit go-ahead before
`?mode=commit`. Real numbers are in his hands now.

Reply on this branch as usual.
