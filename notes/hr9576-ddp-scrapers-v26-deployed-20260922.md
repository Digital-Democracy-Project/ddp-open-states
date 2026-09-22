# ddp-scrapers image side is done -- v26/revision 31 live, your ddp-sync rebuild is the last piece

**Re:** `hr9576-ddp-sync-rebuild-instructions-20260922.md` (this branch, earlier today).

Ramon built, verified, pushed, and registered the new `ddp-scrapers` image on his own machine:

```
{
    "arn": "arn:aws:ecs:us-east-1:350941939790:task-definition/ddp-scrapers:31",
    "revision": 31,
    "image": "350941939790.dkr.ecr.us-east-1.amazonaws.com/ddp-scrapers:v26"
}
```

Verified before push: `/opt/venv/bin/python --version`, `pdftotext -v`, and a real
`RUNNER_SCRIPT=backfill-vote-person-resolution.py --dry-run` run against the local replica
(correct output: 23,047 unresolved found, 19,803 would resolve). Digest on ECR matches the
locally-built/verified image exactly. `v25`/revision 30 stays as an untouched rollback --
registration doesn't disturb anything already running, and new task launches should pick up
revision 31 automatically since the family is referenced unqualified in config.

**This side is done.** The one remaining piece is the `ddp-sync` rebuild/restart on this host
itself (previous note has the exact commands) -- once that's done, the full path from
`POST /trigger/vote-person-backfill?mode=dry-run` through to a launched Fargate task running the
actual backfill script should be complete end to end. Report back the dry-run numbers once
you've got it running.
