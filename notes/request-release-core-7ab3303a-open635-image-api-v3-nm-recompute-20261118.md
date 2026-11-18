# REQUEST (each part waits on Ramon's go): release core `7ab3303a` (OPEN-635, New Mexico's "Final Version" stage): scrapers image v68, then api-v3 at the same core, then `recompute-diff-order nm` (dry run, then commit on a GO). 2026-11-18 (Mac side)

**Why:**
* NM fails one Stage 3 gate: 129 of 1,112 versions (11.6%) have no stage, all of them NM's "Final Version" (the text as finally passed).
* openstates-core #131 (merged `7ab3303a85ff177ad319516752736c8233b2de30`) classifies it as final passage, the same as NC's "Ratified".
* With that core on the path, the gate reads **0 of 1,112 (0.0%)** on the Mac replica.
* A stage-reader comparison of every (state, version name) pair on the replica (24,087) changes **only** NM's 129 Final Versions.

**Core since v66/v67's `94082df`:** only #131 (`ab49d5c`, `version_ordering.py` and tests). **No migration, no model change.**

## Part A, on the Mac (not yours)
1. On Ramon's go: `deploy-scrapers-image.sh` builds **v68** (the live one is v67 = revision 70). It records core `7ab3303a`, and I post the revision here as an `update-` note.
2. Then the Mac's api-v3 (`refresh-api-v3.sh`, which builds at the live image's core), by me on the same go.

## What I need from you (Part B, after my update note names v68's revision)
1. **EC2 api-v3 at core `7ab3303a`,** on Ramon's go. The same method as your checkpoint `a630172`:
   * tag the running image for rollback (`:pre-v68`);
   * build with `DDP_CORE_SHA=7ab3303a85ff177ad319516752736c8233b2de30` (`docker-compose.rds.yml`);
   * `up -d --no-deps api` only.

   **Gates:**
   * healthz 200 before and after;
   * `check-core-pin-drift.py --image-core 7ab3303a85ff177ad319516752736c8233b2de30 --container ddp-openstates-api-1` exits 0;
   * NM HB 4 (2026) versions read "introduced version" … "Final Version" last.
2. **`recompute-diff-order nm` dry run** (read only), core `7ab3303a`:
   * `os-text-extract recompute-diff-order nm --dry-run --list /home/bitnami/ops/step-open635/nm-dry.csv`, after exporting NM's stored comparisons as the backup, as in `e4a007a` step 2.
   * **Baseline** (Mac replica, 21:45 UTC 11-18): NM has 1,113 version documents in 812 bills; 171 have a comparison. All 129 Final Versions have none: they were outside the lineage, so they never got one.
   * **Expected:** `nulled=0`, 0 errors, and `corrected` about **129** (each Final Version gains its comparison; the other comparisons should stay the same). **Outside 100 to 140, or any nulled: stop and report.**
   * Report the exact lines and the list's md5. **The commit holds until a GO note.**

## Timing (real reasons only)
* api-v3: not 05:00 to 07:00 UTC (the scorecard chain reads it).
* The NM recompute: not while an NM scrape runs. NM's weekly run is Sunday 11-22 02:00 UTC, and the recompute is best done before it, so Sunday's diffs come out right.

## Not authorized
* The recompute commit (needs its own GO).
* Any other state's recompute.
* LegBot for NM.
* Any manifest change.
* ddp-sync's rebuild: that is SYNC-180's own request, which should take core `7ab3303a` or later.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
