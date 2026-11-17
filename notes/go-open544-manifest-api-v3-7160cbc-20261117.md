# GO: OPEN-544 last step. Roll out ddp-open-states main `487c06f` and rebuild EC2 api-v3 from main `7160cbcf` (#70). 2026-11-17 (Mac side)

**Ramon, 2026-11-17 ~05:10 UTC:** "merged 70 and 391". He also chose (pop-up) "Rebuild now, accept" for the core gap described in step 4.

**Why now:** broker `f8137857` is live (your `a77c7ff9`, `1e23e5d3`) and carries #737, so the broker no longer needs the `actions` field. This step removes it:
* ddp-open-states #391 (`487c06f`): no state has `actions.newest_first` any more. Every state's actions are stored oldest first (US reversed 02:11, `28de4d6`; LA/NE/NC earlier).
* api-v3 #70 (`7160cbcf`): `/ddp/enrollment` stops serving `actions`.

## Rules
* PA's 04:00 run may continue: the pull changes only the manifest file, and running Fargate tasks keep what they started with.
* A stop is harmless. Report it; do not retry past what a step says.

## Steps
1. **Check first** (`git ls-remote`):
   * api-v3 main = **`7160cbcf1…`**;
   * ddp-open-states main = **`487c06f6d…`** (a later docs-only commit is fine: report it);
   * openstates-core main = **`b5728c43…`** (core #116, OPEN-608). If core moved past it, **stop and report**: do not build.
2. **Manifest rollout:** pull `/opt/ddp-open-states` to main the usual way. `grep -c newest_first jurisdictions.yaml` gives only comment lines (no `newest_first:` key under any state). Run `check-jurisdiction-drift.py` the usual way and report.
3. **api-v3:** tag the running image `ddp-openstates-api:pre-7160cbc` (rollback; it is `d552fabd` on core 44c3b8dc). Pull api-v3 to `7160cbcf`, build, `up -d --no-deps api` (the api service only). Postgres untouched.
4. **Gates:**
   * healthy; the container imports `openstates.utils.version_ordering`;
   * `python3 check-core-pin-drift.py --image-core 44c3b8dc82a0f296b68c3bf2a2e6e2454e5b29b9 --container ddp-openstates-api-1`: **expected exit 1**, with exactly one disagreement: installed `b5728c43…` vs image `44c3b8dc…`. Ramon accepted this gap (pop-up, 05:15): core #116 changes only how vote voters are resolved during an import (`openstates/importers/base.py`), code api-v3 never runs, so api-v3 serves the same answers. The next scrapers image (needed anyway for Oregon's joint-committee voters) closes it. **Any other disagreement, or exit 2: roll back.** Paste the output;
   * `/ddp/enrollment` (direct and through the broker): the same jurisdiction count as before step 2, and **no entry has an `actions` key**;
   * Virginia HB 1432 (2026) versions still in order, latest = Delegate Mehta Substitute;
   * broker: after its next enrollment re-read (or a cache clear, if you did one last time), no error or warning in web/celery about enrollment or `actions`. Report the time you read it.
5. **Rollback** if a gate fails: retag `pre-7160cbc` as `:local`, recreate `api` only. Then report; do not revert the manifest (the broker reads a missing field as oldest first, which is now true for every state).

## Not authorized
A scrapers image or task-definition change; any data change; broker or ddp-sync changes.

The Mac side rolls out the manifest and rebuilds the Mac api-v3 (:8002) the same way now, and runs `validate_bill_stages` (read only) against its replica for every live state.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
