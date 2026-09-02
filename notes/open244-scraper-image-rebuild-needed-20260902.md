# OPEN-244 fix is real but not live yet — the Fargate scraper image itself needs a rebuild this host can't do

*Replies to `notes/open243-open244-pm-review-pass-20260902.md`.*

Confirmed both PR #114 and PR #220 are merged (`d362024` on `ddp-sync`, `fc3cf76` on
`ddp-open-states`), reviewed both diffs, and pulled both into this host's checkouts. `ddp-sync`
side is fully ready: `OPENSTATES_ROOT=/opt/ddp-open-states` is now wired into
`docker-compose.prod.yml`.

**But OPEN-243 and OPEN-244 aren't the same kind of fix.** OPEN-243 (the `OPENSTATES_ROOT` env
override) lives in `ddp-sync`'s own code — rebuilding `ddp-sync`'s container here is enough to
pick it up, same as every fix tonight before it. **OPEN-244 lives in `cloud_collector.py`,
which gets baked into the Fargate task's own Docker image (`infra/fargate-spike`'s Dockerfile),
pushed to ECR as an immutable tag, and only takes effect once the task definition is
`terraform apply`'d to point at that new tag.** Pulling `ddp-open-states` here doesn't touch
what's actually running in Fargate at all — that's a real, separate deployment step nobody has
done yet, and this host can't do it:

- No `terraform` installed, no local state for `infra/fargate-spike` (applied from wherever the
  original stand-up happened).
- No `docker buildx` — the Dockerfile needs BuildKit's `--secret` mount for a GitHub PAT during
  the multi-stage build, and cross-platform build/emulation (`--platform linux/arm64` — this
  host is `x86_64`, the task definition targets `ARM64`/Graviton).
- No GitHub PAT available here for the build step.
- Don't even have `ecs:DescribeTaskDefinition` to check what image tag is currently live.

Whoever has the access this originally used (per `infra/fargate-spike/README.md`'s own setup
recipe): `docker build --platform linux/arm64 -t ddp-scraper:<new-tag> .` (with the GitHub PAT
secret), push to ECR, `terraform apply -var image_tag=<new-tag>`.

**Not re-attempting the canary until that's confirmed live** — retrying now would just repeat
the exact no-op misclassification found earlier, since the running task still uses the
pre-OPEN-244 image. `ddp-sync` stays stopped in the meantime; everything on that side is staged
and ready to go the moment the new image is confirmed deployed.
