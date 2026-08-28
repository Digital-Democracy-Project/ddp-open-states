# Draft Phase 5: Fargate only, no EC2 capacity providers -- deciding whether Fargate is even
# the right runtime is the whole point of OPEN-200, so this prototype should not pre-commit
# capacity infrastructure the finding might reject.
resource "aws_ecs_cluster" "scrapers_prototype" {
  name = var.cluster_name
  tags = var.tags
}

resource "aws_ecs_cluster_capacity_providers" "scrapers_prototype" {
  cluster_name       = aws_ecs_cluster.scrapers_prototype.name
  capacity_providers = ["FARGATE"]
}

# Draft Phase 11. `source-id` and `key=value` parameters are passed at `run-task` time as the
# container command override, per contract SS1 -- not baked into the task definition, so one
# definition serves every jurisdiction (the draft's own instruction: "same image, same task
# definition, different runtime parameters", not one definition per jurisdiction).
resource "aws_ecs_task_definition" "scraper_prototype" {
  family                   = var.task_family
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name      = "scraper"
      image     = "${aws_ecr_repository.scrapers.repository_url}:prototype"
      essential = true
      # readonlyRootFilesystem needs an explicit writable mount for cloud_collector.py's
      # tempfile.TemporaryDirectory() staging area, or "where practical" silently becomes
      # "not practical" the first time a run tries to write. 1 GiB is a starting size for the
      # prototype's first (small) jurisdiction, not a sized answer for MA-scale output --
      # OPEN-189's long-run test should report whether this needs to grow.
      readonlyRootFilesystem = true
      linuxParameters = {
        tmpfs = [
          { containerPath = "/tmp", size = 1024 }
        ]
      }
      environment = [
        { name = "MEMORY_BUCKET", value = regex("arn:aws:s3:::([^/]+)", var.memory_bucket_arn)[0] },
        { name = "MEMORY_PREFIX", value = "prod" },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.scrapers.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "scraper"
        }
      }
    }
  ])

  tags = var.tags
}
