variable "aws_region" {
  description = "Region already hosting ddp-openstates-backups and the memory store."
  type        = string
}

variable "execution_role_arn" {
  description = <<-EOT
    ARN of ddp-scraper-ecs-execution-role, created OUT OF BAND by whoever holds broader AWS
    access -- deliberately not a resource this module manages. Role creation (and the PassRole
    grant it needs) is IAM-privileged in a way that "apply this Terraform" should not casually
    be. See README.md's setup recipe.
  EOT
  type        = string
}

variable "task_role_arn" {
  description = "ARN of ddp-scraper-task-role -- same reasoning as execution_role_arn above."
  type        = string
}

variable "security_group_id" {
  description = <<-EOT
    ID of a pre-created security group (outbound HTTPS only, no inbound) in the target VPC --
    also created out of band. This module has no ec2:* permissions at all and never touches a
    security group, existing or new; this is a plain string used only in the README's
    `aws ecs run-task` example.
  EOT
  type        = string
}

variable "public_subnet_ids" {
  description = <<-EOT
    Subnets with a route to an Internet Gateway and auto-assigned public IPv4 -- the draft's
    Option A (public IP per task), required for the first WAF/egress test so tasks don't share
    one NAT Gateway's address, which would recreate the centralised-egress problem this
    migration exists to remove.
  EOT
  type        = list(string)
}

variable "memory_bucket_arn" {
  description = <<-EOT
    ARN of ddp-openstates-scraper-memory -- a dedicated bucket, not ddp-openstates-backups.
    Moved 2026-08-29: ddp-openstates-backups carries a bucket-wide (Filter: Prefix "") 30-day
    Expiration + 1-day NoncurrentVersionExpiration rule, set up for Postgres dumps under db/
    before OPEN-183's working-tier decision existed. OPEN-183 assumed "there is no lifecycle
    to separate" -- that assumption was wrong, and everything this task writes (working-tier
    documents, per-source memory/cache) would have hard-deleted around day 31 regardless of
    scrape frequency. The new bucket has no lifecycle rule and Object Lock enabled (Governance
    mode, 1-year default retention) so a future rule applied to the wrong bucket can't silently
    repeat this. Scopes the task role rather than granting broad S3 access.
  EOT
  type        = string
}

variable "va_api_key" {
  description = <<-EOT
    Virginia's LIS API key (https://lis.virginia.gov/developers). Found missing during OPEN-191's
    per-jurisdiction Fargate rehearsal (2026-08-29/30): the default VaBillScraper needs it, and
    without it the scraper silently returns zero objects -- openstates-core then raises
    "ScrapeError: no objects returned from VaBillScraper", indistinguishable at the exit-code
    level from a real scrape failure. Reproduced locally (`docker run` against the same image)
    to confirm, since CloudWatch log read access was unavailable at the time to see the real
    traceback from the Fargate task directly.

    Plain environment variable for now, matching MEMORY_BUCKET/MEMORY_PREFIX's existing pattern
    -- not yet moved to Secrets Manager. That's a real gap (this is a credential, not
    infrastructure-shaped config like a bucket name) worth fixing before any other jurisdiction's
    API key is added the same way; tracked as a follow-up rather than blocking this fix.
  EOT
  type        = string
  sensitive   = true
}

variable "image_tag" {
  description = "The ECR tag this task definition points at. ecr.tf sets the repository to IMMUTABLE tags, so a rebuilt image during the spike needs a new value here (a git sha, a timestamp -- anything but reusing the last one, which ECR will simply refuse)."
  type        = string
  default     = "prototype"
}

variable "ecr_repository_name" {
  description = "Matches the fargate draft's suggested name."
  type        = string
  default     = "ddp-scrapers"
}

variable "cluster_name" {
  description = "Matches the cluster Ramon actually created (2026-08-28) -- named without a '-prototype' suffix on purpose, since Fargate may end up the long-running answer rather than a throwaway."
  type        = string
  default     = "ddp-scrapers"
}

variable "task_family" {
  description = "Matches the task-definition family name Ramon settled on (2026-08-28) -- ddp-scrapers, same as the cluster and log group, not the earlier ddp-scraper-prototype/ddp-scraper guesses."
  type        = string
  default     = "ddp-scrapers"
}

variable "task_cpu" {
  description = "1 vCPU, per the draft's starting point (Phase 11)."
  type        = string
  default     = "1024"
}

variable "task_memory" {
  description = "2 GB, per the draft's starting point (Phase 11)."
  type        = string
  default     = "2048"
}

variable "tags" {
  description = "Required prototype tags (draft Phase 17)."
  type        = map(string)
  default = {
    Project     = "DDP-Scrapers"
    Environment = "Prototype"
    Owner       = "DDP"
    Workload    = "Ingestion"
  }
}
