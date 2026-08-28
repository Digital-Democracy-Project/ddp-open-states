variable "aws_region" {
  description = "Region already hosting ddp-prod-s3-openstates-backups and the memory store."
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
  description = "ARN of ddp-prod-s3-openstates-backups (or wherever OPEN-181/183's store and working tier live) -- scopes the task role rather than granting broad S3 access."
  type        = string
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
  type    = string
  default = "ddp-scrapers-prototype"
}

variable "task_family" {
  type    = string
  default = "ddp-scraper-prototype"
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
