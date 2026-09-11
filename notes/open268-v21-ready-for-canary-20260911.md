# OPEN-268 image built on the Mac, revision 25 registered -- ready for the dry-run canary

Built and verified on the Mac (not here), per the corrected note and the new RUNBOOK.md
section (ddp-open-states PR #236):

- **Image:** `350941939790.dkr.ecr.us-east-1.amazonaws.com/ddp-scrapers:v21`
  (digest `sha256:4a8acc40f21a2897595dcd635f90d58f38206e6da8a36226119b0060e43cabae`)
- **Task definition:** `arn:aws:ecs:us-east-1:350941939790:task-definition/ddp-scrapers:25`
- Verified inside the pushed image before registering: `python --version` -> 3.10.21,
  `pdftotext -v` -> 22.12.0, and specifically `RUNNER_SCRIPT=cloud_text_extract.py` ->
  correctly execs into `os-text-extract --help` (confirmed the full subcommand list prints,
  including `recompute-diff-order`/`refresh-extraction`/`reextract`).
- Revision 24 (`v20`) is untouched and still registered -- nothing currently running was
  disturbed, this is purely additive. Rollback is just not pointing anything at 25.

## Your turn: the supervised dry-run canary (OPEN-268's second acceptance criterion)

```bash
curl -X POST "http://localhost:8000/trigger/openstates-backfill/mi?subcommand=recompute-diff-order&mode=dry-run" \
    -H "Authorization: Bearer $DDP_SYNC_API_KEY"
```

Returns `{"status": "started", "run_id": "...", ...}` immediately (202). Grep `ddp-sync`'s own
structured logs for that `run_id` a few seconds later for the actual result -- look for
`openstates_backfill: fargate task done` with a non-empty `output` matching MI's usual dry-run
summary shape (`mi: [DRY RUN] N bills checked | unchanged=... corrected=... nulled=...`).

Same thing to watch for as before: `output` may take a few extra seconds to show up (the
log-fetch fix now waits for 2 consecutive quiet CloudWatch rounds before returning) -- if
`exit_code` is 0 but `output` comes back empty, that's worth flagging back rather than assuming
it's fine.

If that all checks out, OPEN-268's both acceptance criteria are met and it can move to Done.
