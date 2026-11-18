# Checkpoint: EC2 api-v3 rebuilt at core 46cc5759 (step B of 59c62e0, per 133855141), all gates pass

Written 04:45 UTC 11-18 (date -u at write time). From the production EC2 host. User's words in session: "i approve the restart for api-v3" (after I asked and said it also needed Ramon's go on the dev side; the user gave the go).

## Checks first (04:43 UTC)
api-v3 main 7160cbc (the checkout is already there; nothing to pull; its history carries no OPEN-556 or OPEN-557 merge, so neither is in this build); openstates-core main exactly 46cc5759208b84343fef325fd8e263f7e58bb324. ddp-open-states checkout 8288fa242 (includes #406's build-time import step and the chambers block; EC2 skips step A as you say).

## Done (04:44:21-04:44:52 UTC)
- Running image tagged **ddp-openstates-api:pre-v65** (image e33937cfe23f) for rollback: retag it as :local and recreate api only.
- Built with **DDP_CORE_SHA=46cc5759208b84343fef325fd8e263f7e58bb324** (the build's import step "import api.main" passed), `up -d --no-deps api` only: compose exit 0, 19 s, down about 7 s, healthz 200 before and after.

## Gates
- Healthy; the container imports openstates.utils.version_ordering.
- `check-core-pin-drift.py --image-core 46cc5759208b84343fef325fd8e263f7e58bb324 --container ddp-openstates-api-1`: **exit 0**, "OK: the scrapers image and 1 api-v3 container(s) all run core 46cc5759...". The expected disagreement is closed.
- /ddp/enrollment through the broker's web container: 200, **17 jurisdictions**, 0 entries with an actions key. (The container's manifest copy carries the chambers block; api-v3 itself ignores it until #71.)
- Virginia HB 1432 (2026) versions in order: Introduced, Criminal Subcommittee Substitute, Courts of Justice Substitute, Delegate Mehta Substitute.
- ddp-sync log: 0 Tracebacks in the 3 minutes after the 7-second gap; PA (pa-ee12bf9e20bd) and the extra Oregon run (or-8290a384c248) were running on revision 68 during it.

Not done: no relabel, no manifest change, no other service touched. The Mac api-v3 is yours.
