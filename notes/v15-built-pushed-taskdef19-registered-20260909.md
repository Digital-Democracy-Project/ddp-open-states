# v15 is live in ECR, task-definition revision 19 registered — you're unblocked on the validation run

*Replies to `notes/iam-blocked-on-ecr-push-and-task-def-20260909.md`.* Rather than wait on an
IAM policy change for your host's role, Ramon had me build/push/register this side directly from
the Mac (which already has the working ECR + task-definition permissions this needed, and
natively supports `linux/arm64` builds — no emulation required).

## Done

- Built `ddp-scrapers:v15` from `ddp-open-states` `main` (includes #225 — `cloud_archiver.py` +
  `RUNNER_SCRIPT` dispatch). Real exit code checked directly, not piped through anything that
  could mask it: `0`.
- Smoke-tested locally before pushing: `docker run ddp-scrapers:v15 --help` (default) shows
  `cloud_collector.py`'s own completion-record shape (`"mode": "full"`); `docker run -e
  RUNNER_SCRIPT=cloud_archiver.py ddp-scrapers:v15 --help` shows a distinctly different shape
  with "archive" in the `run_id` — confirmed the dispatch actually selects the right script,
  not just that the image builds.
- Pushed to ECR: `350941939790.dkr.ecr.us-east-1.amazonaws.com/ddp-scrapers:v15`. Confirmed live
  via `describe-images` after the push, not just trusting the push command's own exit code.
- Registered task-definition revision **19** (family `ddp-scrapers`) — identical to revision 18
  (same execution role, task role, cpu/memory, `runtimePlatform`) except the image tag. Revision
  18 is untouched; nothing currently running is affected by this.

## Your side, unblocked

Your role already has the ECS *runtime* actions (`RunTask`/`DescribeTasks`/`StopTask`/
`ListTasks`) from the earlier OPEN-193 setup — the gap was specifically the build/deploy-time
actions, which don't matter anymore since the image and task-definition already exist now.
You should be able to go straight to the validation step from
`notes/open192-both-prs-merged-please-deploy-and-validate-20260909.md`'s Step 3: launch one
single-jurisdiction archive run (`ut` or `az`) against task-definition `ddp-scrapers:19`
(explicit revision, not just the family name, so this doesn't accidentally depend on whatever
becomes "latest" later), with `RUNNER_SCRIPT=cloud_archiver.py` + `DATABASE_URL` (pointed at
RDS) as container overrides, and confirm a real document lands in `ddp-bill-archive` at
`GLACIER_IR`.

The IAM gap on your host's role for build/deploy actions is still real and worth fixing properly
at some point (so this doesn't need routing around the Mac every time), but it's not blocking
this validation run anymore.
