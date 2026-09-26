# OPEN-305: v28 built + pushed, task-def revision 33 registered

**Re:** your Jira comment on OPEN-305 flagging that the merged fix (`openstates-scrapers` PR #54)
wasn't live yet since `usa` runs on Fargate. Built and pushed on the Mac per RUNBOOK.md's
"Deploying a Fargate image change" section.

## What's ready

- **Image:** `350941939790.dkr.ecr.us-east-1.amazonaws.com/ddp-scrapers:v28`
  (digest `sha256:9c29e65e3f8b40e7ae532d017bc2abd0ffc7c01240fd409ef3b6855533b9d9e6`)
- **Task-definition revision:** `ddp-scrapers:33`
  (`arn:aws:ecs:us-east-1:350941939790:task-definition/ddp-scrapers:33`)
- **Verified inside the image before push:** `python --version` (3.10.21), `pdftotext -v`
  (22.12.0), and -- since "the build succeeded" isn't the same claim as "the fix is actually in
  there" -- grepped the image's own cloned `openstates-scrapers` checkout directly for the fixed
  line:
  ```
  919:            # see scrapers/usa/__init__.py); its own vote.vote(..., note=lis_id, id=lis_id) call
  921:            vote.vote(self.vote_codes[choice], name, note=lis_id, id=lis_id)
  ```
  Confirms this image was actually built from `openstates-scrapers` `main` post-merge
  (`4d5f2f19e5bdd173b161c57115a46ef20a6d9ea5`), not a stale cache.

## You may not need to do anything else for this to go live

Checked `ddp-sync`'s `config/sync_schedule.yaml`: `openstates_scrape.cloud_path.fargate.
task_definition` is set to the bare family name `"ddp-scrapers"`, not a pinned revision number.
ECS resolves a bare family name to whatever revision is currently **active** at `run_task` time
-- and revision 33 is now that. So the next regularly-scheduled `usa` scrape should pick up v28
automatically, no separate deploy step needed on your end.

## Ask

Given how long this has been silently wrong, probably worth confirming rather than waiting for
the next cron tick -- there's already a `/trigger/openstates-scrape/usa` endpoint. Could you:

1. Trigger it once.
2. After it completes, spot-check a couple of freshly-scraped vote_events (same query shape as
   your own investigation: `PersonVote` rows for a `vote_event` with a recent `created_at`) --
   confirm `voter_id` is populated instead of null this time, for both a House and a Senate vote
   if the run touches both.
3. Report back here with what you find, and I'll close out OPEN-305 in Jira.
