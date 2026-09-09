# Real fix for the missing pdftotext -- Dockerfile PR up, please rebuild once merged

*Replies to `notes/ut-refused-docs-root-cause-missing-pdftotext-20260909.md`.* Ramon's call: fix
the Dockerfile properly rather than patch the running container live -- a live `apt-get install`
would just disappear on the next rebuild/redeploy and reproduce this exact investigation again
later.

## What's wrong, precisely

`ddp-sync`'s own `infrastructure/Dockerfile` (the OPEN-248 bundled toolchain image you're running
`refresh-extraction` from) has a header comment claiming it mirrors `ddp-open-states`' root
`Dockerfile` "exactly" -- it doesn't. The root Dockerfile added `poppler-utils` 2026-08-29 after a
real FL scrape hit the same `FileNotFoundError: 'pdftotext'`; `ddp-sync`'s copy never got it, even
though its own `libgdal32` addition (same file, same reasoning, same "found missing by actually
running a real command here") landed 2026-09-02 -- a week later, still missed it.

## Fixed

[ddp-sync#122](https://github.com/Digital-Democracy-Project/ddp-sync/pull/122) — adds
`poppler-utils` to the same final-stage `apt-get install` line as `libgdal32`. Not merged yet
(self-authored, needs independent review before landing, same as everything else this session).

## Once it's merged, please rebuild

```
docker-compose -f infrastructure/docker-compose.prod.yml build ddp-sync
docker-compose -f infrastructure/docker-compose.prod.yml up -d ddp-sync
```

Needs the same `GITHUB_PERSONAL_ACCESS_TOKEN` this build has needed all along
(`docker-compose.prod.yml`'s own `secrets: github_token: environment: GITHUB_PERSONAL_ACCESS_TOKEN`
block already wires it up automatically) -- same open question as OPEN-257's Fargate deploy, not
a new one. If that's been provisioned on this host in the meantime, this should just work; if not,
it's the same blocker as before.

After the rebuild, re-run `refresh-extraction ut --dry-run` one more time against RDS -- that's
the run that actually tells us the real regression rate (if any), now that the missing-binary
noise is gone. Everything before that rebuild (this run's 6,270, and whatever WA/US came back
with) should be treated as inflated by this bug, not a real baseline.
