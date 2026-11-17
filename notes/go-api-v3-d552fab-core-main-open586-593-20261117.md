# GO: rebuild EC2 api-v3 now from api-v3 main `d552fabd` (core main `44c3b8dc8` = v62's core): OPEN-586, OPEN-593, OPEN-602. Not #70. 2026-11-17 (Mac side)

**Ramon, 2026-11-17 ~03:45 UTC:** "go, post the api-v3 rebuild request while you rebuild the api-v3 here on the Mac". He is deploying the broker (ddp-broker-py #737, OPEN-544) in parallel; this rebuild is safe with either broker.

**Why now:** EC2 api-v3 runs core `96445eb` (11-16). The stored data now follows v62's core `44c3b8dc8`: Virginia's comparisons were rebuilt at 02:49 (`705f13a`), and GA/NV/OR are being archived on v62. Until api-v3 is rebuilt, the version lists it serves for Virginia (and Georgia) use the old order.

**What ships:**
* api-v3 #69 (OPEN-586, merged 11-16): no pin file; the build installs core **main** at its current commit (`deploy/Dockerfile.ddp`, `ddp-open-states #389`).
* core main `44c3b8dc8` brings OPEN-593 (Virginia substitutes by LIS file number), OPEN-602 (Georgia version stages and order), OPEN-578, OPEN-580 and the rest of v62's core.
* **Not** api-v3 #70 (OPEN-544, still open): `/ddp/enrollment` keeps serving `actions` this time.

## Steps (the `52fcaf5` / `07a9d85` method)
1. **Check first:** `git ls-remote https://github.com/Digital-Democracy-Project/api-v3 refs/heads/main` must be **`d552fabd8…`**. If main has moved (for example #70 merged), **stop and report**: do not build.
   Core: `git ls-remote https://github.com/Digital-Democracy-Project/openstates-core refs/heads/main` should be **`44c3b8dc8…`**; if it moved, report it, and build anyway only if step 4's check is expected to fail (say so).
2. Pull `/opt/ddp-open-states` (already at `8afea0a1` from tonight's rollout, which has #389's `deploy/Dockerfile.ddp`) and api-v3 to `d552fabd`.
3. Tag the running image `ddp-openstates-api:pre-306b4f5` (rollback); build; `up -d --no-deps api` (the api service only).
4. **Gates:**
   * the container imports `openstates.utils.version_ordering`; healthy; postgres untouched;
   * `python3 check-core-pin-drift.py --image-core 44c3b8dc82a0f296b68c3bf2a2e6e2454e5b29b9 --container ddp-openstates-api-1` from `/opt/ddp-open-states`: **exit 0**. Report its output;
   * `/ddp/enrollment` still answers (16 jurisdictions, `actions` present, no `newest_first: true`);
   * Virginia spot check: HB 1432 (2026) versions in order Introduced, Criminal Subcommittee Substitute, Courts of Justice Substitute, Delegate Mehta Substitute (latest = Mehta).
5. **Rollback** if a gate fails: retag `pre-306b4f5` as `:local`, recreate `api` only. Rebuilding an older commit does not roll back (it would install today's core main).

## Not authorized
api-v3 #70 or a manifest rollout (both wait for the broker, then go together); any data change; ddp-sync or the broker.

The Mac side rebuilds the Mac copy (:8002) the same way now.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
