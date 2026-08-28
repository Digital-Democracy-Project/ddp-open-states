# Draft Phase 6, Option A: public IP per task, no NAT Gateway, no shared egress address --
# the whole point of the prototype's networking test. Inbound: none. Outbound: HTTPS only,
# per the draft's minimum ("HTTP 80 if needed" is deliberately not opened until a real source
# needs it -- narrower than the draft's own suggestion, and easy to widen if OPEN-189 finds one).
resource "aws_security_group" "scraper_task" {
  name        = "ddp-scraper-task"
  description = "OPEN-200 prototype Fargate task -- outbound HTTPS only, no inbound"
  vpc_id      = var.vpc_id

  egress {
    description = "HTTPS to source sites, ECR, S3, CloudWatch"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = var.tags
}
