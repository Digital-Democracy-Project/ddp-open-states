# Draft Phase 7: two roles, deliberately not one, and neither is a broad managed policy
# (AdministratorAccess / AmazonS3FullAccess) -- the draft calls both out by name as what not
# to attach.

data "aws_iam_policy_document" "ecs_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# Pulls the image and writes logs. Nothing about the scraper's own data.
resource "aws_iam_role" "execution" {
  name               = "ddp-scraper-ecs-execution-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "execution_managed" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# This is the "role-based credentials" cloud_collector.py's S3Memory expects (OPEN-201): read/
# write scoped to the one bucket OPEN-181/183 already use, not a bucket-wide "*" grant and not
# access to any other bucket in the account.
data "aws_iam_policy_document" "task_memory_access" {
  statement {
    sid = "MemoryAndWorkingTierReadWrite"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket",
    ]
    resources = [
      var.memory_bucket_arn,
      "${var.memory_bucket_arn}/*",
    ]
  }
}

resource "aws_iam_policy" "task_memory_access" {
  name   = "ddp-scraper-memory-access"
  policy = data.aws_iam_policy_document.task_memory_access.json
}

# What the scraper application itself runs as -- distinct from the execution role per the
# draft's Phase 7, and this is the role a real workload actually exercises OPEN-201's
# "credentials come from boto3's default chain" design against.
resource "aws_iam_role" "task" {
  name               = "ddp-scraper-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "task_memory_access" {
  role       = aws_iam_role.task.name
  policy_arn = aws_iam_policy.task_memory_access.arn
}
