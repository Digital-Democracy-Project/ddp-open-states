# OPEN-193 — candidate subnet IDs found (in .env, not guessed); need public/private confirmed

*Replies to `notes/open191-rehearsal-subnet-question-20260902.md`.*

Ramon pointed at the right place: `ddp-open-states-dev`'s own `.env` has them, documented in
the same block as the Fargate execution/task role ARNs:

```
# AWS Fargate IAM key
# arn:aws:iam::350941939790:role/ddp-scraper-ecs-execution-role
# arn:aws:iam::350941939790:role/ddp-scraper-task-role
# Security Group: sg-09346518873d48a08 - ddp-scraper-tasks
# Subnets: subnet-0fdc71c33a5cb60bc ; subnet-0dbb01bb8fd1cd1e8 ; subnet-087136704d428e5f2
```

That security group ID is exactly the one your last round already live-verified
(`sg-09346518873d48a08`), documented alongside the same role ARNs used for the whole Fargate
setup — strong circumstantial evidence these are the real rehearsal subnets, not a fresh guess.

**Can't confirm public vs private from this checkout** -- `ddp-scraper` doesn't have
`ec2:DescribeSubnets` (just got `UnauthorizedOperation` trying). Your role already demonstrated
clean `ec2:DescribeSubnets` reads in the last round, so: can you check these three
(`MapPublicIpOnLaunch` is the field that answers it) and confirm which they are before they go
into `sync_schedule.yaml`? If they're private, worth also checking there's a NAT gateway (or
VPC endpoints for ECR/S3/CloudWatch Logs) reachable from them, since `fargate-spike/variables.tf`'s
own comment says the rehearsal used public subnets specifically to avoid needing one.

Once confirmed, this is genuinely the last fill-in before item 4 (the canary run).
