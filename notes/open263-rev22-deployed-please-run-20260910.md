# OPEN-263's fix is built, pushed, and registered as task-definition revision 22 -- please run it

Both companion PRs for OPEN-263 are merged and independently re-verified (your own comment on the
ticket, 2026-09-10 00:40 -- reproduced the pre-fix `DJANGO_SETTINGS_MODULE` failure, re-ran the
full 717-test suite against real Postgres). This note is the next step: getting that fix actually
running in Fargate, since a merge alone doesn't deploy it.

## What's been done

- Pulled `ddp-open-states`'s `main` locally (has PR #229's `cloud_archiver.py` regex fix) and
  confirmed `openstates-core`'s PR #45 is merged to its own `main` (the Dockerfile clones that
  fresh at build time).
- Built `ddp-scrapers:v18` with `--no-cache` (this repo's own standing methodology, OPEN-247 --
  never trust Docker's layer cache against a moving `git clone main` target).
- **Confirmed the fix is actually inside the built image**, not just assumed: exec'd into it and
  grepped the real `text_extract.py` and `cloud_archiver.py` for `persist_errors` -- present in
  both, in the positions the code changes describe.
- Smoke-tested the entrypoint (`RUNNER_SCRIPT=cloud_archiver.py`, no state arg) -- loads and fails
  cleanly with the expected usage message.
- Pushed to ECR: `350941939790.dkr.ecr.us-east-1.amazonaws.com/ddp-scrapers:v18`.
- Registered task-definition revision **22** (family `ddp-scrapers`), identical to the current
  revision 21 except the image tag. Revision 21 (image `v17`) is untouched.

## Please run

The backfill-scope note (`notes/backfill-scope-decided-split-filed-20260910.md`) already
established that OPEN-263's ~624-row incident set (`us`, `az`, `mi`, `ma`'s `is_error=False`
portion) doesn't need a separate backfill script -- a normal archive run against those four
jurisdictions, now that the skip-check treats `archive_location IS NULL` as retryable, recovers
them as a side effect. Please run the archive for **us, az, mi, ma** using **task-definition
revision 22 explicitly** (not just the family's latest, in case anything else registers a revision
in between), same as previous validation rounds.

Worth watching for in the output beyond the normal counts: the new `persist_errors` field in the
summary line (should read `persist_errors=0` on a clean run, confirming yesterday's container
permission fix and this fix aren't fighting each other), and that jurisdictions with previously
stuck rows show `skipped=0` for those specific documents rather than treating them as done.

## Also still open: OPEN-266's data request

Unrelated to the above but still waiting on you: `notes/open266-data-request-20260910.md` (filed
earlier today) asks for row-level production data on MA's ~75 excess `is_error=False` rows and
VA's 4 rows -- both predate the 2026-09-09 incident and need their own root-cause, blocked on data
this dev checkout can't pull directly (no RDS/Secrets Manager access from the local IAM user).
Whenever convenient, not urgent relative to the rev-22 run above.
