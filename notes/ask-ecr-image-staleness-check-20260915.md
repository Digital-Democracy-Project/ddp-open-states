# Ask: how far behind main are our ECR-hosted Docker images right now?

Ramon's question, while you're already in the middle of the EC2 OPEN-292 deploy: across
whatever containers we run from ECR (at minimum the "ddp-scrapers" cluster/task-definition
used for both scraping and archiving Fargate tasks -- cluster/task_definition names both
"ddp-scrapers" per `sync_schedule.yaml`), how stale is each one relative to its source repo's
real `main` HEAD right now?

**I couldn't check this myself** -- the only AWS credentials available to this session are the
scraper-scoped `ddp-scraper` IAM user (from `ddp-open-states-dev/.env`), and it's explicitly
denied `ecr:DescribeRepositories` (`AccessDeniedException`) -- that identity is scoped to S3
scraper work only, nothing ECR/ECS. No other AWS profile is configured on this Mac. You likely
have broader access from wherever you're running.

**What would answer this concretely**, for each repository:
- `aws ecr describe-repositories` to enumerate what's actually in ECR (don't assume it's just
  "ddp-scrapers" -- "all of our docker containers" was the actual ask, so worth listing
  everything rather than assuming scope).
- For each repo, `aws ecr describe-images --repository-name <name>` (or check whatever tag the
  live ECS task definition actually references via `aws ecs describe-task-definition`) to find
  the currently-deployed image's push timestamp and, if tagged with a git SHA, which commit it
  was built from.
- Compare that commit/timestamp against the corresponding source repo's real `main` HEAD to say
  how many commits (or how much time) behind each image actually is.

Not urgent relative to the OPEN-292 deploy in progress -- just flagging it as a real open
question, not something to drop everything for.
