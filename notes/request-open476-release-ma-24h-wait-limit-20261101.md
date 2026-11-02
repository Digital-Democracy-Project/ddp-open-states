# Request: put the 24-hour Massachusetts wait limit live on the EC2 ddp-sync host (OPEN-476), 2026-11-01

Ramon merged ddp-sync PR #257 (merge commit 476d6d4, 2026-11-01 23:23 UTC). It is the fix chosen after your OPEN-475 reply: Massachusetts' cloud scrape now waits up to 24 hours instead of 12. **It must be live before Sunday 2026-11-08 02:00 UTC**, or MA hits the 12-hour limit again.

## What changed
- Code: `src/ddp_sync/pipelines/cloud_scrape_trigger.py` now reads a per-state wait limit.
- Config: `config/sync_schedule.yaml`, scrape block under `cloud_path.fargate`:
  ```yaml
  max_wait_seconds: 43200            # 12 h for every state not named below
  max_wait_seconds_by_jurisdiction:
    ma: 86400                        # 24 h
  ```
- Other states stay at 12 h. A blank or wrong value in the new key makes ddp-sync fail loudly, not quietly fall back to 12 h.

## What I need from you
1. On the EC2 ddp-sync host (the instance that runs the MA cloud scrape), bring ddp-sync to the merged code and restart it the usual way.
2. **Read the live `cloud_path.fargate` block first, don't just pull.** That host's `sync_schedule.yaml` has been hand-edited before. If it differs from the repo, keep whatever is deliberately different and add only the `max_wait_seconds_by_jurisdiction` block. Do not change the archive block's separate 12 h value.
3. Reply with: the commit now running (UTC time), the live `cloud_path.fargate` block as it reads now (no secrets), and confirmation ddp-sync started cleanly.
4. Check that no MA scrape is in flight when you restart. A job already running keeps the value it started with.

Not asked: no re-run of MA now, no change to the 11-08 schedule, no change to the task definition. If the restart looks risky for anything running, tell me and wait.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
