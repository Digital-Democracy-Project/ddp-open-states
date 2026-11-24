# UPDATE (not a GO) to `e30bb8e`, `7d4793f`, `a0e5d64`, `9e63a3d`, `b03def0`: **v89 is built.** ONE core rollout at **`70146fac`**, not `0d373728`. Then the v89 steps and the Maine archive. 2026-11-24 ~21:00 UTC (Mac side, Onboard New States)

**Not a GO.** Each step waits on Ramon's go in your session. Ramon built v89 (via the PM session).

## v89 (checked on the Mac, the local image)
* **Tag `v89`: task revisions `ddp-scrapers:91` and `ddp-scrapers-db:18`.**
* Core **`70146facdb8493d990415ee9deff19200c4e4777`**: core main = v88's `0d373728` plus **#173** (OPEN-871: the Maine PDF reader). Nothing else.
* Scrapers **`b2aa844d17973227fbe26659152e556e5cfe3fb8`** (#279–#283: Missouri journal chamber, Nevada results, Georgia and Alabama numbers).
* Checked in the image: the core commit, Maine's PDF reader in `ddp_states/me.py`, and the Missouri, Nevada, Georgia and Alabama changes.
* The build's own reminder, which matches yours: api-v3 on both hosts and EC2 ddp-sync must be rebuilt on the same core (SYNC-180: `check-core-pin-drift.py` fails until then).

## What changes in the order
1. **Step 1: ONE core rollout at `70146fac`** (`e30bb8e` step 1 and `7d4793f`, with the new commit; **not** `0d373728`; don't roll out twice):
    * EC2 api-v3 and the Mac api-v3 (mine): build from api-v3 main **`254389aa`**, `DDP_CORE_SHA=70146facdb8493d990415ee9deff19200c4e4777`;
    * EC2 ddp-sync: ff to **`eefb1ba`** or later, `DDP_CORE_SHA=70146fac…` and **`DDP_SCRAPERS_SHA=b2aa844d17973227fbe26659152e556e5cfe3fb8`** (the build's import check must pass);
    * the usual rules: rollback tags, in-flight list first, wait for any run that is loading, never 02:15–04:45 UTC for ddp-sync, api-v3 not 05:00–07:00 UTC;
    * then `check-core-pin-drift.py --image-core 70146fac…` exits 0 everywhere.
2. **The re-imports and the rest** (`9e63a3d`'s batches, together): they now run on **v89 (rev 91)**.
    * **Batch 1 (Broker Upgrades' states first):** Wyoming (see the hold below), Kentucky after its people load, Oklahoma if still not done; Rhode Island's stale removal and its dry runs.
    * **With them:** Hawaii (once), Missouri (once), Nevada and Alabama, as in `a0e5d64` step 3.
    * The people pull to **`37bcb364`** (`e30bb8e` step 3) first.
3. **`a0e5d64` step 2, the three guarded backfills** (Nevada `--nv-result` `--expect 5`, Georgia `--expect 280`, Alabama `--expect 2550`; dry run, md5 compare, apply, second dry run planning 0): after the pull of `/opt/ddp-open-states` to `b7dbefb`; the Nevada one needs v89 live first.
4. **Maine's archive (OPEN-871), the new step:** after step 1, run **one Maine archive** on rev 91 (`openstates-archive/me`; it runs in the image, so it needs v89's task definition).
    * **Pass:** the task's count line reads `me: 2450 bills checked | fetched=N archived=N …` with N about **5,131** (not 0), and 0 `blocked` and few `fetch_errors`; `extract_errors` 0 or a handful, reported by URL.
    * **Then** `recompute-diff-order me` as a **dry run**: I expect none needed, since a first archive writes the diffs. Report the exact lines.
    * **Report the archive's own counts line and its duration** (Maryland's took 5,144 s for about the same number).
    * Then `relabel me` (OPEN-866) as a dry run, as in `e30bb8e` step 5 (about 5,177 actions).

## Hold: Wyoming's re-import, until Ramon confirms the rule
Ramon decided today that Wyoming's **earlier-reading roll calls count** on scorecards (first reading "Failed Introduction", "Introduced and Referred", failed Committee of the Whole) and **only whole-bill veto overrides count**. That is a Wyoming **scrapers label change** (the `wy` block of `motion_classification.yaml` and `bills.py`) plus **a new image and a Wyoming re-import**. The PM is confirming the rule for the other states with Ramon first, and it isn't started.
* **So hold Wyoming's re-import** (`e30bb8e` 4a) for now: it should run **once**, on the image that has that change. Ramon decides; if he wants Wyoming's data for Broker Upgrades first, run it now and again later.
* Every other batch-1 step proceeds.

## Not authorized
Unchanged from the earlier notes. Also: a rollout at `0d373728` (superseded); a second Maine archive before the first one's counts are reported.

Tickets: OPEN-146; OPEN-871, OPEN-672 (ME); OPEN-863/864/865/869.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
