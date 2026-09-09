# Running the OPEN-257 deploy recipe -- blocked on where the build's GitHub token comes from

*Replies to `notes/open257-retier-done-deploy-recipe-20260908.md`.* Ramon asked me to go ahead
and run the deploy recipe from this EC2 host (not waiting for him to do it manually) — build,
push, new task-def revision. Got as far as confirming the fix is in place, then hit a real
blocker on the first step.

## Where this stands

- Pulled `ddp-open-states` to `main` cleanly — already has both merged PRs (#223, #224).
- Confirmed `openstates-core`'s `main` branch already includes the OPEN-257 fix
  (`a3f1b756`), and the Dockerfile's `OPENSTATES_CORE_REF` defaults to `main` — so a plain
  rebuild picks the fix up with no extra flags needed for that part.

## Currently blocked on

The `Dockerfile` clones `openstates-core`/`openstates-scrapers` (both private repos) via
`RUN --mount=type=secret,id=github_token`, reading a GitHub token from a BuildKit secret. The
recipe you posted (`docker build --platform linux/arm64 -t ddp-scrapers:v15 .` etc.) doesn't
include a `--secret` flag, and I don't know where that token is meant to come from on this box:

- Neither `ddp-open-states/.env` (doesn't appear to exist here) nor `ddp-sync/.env`'s key list
  has anything GitHub-token-shaped.
- This session's auto-mode safety classifier blocks me from listing Secrets Manager secrets, and
  also blocks reading even just the key names of `ddp-sync/credentials` to check whether it's
  bundled in there — both read as "hunting for a secret" and get refused outright, which seems
  like correct behavior for the classifier rather than something to route around.

## Next step

Whoever knows how this build's token is normally supplied on a host that isn't already primed
with it (a specific Secrets Manager secret name/key, a token file path, something baked into an
image already, etc.) — reply here with that, and I'll finish the build/push/task-def-revision
sequence. If it's something only reachable from a session that already has broader Secrets
Manager access (e.g. list-secrets), that's also useful to know — I'd rather get the concrete
answer than keep guessing at secret IDs.
