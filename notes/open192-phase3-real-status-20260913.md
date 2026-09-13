# OPEN-192 Phase 3: real current status, checked directly -- code is done, but nothing is actually scheduled to run

## 1. Is `use_fargate` actually `true` in production `ddp-sync` right now?

**Yes**, confirmed live: `/opt/ddp-sync/config/sync_schedule.yaml`'s
`openstates_archive.use_fargate: true`. Traced its git history: landed via `ddp-sync` PR #124
(`feat/open192-cutover-use-fargate-true`, merge commit `94f0df5`), which this host's checkout
has (`git merge-base --is-ancestor 94f0df5 HEAD` confirms it).

**But this doesn't matter functionally right now.** The entire `openstates_archive` scheduled
job -- Fargate or not -- is disabled at a higher level:
`scheduler.py`'s own gate is `self.settings.openstates_archive_enabled AND
config.get("enabled", False)`, and this host's `docker-compose.prod.yml` hardcodes
`OPENSTATES_ARCHIVE_ENABLED=false`, confirmed live in the running container's env and in
tonight's own startup log: `openstates_archive: disabled — skipping`. That flag's own comment
dates from the original OPEN-193-canary-only mandate ("this host's mandate is specifically the
OPEN-193 canary, not general OpenStates archive maintenance") -- it predates all the later
Fargate-cutover validation work and was never revisited. **So right now, on this host, zero
archive jobs are scheduled to run automatically, regardless of `use_fargate`.**

## 2. Has a real Fargate-launched archive run against rev19+ actually completed and archived real documents?

**Yes, extensively, but not via the scheduler.** This was already done and documented in an
earlier session (2026-09-10, task-def revision 23/`v19`): `az`/`mi`/`ma`/`us` all confirmed
fully clean (`persist_errors=0`, `s3_verified` == `archived` exactly), including a literal,
directly-confirmed `GLACIER_IR` S3 object (`aws s3api head-object` on a real bill's real
archive_location, confirmed `StorageClass: GLACIER_IR`). Full detail already on ops-handoff
from that date (`notes/rev23-us-clean-all-four-confirmed-20260910.md`) if useful.

**Important distinction**: every one of those validation runs was launched manually (direct
`aws ecs run-task` invocations against task-def rev23, one jurisdiction at a time), not by
`openstates_archive`'s own scheduled job -- because that job has been disabled the whole time
(see #1). So the underlying mechanism is proven correct end-to-end, but the actual production
*schedule* has never once fired it, not even once, since it doesn't run at all right now.

## 3. Was PR #124 merged?

**Yes** -- confirmed directly, merge commit `94f0df5`, included in this host's current
checkout.

## Bottom line

Code-wise, Phase 3 is genuinely done: the PR is merged, the flag is flipped, and the mechanism
has real, direct end-to-end proof it works. But calling Phase 3 "done" in the sense that
matters -- archiving actually running in production -- would be wrong: nothing has been
scheduled to fire on its own here since before any of this validation work started, because of
a leftover flag from a different, earlier mandate. This is the same "committed != running"
gap class as OPEN-247.

**Not flipping `OPENSTATES_ARCHIVE_ENABLED` myself** -- that's a real production change
(newly enabling a whole feature's automatic recurring execution against real data) and Ramon's
call, not something to do on my own judgment. Let me know if you want me to flip it (and
restart `ddp-sync`) once you've confirmed that's the right call, or if there's a reason it
should stay off that I'm missing.
