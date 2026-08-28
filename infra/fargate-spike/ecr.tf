# Draft Phase 4. One repository is sufficient for the prototype; immutable tags per the
# draft's explicit instruction not to rely on `latest` alone.
resource "aws_ecr_repository" "scrapers" {
  name                 = var.ecr_repository_name
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = var.tags
}
