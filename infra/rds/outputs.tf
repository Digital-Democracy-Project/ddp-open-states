output "endpoint" {
  description = "Connection endpoint (host:port)."
  value       = aws_db_instance.openstates.endpoint
}

output "address" {
  description = "Bare hostname, without the port -- what DATABASE_URL/DATABASE_URL_OVERRIDE needs."
  value       = aws_db_instance.openstates.address
}

output "master_user_secret_arn" {
  description = "Secrets Manager ARN holding the master credential -- read via secretsmanager:GetSecretValue, never a plain password."
  value       = aws_db_instance.openstates.master_user_secret[0].secret_arn
}
