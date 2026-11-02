# Amendment to the OPEN-318 switch request (`ef87f54`): the Mac side is done; the EC2 host is still wanted, 2026-11-02

Ramon switched the **Mac** himself with me, so please skip the Mac in Step 1 and the dev broker in Step 2. Still wanted: **the EC2-broker host's ddp-sync and the production broker**, with every read-only check, stop condition and rollback in the original request. Nothing else changes.

What was seen on the Mac (2026-11-02 about 01:15 to 01:33 UTC):
* **ddp-sync (Mac):** `JURISDICTION_MANIFEST_MODE=authoritative` in its `.env`; restarted 01:14:30 UTC; start-up logged `jurisdiction_manifest_agrees manifest_mtime=2026-10-31T15:49:29+00:00 mode=authoritative`; no `unusable`, no disagreement, no error after it; scheduler 7 jobs.
* **Dev broker (Mac):** `DDP_ENROLLMENT_SOURCE=manifest`; web recreated 01:32 UTC; the setting reads `manifest`, the manifest was read (same mtime), and the routed list is unchanged: `AZ, FL, MI, NC, US, UT, VA, WA` (equal to the manifest's `replica_routing`); status endpoint 200.
* The Mac drift check run before the switch: every list agrees (this checkout current, ddp-sync Mac 4 commits behind main, none touching this).

Two traps learned, for your side: (1) a plain container **restart does not re-read `.env`**, only a recreate does; (2) `infra/scripts/compose-broker.sh` names its project after the repository folder (`ddp-broker-py`), but the running stack is `ddpbroker`, so run it with `COMPOSE_PROJECT_NAME=ddpbroker` and `--no-deps` (my first run without it started a second empty stack on the Mac, which I removed: four containers, three new empty volumes and one network, all created seconds earlier; the real stack was untouched). Check the project name on the EC2 host before you run anything.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
