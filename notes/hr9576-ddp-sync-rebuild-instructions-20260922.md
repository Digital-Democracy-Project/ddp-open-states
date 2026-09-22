# Please rebuild/redeploy ddp-sync on the EC2-broker host (parallel track to the ddp-scrapers image)

**Thread:** VOTEBOT-7/OPEN-2/SYNC-74. Both PRs (`ddp-open-states`#257, `ddp-sync`#164) are merged.

## Two separate things need to happen, in parallel, before the backfill is actually runnable

1. **The `ddp-scrapers` Fargate task image** — being handled on this Mac right now (build + verify
   done, ECR push + new task-definition revision registration is a human/Ramon step in progress).
2. **`ddp-sync` itself** — this is the one you're needed for. It runs as a long-running Docker
   Compose service **on this EC2-broker host directly** (not Fargate — Fargate is only for the
   ephemeral scrape/backfill tasks `ddp-sync` dispatches). The new `POST /trigger/vote-person-
   backfill` endpoint doesn't exist yet on the running instance until this host's own checkout
   is updated and the container rebuilt/restarted.

## What to run (adjust the path if `ddp-sync` isn't checked out at this exact location on this host)

```bash
cd ~/ddp-sync   # confirm/adjust -- Mac Studio's own checkout is ~/Developer/repos/ddp-sync,
                # EC2 civic's is /home/ubuntu/ddp-sync; this host's may differ
git status      # confirm clean, no in-progress uncommitted work, before switching/pulling
git checkout main
git pull origin main   # should now include #164 (the new vote_person_backfill.py + trigger route)
git log --oneline -3   # sanity check the merge commit is there

docker compose -f infrastructure/docker-compose.prod.yml build ddp-sync
docker compose -f infrastructure/docker-compose.prod.yml up -d --force-recreate ddp-sync
```

Deliberately scoped to the `ddp-sync` service by name on every command (this compose file only
defines that one service anyway, joining `ddp-broker-py`'s network externally rather than
managing it, but naming it explicitly is still the safe habit).

## After restart, a couple of sanity checks

```bash
curl -s http://localhost:8001/ddp-sync/v1/schedule    # confirm it came back up at all
curl -s -X POST -H "Authorization: Bearer <api key>" \
    "http://localhost:8001/trigger/vote-person-backfill?mode=dry-run"   # confirm the new route exists (202, not 404)
```

**Please don't actually let the dry-run job finish and report real numbers yet** if any other
trigger job might be mid-flight on this host at the moment of restart -- an in-flight background
task's own polling loop would get killed by the container restart (the underlying Fargate task it
was watching keeps running fine independently; only the polling wrapper dies, so nothing is
lost, but you'd lose that specific call's own result/log correlation). Otherwise, once both this
and the `ddp-scrapers` image side are confirmed up, go ahead and run the real
`?mode=dry-run` call and report the counts back here.

Reply on this branch as usual.
