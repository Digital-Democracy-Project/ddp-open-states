output "ecr_repository_url" {
  value = aws_ecr_repository.scrapers.repository_url
}

output "cluster_name" {
  value = aws_ecs_cluster.scrapers_prototype.name
}

output "task_definition_arn" {
  value = aws_ecs_task_definition.scraper_prototype.arn
}

output "security_group_id" {
  value = aws_security_group.scraper_task.id
}

output "log_group_name" {
  value = aws_cloudwatch_log_group.scrapers.name
}

# Surfaced rather than left as an unused input: assignPublicIp and subnet selection are
# `run-task`-time arguments, not task-definition fields (pm-review's point), so this is where
# an operator actually needs var.public_subnet_ids again when following the README's manual
# `aws ecs run-task` example.
output "public_subnet_ids" {
  value = var.public_subnet_ids
}
