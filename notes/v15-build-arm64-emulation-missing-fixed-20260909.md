# v15 build: first attempt failed (no ARM64 emulation on this host), fixed, rebuilding

*Replies to `notes/open192-both-prs-merged-please-deploy-and-validate-20260909.md`.* Ramon
provisioned `GITHUB_PERSONAL_ACCESS_TOKEN` in this host's `.env` — that blocker's cleared. First
build attempt still failed, for an unrelated reason.

## What happened

`DOCKER_BUILDKIT=1 docker build --secret id=github_token,env=GITHUB_PERSONAL_ACCESS_TOKEN
--platform linux/arm64 -t ddp-scrapers:v15 .` failed inside `apt-get install` with
`standard_init_linux.go:239: exec user process caused: exec format error`. Nearly missed this —
I'd piped the build through `tail -60`, so the background task reported the pipeline's exit code
(0, from `tail`) rather than `docker build`'s real one. Caught it by checking `docker images` and
seeing no `v15` tag existed at all.

## Root cause

This EC2 host is `x86_64` with **zero ARM64 emulation configured** — confirmed with a plain
`docker run --rm --platform linux/arm64 arm64v8/busybox uname -m`, which failed with the
identical `exec format error`, no build involved. The existing `ddp-sync-builder` buildx instance
(from the earlier OPEN-193 session) only lists `linux/amd64`/`linux/386` as supported platforms —
no `arm64`. Whoever built `v14` previously was almost certainly doing it natively on an
ARM64-native machine (Apple Silicon Mac), where this gap doesn't exist and so was never hit.

## Fixed

Ran `docker run --privileged --rm tonistiigi/binfmt --install all` (standard one-shot QEMU
binfmt bootstrap — asked before running it, since `--privileged` touches the host's kernel-level
binfmt_misc handlers, not something to do silently). Confirmed working immediately after: the
same `arm64v8/busybox uname -m` check now reports `aarch64`. This should be a permanent host
fix, not something that needs repeating per-build.

## Status

Retrying the `v15` build now with emulation in place, this time capturing the real exit code
directly (redirected to a log file, not piped through `tail`) so a silent failure can't slip by
again. Will report the actual result once it lands — this note is the failure + workaround, not
the final outcome.
