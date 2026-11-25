# REQUEST (not a GO): **go-live for Hawaii, Rhode Island, North Dakota and Kentucky: one manifest rollout, dry run first.** The change is ddp-open-states **#494** (head `2eb6cf48414f54e0106fab841d8d037a1474e3c5`, CI green, **not merged yet**). Missouri is NOT in it (it goes live in a later rollout, only after its version-comparison cleanup is committed). ~00:10 UTC (Mac side, Onboard New States)

**Not a GO.** Ramon decided on 11-25 (via the PM) that these four go live in the next manifest rollout, dry run first. **He gives the go in your session naming this note;** please confirm it with him. **This request starts only after the PM has merged #494** (I will say so on the branch, or you will see the merge on `origin/main`).

## What changes (read from the PR: `jurisdictions.yaml` only, 20 lines, five edits in each of four blocks)
For each of **hi, ri, nd, ky**: `status: scraping` → `live`, and `enrollment.search_refresh`, `embedding`, `api_smoke_test`, `qa_sweep` false → true (exactly what #480 did for New Mexico). **Nothing else changes for these states:** `replica_routing` and `legbot_replica` stay **false** (the decision did not name them; Ramon's separate call, and Rhode Island's scorecard switch, BROKER-590, is also separate).

## Why they are ready (what I verified on the Mac replica, 11-25; production is your reading)
* **Hawaii:** both re-imports verified; unmatched person votes **1 of 285,813** ("Garcia; and" only); 0 of 1,182 Senate passage roll calls without person votes; 6,728 bills; recompute and relabel dry runs **0**.
* **Rhode Island:** v95 re-import verified; **1,324** passage events; HB 7127 Senate roll calls 14; **0 of 79,412** unmatched; relabel and recompute dry runs 0.
* **North Dakota:** text refresh, recompute (3 flags) and relabel (520) committed and verified; relabel dry run 0.
* **Kentucky:** loaded 11-24 on core `70146fac`; **0 of 61,568** unmatched; recompute committed earlier (your note); its broker rules (migration 0117) are live since the 558f169a release (your checkpoint).

## The steps (the usual manifest rollout, with the lessons of 11-25)
1. **Gate:** #494 is on `origin/main`. Read the **per-state diff of the deployed copy against main** before rolling out (as you did on 11-25) and **report any state other than these four that would change**; if something else would, stop and tell me (the manifest copies all of main).
2. **Pull first, then the script** (the host's validator checks the incoming file; `rollout-manifest.sh` can refuse a change that adds or removes a required field): `/opt/ddp-open-states` to main, then **`bash deploy/rollout-manifest.sh --host ec2 --ddp-sync-root /opt/ddp-sync --dry-run`**; it must exit 0 and say the manifest is valid and agrees with ddp-sync. **Report the dry run's lines, do not roll out from it.**
3. **On the go: the real run** (the same command without `--dry-run`; the script stops itself within 10 minutes of the 2:00 job, as on 11-25). Then the checks as on 11-25: md5 of the checkout file, the api-v3 copy and the file inside the container all equal; api-v3 healthy, no restart; `check-core-pin-drift` exit 0; ddp-sync `/schedule` still 35 jobs; ddp-sync's own read of the manifest shows `status live` for these four (and `state_loads_on_fargate` true for az only).
4. **No ddp-sync restart is needed** (it reads the file by modification time). The Mac host's own copy (`--host mac`) is **not** part of this request.

## Watch after the rollout (new work you will see)
* **First embedding and search-refresh passes** for the four states run in ddp-sync's process and take hours (Hawaii 6,728 bills, Rhode Island 3,011, North Dakota 1,106, Kentucky 1,737). The embedding has no in-flight record, so **apply your narrow restart rule: no ddp-sync restart while a state holds a pipeline lock with no collection task.** Please post when each has finished.
* The **API smoke test and the QA sweep** start for these states: report any failure by state; a failure stops nothing, but tell me.

## Not authorized
Missouri; `replica_routing` or `legbot_replica` for any state; any broker switch (scorecard or state list); the Mac host's rollout; a ddp-sync restart; any change beyond the four states' five edits. **Rollback if you see a problem:** revert those 20 lines in a PR, merge, roll out again; tell me first.

Tickets: OPEN-668 (HI), OPEN-665 (RI), OPEN-663 (ND), OPEN-667 (KY); OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
