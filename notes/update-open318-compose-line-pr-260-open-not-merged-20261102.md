# Update to OPEN-318: the ddp-sync compose line is now a PR (#260), not merged yet, 2026-11-02

Thank you for the api-v3 recreate and the clear note. The four lines you added to `/opt/ddp-sync/infrastructure/docker-compose.prod.yml` are now **ddp-sync PR #260** (`e435d9a`, branch `fix/OPEN-318-ec2-manifest-mode`): the same setting `JURISDICTION_MANIFEST_MODE=authoritative`, right after `JURISDICTION_DRIFT_CHECK_ENABLED`, with a 3-line comment, plus a note in `primitives.md`. No code change.

**Nothing for you to do yet.** It is not merged; Ramon merges it. **When it is merged I will post another note here first**, and only then please run `git checkout -- infrastructure/docker-compose.prod.yml` and pull. Until then leave your local edit as it is: it is what is running, and a pull of anything else that does not touch that file is unaffected.

The wording in my commit differs from your local comment lines, so after the pull the file will differ from what you hold today by comment text only; the setting line is identical. A restart is **not** needed after the pull (the value is unchanged); I do not expect any container change from it.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
