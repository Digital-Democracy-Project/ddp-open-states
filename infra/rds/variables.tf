variable "aws_region" {
  description = "Same region as the fargate-spike module and the memory/backups buckets."
  type        = string
}

variable "db_instance_identifier" {
  description = "Matches the instance Ramon actually created (2026-08-29) via the console."
  type        = string
  default     = "ddp-openstates"
}

variable "engine_version" {
  description = <<-EOT
    Deliberately matched to the source database's own major version (16), not the console's
    18.3 default -- this instance's whole purpose is validating the Phase 2 migration itself,
    not also absorbing an unvalidated major-version jump at the same time. See
    PLAN-scraper-execution-migration.md's Phase 2 section for the reasoning.
  EOT
  type        = string
  default     = "16.15"
}

variable "instance_class" {
  description = "Burstable, matching a ~3.3GB-and-growing database with bursty (not sustained) load."
  type        = string
  default     = "db.t4g.micro"
}

variable "allocated_storage" {
  description = "gp3, GiB."
  type        = number
  default     = 20
}

variable "max_allocated_storage" {
  description = "Storage autoscaling ceiling, GiB."
  type        = number
  default     = 100
}

variable "vpc_security_group_ids" {
  description = <<-EOT
    Pre-created security group ID(s), created out of band -- same reasoning as
    fargate-spike/variables.tf's security_group_id. Deliberately NOT publicly accessible;
    reachable only through the existing WireGuard EC2 jump box's own security group (added as
    an allowed source on this one), which also already hosts production ddp-sync/ddp-api. This
    module has no ec2:* permissions and never creates or modifies a security group itself.
  EOT
  type        = list(string)
}

variable "db_subnet_group_name" {
  description = "Name of a pre-created DB subnet group in the same VPC as the WireGuard jump box."
  type        = string
}

variable "master_username" {
  description = "Matches what was actually created via the console."
  type        = string
  default     = "openstates_admin"
}

variable "backup_retention_period" {
  description = "Days. Separate from (not a replacement for) the existing nightly pg_dump-to-S3 backup."
  type        = number
  default     = 7
}
