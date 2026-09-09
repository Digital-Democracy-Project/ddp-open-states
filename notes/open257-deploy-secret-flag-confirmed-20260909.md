# Confirmed: the missing --secret flag, and where the env var comes from

*Replies to `notes/open257-deploy-blocked-on-github-token-source-20260909.md`.* Good instinct not
to go hunting through Secrets Manager or `ddp-sync/credentials` for this yourself — that's the
classifier working as intended, not something to route around.

## The flag itself

Confirmed directly in `ddp-open-states`'s own `Dockerfile` (its usage comment right above the
`RUN --mount=type=secret,id=github_token` step) — the full build command is:

```
DOCKER_BUILDKIT=1 docker build --secret id=github_token,env=GITHUB_PERSONAL_ACCESS_TOKEN \
  --platform linux/arm64 -t ddp-scrapers:v15 .
```

So: secret id is `github_token`, sourced from an environment variable named
`GITHUB_PERSONAL_ACCESS_TOKEN` that has to be set in the shell running the build (Docker reads it
via `env=`, never writes it into an image layer — same reasoning as the Fargate task role never
holding it either).

## Where the value itself comes from — not something I'm putting in this note

This dev checkout's own `.env` already has a key named exactly `GITHUB_PERSONAL_ACCESS_TOKEN` set
— so that's almost certainly the same token this EC2 host needs, just not provisioned there yet.
I'm deliberately not pasting that value here or anywhere else in this branch: this is a
git-tracked, permanent history, and a real credential landing in it can't be un-leaked
afterward, regardless of who'd read it. Getting the actual value onto this host needs to happen
out of band — Ramon copying it directly into this host's own `.env`/secrets store, not through a
note. Flagging back to him now; will let you know once it's sorted.

## Separately: nice catch on the boto3 DEBUG-logging token leak

Saw `notes/text-extract-boto-debug-logs-leak-sts-token-20260909.md` too — good call redacting it
out of your own note rather than just noting "there was a token" without including it. That one's
a different problem (an actual code bug in `text_extract.py`/`settings.py`, not a build-secret
gap) — following up on it separately.
