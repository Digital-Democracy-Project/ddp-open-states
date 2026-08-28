variable "aws_region" {
  description = "Region already hosting ddp-prod-s3-openstates-backups and the memory store."
  type        = string
}

variable "vpc_id" {
  description = <<-EOT
    VPC the prototype task runs in. Not defaulted on purpose -- this is a real choice (share
    the VPC an existing DDP resource lives in, or an isolated prototype VPC) that should be
    made explicitly, not inherited from whatever Terraform finds first.
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
