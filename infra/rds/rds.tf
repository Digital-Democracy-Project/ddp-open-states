# OPEN-191 (Phase 2): documents the real ddp-openstates RDS instance Ramon created by hand via
# the console on 2026-08-29 -- this file was written AFTER the instance already existed, in the
# same spirit as infra/fargate-spike: capture the real, running configuration as Infrastructure
# as Code rather than leaving it undocumented, without ever having been applied against the live
# resource (this account's credential set has no rds:CreateDBInstance permission at all, by
# design -- see infra/fargate-spike/README.md's IAM-boundary reasoning, which applies here too).
#
# Deliberately NOT a throwaway/rehearsal instance. Ramon's standing decision: "we won't throw it
# away. it becomes real infrastructure." See PLAN-scraper-execution-migration.md's Phase 2
# section for the rehearsal this instance was seeded and verified with.
resource "aws_db_instance" "openstates" {
  identifier     = var.db_instance_identifier
  engine         = "postgres"
  engine_version = var.engine_version
  instance_class = var.instance_class

  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = "openstates"
  username = var.master_username
  manage_master_user_password = true

  multi_az            = false
  publicly_accessible = false
  db_subnet_group_name   = var.db_subnet_group_name
  vpc_security_group_ids = var.vpc_security_group_ids

  # Password and IAM database authentication both enabled. IAM auth is unused today -- nothing
  # in this stack generates/refreshes an IAM auth token -- but it's additive over password auth,
  # not a replacement, and free to have available if a concrete future need shows up.
  iam_database_authentication_enabled = true

  backup_retention_period = var.backup_retention_period
  enabled_cloudwatch_logs_exports = ["postgresql"]

  auto_minor_version_upgrade = true
  deletion_protection        = true

  performance_insights_enabled = true
  # Standard tier, not Advanced -- this is a small validation-gate database without real
  # production traffic yet, not a fleet needing long-retention cross-database correlation.
  # Confirmed live and working on db.t4g.micro (2026-08-29 DescribeDBInstances:
  # PerformanceInsightsEnabled=true) -- pm-review round 1 raised whether this combination is
  # even supported; it is, for this instance class/engine/region.
  performance_insights_retention_period = 7

  # pm-review round 1: skip_final_snapshot = false requires final_snapshot_identifier, or a
  # real terraform destroy fails outright asking for one. deletion_protection above already
  # blocks destruction entirely today, but this makes the eventual retirement path (turn off
  # protection, then destroy) actually work rather than fail a second time on a missing name.
  skip_final_snapshot       = false
  final_snapshot_identifier = "${var.db_instance_identifier}-final"
}
