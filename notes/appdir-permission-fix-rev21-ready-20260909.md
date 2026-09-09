# Root cause found and fixed: /app was root-owned -- v17 built, pushed, registered as rev 21

*Replies to `notes/batch-fetch-errors-full-detail-20260909.md`.* Real bug, fixed at the source.

## Root cause

The Dockerfile's `WORKDIR /app` + `COPY` steps run before `USER scraper` switches the container
to its non-root runtime user -- so `/app` ends up root-owned, and the `scraper` user can read/
execute what's in it but can't create new entries. `archive_bill_versions()` stages every
fetched document under `/app/_archive/...` before uploading to S3, which is exactly what failed
on every single fetch across `az`/`mi`/`ma`/`us` in today's batch.

## Fix and verification

- One `chown -R scraper:scraper /app` added right before `USER scraper`. Rebuilt with
  `--no-cache` (v17, per yesterday's build-cache lesson).
- Confirmed directly inside the built image: `/app` is now `scraper`-owned, a real write to
  `/app/_archive/bills/raw/test/file.txt` succeeds as the `scraper` user (not root, not
  assumed), and yesterday's `concurrent_writes` fix is still present.
- Smoke-tested both entrypoints via `RUNNER_SCRIPT` -- both still load and fail cleanly on
  missing `MEMORY_BUCKET`.
- Pushed to ECR, confirmed live via `describe-images`. Registered task-definition revision
  **21** (identical to 20 except the image tag). Revision 20 untouched.
- PR: https://github.com/Digital-Democracy-Project/ddp-open-states/pull/228

## Filed separately, not fixed by this PR

- **OPEN-263**: the code-side blind spot this permission bug happened to expose --
  `archive_bill_versions()`'s local-persist failure handler doesn't increment any counter at
  all, so a systemic write failure (this one, or a future different one) is indistinguishable
  from "nothing new to archive" in the summary line. Real fix needed in `openstates-core`, not
  this container config.
- **SYNC-58**: `us`'s separate fatal crash (a dropped Django DB connection ~14 minutes into the
  run, `OperationalError: server closed the connection unexpectedly`) -- unrelated to the
  permission bug, still needs its own investigation.

## Please re-run

Same all-9-jurisdiction batch, task-definition `ddp-scrapers:21` explicit revision,
`RUNNER_SCRIPT=cloud_archiver.py`, credential still resolved fresh per launch (OPEN-260's fix).
This should be the run that finally produces a real `archived > 0` and the literal `GLACIER_IR`
proof -- assuming the actual documents being fetched today have real content to archive, which
today's `fetched` counts (az=32, mi=12, ma=74, us=68) suggest they do. `us` will likely still
crash on the separate DB-connection issue (SYNC-58, not fixed by this PR) -- worth confirming
whether it now gets further before that happens, but don't expect it to complete clean yet.
