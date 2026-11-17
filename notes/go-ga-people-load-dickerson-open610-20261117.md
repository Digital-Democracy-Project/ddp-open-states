# GO: Georgia people load on production for Sen. Jason Dickerson's other name (OPEN-610, people #26). 2026-11-17 (Mac side)

**Ramon, 2026-11-17 (catch-up pop-up):** "Yes, post the go now".

**Why:** Georgia's vote records spell him "Jason T. Dickerson"; his people file had only "J.T. Dickerson". 35 Georgia Senate member votes are unlinked (Mac replica, 11-17), all this name. people #26 (merged `824bd8c8`) adds the other name. No code, image or data change beyond the people load.

## Steps
1. Pull `/opt/ddp-open-states/people` to main; it must include `824bd8c8` (people #26). If main is behind that, stop and report.
2. `os-people` from the container's `/opt/venv-openstates/bin/os-people`, `--safe` first, as for ga/nv/or on 11-17 (`1fc0d67` step 7A), then the load for **ga** only.
3. **Gate:** the run reports Jason Dickerson updated (other name added), **0 created**, and no "went missing" or retirement line. Anything else: stop and report.
4. Do not trigger a Georgia scrape for this; the next Georgia run (Sunday 11-22 batch) links the votes. Report the load's output and the time.

## Not authorized
Any scrape, image, manifest, ddp-sync, broker or data change other than this people load.

The Mac side re-checks the replica after the next Georgia run (expect 0 unlinked of 1,925 Senate voters).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
