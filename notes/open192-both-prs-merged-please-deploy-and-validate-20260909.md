# OPEN-192 both PRs merged -- please build/deploy the image, then validate one real Fargate archive run

Ramon reviewed and merged both PRs himself (independent session):

- [ddp-open-states#225](https://github.com/Digital-Democracy-Project/ddp-open-states/pull/225) --
  `cloud_archiver.py` + `RUNNER_SCRIPT` dispatch in `docker-entrypoint.sh`
- [ddp-sync#123](https://github.com/Digital-Democracy-Project/ddp-sync/pull/123) --
  `_run_archive_fargate()`, gated behind `openstates_archive.use_fargate` (currently `false`)

Both are on `main` now. Ramon wants to actually cut over (**flip `use_fargate` to `true` now**,
not wait on the RDS backfill work), so this is the real deploy, not just a rebuild-and-check.

## Step 1: build + push the image, register a new task-def revision

Confirmed fresh just now: current live state is image tag `v14`, task-definition `ddp-scrapers`
revision `18`. This deploy would be `v15` / revision `19`.

```
docker build --platform linux/arm64 --secret id=github_token,env=GITHUB_PERSONAL_ACCESS_TOKEN \
  -t ddp-scrapers:v15 .
docker tag ddp-scrapers:v15 350941939790.dkr.ecr.us-east-1.amazonaws.com/ddp-scrapers:v15
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 350941939790.dkr.ecr.us-east-1.amazonaws.com
docker push 350941939790.dkr.ecr.us-east-1.amazonaws.com/ddp-scrapers:v15
```

Then register a new task-definition revision pointed at `:v15` (same family, execution role,
task role, cpu/memory/runtimePlatform as revision 18 -- only the image tag changes).

**Same open question as before, still unresolved as far as this branch shows**: does this host
have `GITHUB_PERSONAL_ACCESS_TOKEN` provisioned yet for the build secret? No update since
`notes/open257-deploy-secret-flag-confirmed-20260909.md` confirmed the flag/env-var name but
left the actual value as something Ramon needed to provision out of band. If it's still missing,
that's the real blocker here, same as it was for the earlier deploy attempt -- please check
before assuming this is just a straightforward rebuild.

## Step 2: I'm opening a small PR to flip the flag

Separate PR incoming (ddp-sync, `config/sync_schedule.yaml`, `use_fargate: false` -> `true`) --
not doing this as a direct push to the live checkout, per this repo's own standing PR-discipline
rule for `ddp-sync` config changes. **Please don't merge/pull that flag flip until Step 1's new
task-definition revision is confirmed live** -- flipping it first would have the next scheduled
05:00 UTC archive run launch a Fargate task with `RUNNER_SCRIPT=cloud_archiver.py` against
whatever image revision is *actually* registered, and if that's still `v14`/rev 18 (no
`cloud_archiver.py`, no `RUNNER_SCRIPT` dispatch), it fails at container startup, not cleanly.

## Step 3: real end-to-end validation, one jurisdiction, before trusting the full daily batch

Once the new revision is live, please do one real, single-jurisdiction validation before the
flag applies to the whole `openstates_archive.jurisdictions` list. Pick a small/quiet one (`ut`
or `az`, not `us`/`mi`/`fl` -- avoid a multi-hour run for a first smoke test) and either:

- call `run_single_archive_job("ut", config={**normal_config, "use_fargate": True})` directly, or
- use the manual `/trigger/openstates-archive` endpoint with an explicit override if it supports
  one already.

Confirm for real: the Fargate task actually launches, `RUNNER_SCRIPT=cloud_archiver.py` actually
runs (not the image's default `cloud_collector.py`), it reads from RDS (not the Mac's local
Postgres -- `RDS_DATABASE_URL` needs to be set in whatever environment invokes this), and a real
document lands in `ddp-bill-archive` at `GLACIER_IR` (matching OPEN-257's storage-class fix).
Report back with the actual `run_id`/task ARN and what the completion record shows -- this is
the "real Fargate-launched run" validation gap the merge comment called out, separate from the
direct-call validation OPEN-192 already did against `_upload_and_verify_direct()` weeks ago.

Once that's confirmed clean, the daily batch should be safe to leave on `use_fargate: true` for
real.
