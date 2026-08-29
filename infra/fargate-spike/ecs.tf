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
  # Plain input variables, not managed resources -- see variables.tf. This credential has no
  # iam:CreateRole/PutRolePolicy/AttachRolePolicy at all, only iam:PassRole scoped to these two
  # exact ARNs (required for RegisterTaskDefinition to attach them, and nothing more).
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn

  # Built and verified locally on Apple Silicon (arm64) -- Graviton/ARM64 Fargate is also the
  # cheaper option per vCPU-hour, which OPEN-200's own cost-comparison criterion cares about.
  # Declared explicitly rather than left to Fargate's x86_64 default, which would silently
  # reject (or worse, be allowed to accept and then fail at pull time on) an arm64 image.
  runtime_platform {
    cpu_architecture        = "ARM64"
    operating_system_family = "LINUX"
  }

  container_definitions = jsonencode([
    {
      name  = "scraper"
      # IMMUTABLE tags (ecr.tf) mean this must change on every rebuild during the spike --
      # var.image_tag exists so that's a `terraform apply -var image_tag=...` rather than an
      # edit to this file. The draft's own guidance is immutable tags / digest pinning, not a
      # convenience default; keep the friction rather than silently switching the repo to
      # MUTABLE for it.
      image     = "${aws_ecr_repository.scrapers.repository_url}:${var.image_tag}"
      essential = true
      # readonlyRootFilesystem + a mounted /tmp volume was the design here, and it was wrong in
      # practice, found by running a real task rather than by reasoning about it: Fargate's
      # plain ECS "volume" type (no docker_volume_configuration) does not default to the
      # world-writable permissions a local `docker run --tmpfs /tmp` gives you, and this
      # container deliberately runs as non-root -- so tempfile.TemporaryDirectory() found
      # nowhere writable at all and crashed before doing anything. Local testing with
      # `--read-only --tmpfs` did not catch this because that flag isn't what this task
      # definition actually configures. Dropped read-only-root entirely for now, matching every
      # earlier *non*-read-only local test, which all worked -- re-adding it properly (fixing
      # the volume's ownership, or finding another Fargate-supported writable mount that
      # respects a non-root user) is a real hardening step, just not one worth blocking the
      # actual spike question on.
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
