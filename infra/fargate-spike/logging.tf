# Draft Phase 13. Retention set explicitly rather than left at "never expire" -- this is a
# prototype's logs, not the working tier's documents; OPEN-183's retention reasoning does not
# apply here.
resource "aws_cloudwatch_log_group" "scrapers" {
  name              = "/aws/ecs/${var.ecr_repository_name}"
  retention_in_days = 30
  tags              = var.tags
}
