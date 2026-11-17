# GO: New Mexico at `probing` on both hosts (ddp-open-states #412), then New Mexico's people load (OPEN-618). No scrape. 2026-11-17 (Mac side)

**Ramon, 2026-11-17 (pop-up in the onboarding session): "Go: rollout + people load".** The first scrape is **not** part of this. It waits for OPEN-620 (scrapers #125, NM actions stored in the legislature's own order) to be in an image, so NM's history starts in order.

## What I need from you
1. **Gate, before anything:** `/opt/ddp-open-states` main must contain #412's merge. Check: `git -C /opt/ddp-open-states fetch` (SSH), then `origin/main:jurisdictions.yaml` has an `nm:` block with `status: probing`. **If #412 isn't merged yet, stop and report; don't roll out anything else.**
2. **Rollout on EC2,** the usual way: `bash deploy/rollout-manifest.sh --host ec2 --ddp-sync-root <ddp-sync path>`. If the checkout's validator is older than main's, pull first, then run the script (OPEN-532). No real reason to wait for a time slot. It doesn't touch running scrapes; just don't run it during another manifest rollout.
   **Checks:**
   * the script exits 0 and the drift check passes (17 jurisdictions);
   * `/ddp/enrollment`, read from the broker's web container, lists `nm` with status `probing`;
   * ddp-sync's `GET /schedule` has **no** `openstates_scrape_nm` job.
3. **NM people load:**
   * pull `/opt/ddp-open-states/people` to main;
   * run `os-people` from the container's `/opt/venv-openstates/bin/os-people`, `--safe` first, then the load for **nm** only, as for GA/NV/OR on 11-17 (`1fc0d67` step 7A).
   * **Gate:** **0 updated** (NM has never been loaded), **about 289 created** (files on people main: legislature 109, retired 176, executive 4), and no went-missing or retirement line. If created is far from 289 or anything is updated, stop and report.
   * Report the created count, and current NM people afterwards (expected 109 current legislators; House districts 37, 41 and 64 are vacant).

## Afterwards (Mac side)
The Mac side rolls out the same manifest on the Mac and re-reads NM people on the replica.

## Not authorized
Any NM scrape or archive, moving NM to `scraping`, any enrollment flag, any other state's people, any image, task definition, broker, ddp-sync or data change.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
