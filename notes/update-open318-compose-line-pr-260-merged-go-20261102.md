# Update to OPEN-318: ddp-sync PR #260 is MERGED; you may restore the compose file and pull, 2026-11-02 02:40 UTC

As promised: Ramon merged ddp-sync **PR #260** at 02:31:57 UTC; merge commit `2ea2c06`. On `main` the line is at `infrastructure/docker-compose.prod.yml:84`, `- JURISDICTION_MANIFEST_MODE=authoritative`, the same setting you hold locally (my comment lines differ in wording only).

**Please note: `main` has moved since `476d6d4` (what you run).** Between it and `2ea2c06` there are two more merges that are NOT part of this request: **SYNC-140** (ddp-sync #258: organization research alone, and the request id and redo passed through to LegBot; code in `src/`) and a docs-only close-up (#259). So a plain `git pull` brings SYNC-140's code into the checkout. This request does not ask you to release it, and it changes nothing for the OPEN-318 setting.

What I suggest, your call:
1. **Nothing is urgent.** The setting is already live from your hand edit; no restart is needed for #260 (value unchanged).
2. **When you next pull ddp-sync for any reason:** run `git checkout -- infrastructure/docker-compose.prod.yml` first (your 4 local lines), then pull; the file then equals `main` and the setting stays in force.
3. **If you want to pull now without taking SYNC-140,** say so and I will give you the exact commit to pull to; otherwise treat SYNC-140's release as its own request, which I have not posted.

Reply only if you hit a refusal, or to say which of 2 or 3 you chose.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
