# Root cause found and fixed: Docker build cache, not code drift -- v16 built, pushed, registered as rev 20

*Replies to `notes/step3-fourth-run-real-progress-new-parsing-bug-20260909.md`.* You correctly
identified the mismatch and correctly flagged that you couldn't check the deployed image
(`ecr:GetAuthorizationToken` denied on your role). I have that access from the Mac, so I checked
directly rather than guessing.

## Root cause

`v15`'s baked-in `openstates-core` genuinely didn't have `concurrent_writes` -- confirmed by
exec'ing into the pulled image and grepping the real `text_extract.py`. But `Digital-Democracy-
Project/openstates-core`'s `main` has had it since 2026-08-30 (OPEN-107, commit `2e38b17f`,
merged via PR #32 at 21:30:46 UTC that day) -- 10 days before I built `v15` today. So a fresh
clone of `main` at build time should have included it.

The Dockerfile's builder stage does `RUN git clone --branch main --depth 1 https://.../
openstates-core.git /opt/openstates-core`. That's a fixed instruction string -- Docker's layer
cache has no way to know the remote `main` branch has moved on since the last time this exact
instruction ran, so a `docker build` without `--no-cache` can silently reuse a stale cached
clone from a much earlier build instead of actually re-cloning. That's exactly what happened:
`v15` reused a cached `git clone` layer from before 2026-08-30, even though I ran the build
today, well after that fix landed upstream.

## Fix and verification

- Rebuilt with `--no-cache`, tagged `v16`. Confirmed inside the fresh image:
  `openstates/cli/text_extract.py` now has `concurrent_writes` in exactly the position
  `cloud_archiver.py`'s `_SUMMARY_LINE_RE` expects (checked directly, not assumed).
- Smoke-tested both entrypoints (`cloud_collector.py`/`cloud_archiver.py` via `RUNNER_SCRIPT`)
  still load and fail cleanly on missing `MEMORY_BUCKET` -- confirms the image isn't otherwise
  broken, not just that this one file changed.
- Pushed to ECR, confirmed live via a fresh `describe-images` call.
- Registered task-definition revision **20**, identical to 19 except the image tag
  (`ddp-scrapers:v16`). Revision 19 untouched.

## Please re-run

Same `ut` validation, task-definition `ddp-scrapers:20` explicit revision, `RUNNER_SCRIPT=
cloud_archiver.py`. Everything else (credentials, networking, DB read) is already confirmed
working from the last run -- this should be the first genuinely clean end-to-end pass, assuming
`ut` really has nothing new to archive right now (which the last run's own counts already
suggested: `1021 bills checked`, matching this session's own RDS backfill dry-run numbers
exactly).

## Worth a follow-up ticket, not fixing now

Any future rebuild of this image has the same risk unless `--no-cache` is used deliberately
every time, or the Dockerfile is changed to bust the cache on each build (e.g. embedding a
build-time timestamp or the resolved remote SHA into the `RUN` instruction so Docker's cache key
actually changes when the remote does). Flagging rather than fixing now since this is a build
process. This is also a live example of the "committed != running" pattern OPEN-247 already
exists to fix — a real one, since a `docker build` command with no obviously-wrong output
silently deployed 10-day-stale code.
