# Request: switch the broker and ddp-sync to read the jurisdiction manifest (OPEN-318 cutover), 2026-11-02

Ramon's decision (2026-11-02, /ask-me): **do the switch now**, so OPEN-318 can close and pilot #2 is unblocked. This reverses his 11-01 "leave the broker on `env`" for the switch only; the Massachusetts step (OPEN-68) is still its own step and is NOT part of this request.

It is configuration only, no new code, and every step has a stop condition and a rollback. **Do the read-only checks first. If any stop condition is true, do not switch; reply with what you saw and wait.** Do not print secrets. Do not change anything not named here.

## Step 0 (read-only): are we ready?
From your 10-30 reply (`reply-open318-proof-...`) the drift check runs and the broker's list equals the manifest (8 of 8); the one disagreement is MA in ddp-sync's effective `DDP_OPENSTATES_JURISDICTIONS`. Please confirm today, per host:
1. The ddp-open-states checkout is current on `main` (`git -C <openstates_root> log -1`), the EC2 bind mount included (nothing pulls it automatically).
2. ddp-sync has logged `jurisdiction_manifest_agrees` at start-up and from the daily check for a full weekly cycle, with **no `jurisdiction_manifest_disagrees` other than the MA one** and no `jurisdiction_manifest_unusable`. (The Mac's older `unusable` warning was due to clear at its next restart; say whether it did.)
3. The deployed `sync_schedule.yaml` on each host has all six lists.
4. The broker can read `GET /ddp/enrollment` (200, `manifest_mtime` recent).
**Stop if** any of 1 to 4 fails, or if you see any disagreement besides MA.

## Step 1: ddp-sync, Mac first, then the EC2-broker host
Per ddp-sync `primitives.md` ("Cutover checklist"): add `JURISDICTION_MANIFEST_MODE=authoritative` to that host's environment (not the shared secret), restart ddp-sync the usual way, then read the start-up log. **Mac first; read its log and the next daily drift-check line; only then the EC2-broker host.** Nothing may be in flight at a restart (in-flight record 0, no scrape or archive job running).
**Stop and roll back if** the start-up log shows `jurisdiction_manifest_unusable`, any list is empty, or the scheduler's job count changes from before (it was 19 on the EC2 host on 11-02 00:37 UTC). Rollback: remove the env var and restart.
**Not wired on purpose** (still yaml only, per primitives): scheduler registration of scrape/archive jobs, `_cloud_path_owns`, `_memory_backend_enabled`, `maybe_trigger_archive_after_scrape`, and the per-feature opt-in lists. Authoritative mode does not change those.

## Step 2: the broker
On each broker host, set `DDP_ENROLLMENT_SOURCE=manifest` in the broker's `.env` and recreate **only the broker containers** (web, celery, celery-beat; name them explicitly, never an unscoped recreate that touches the shared database). `DDP_OPENSTATES_JURISDICTIONS` stays set: it is the last-resort fallback and the boot guard needs it. In manifest mode the broker fetches `/ddp/enrollment`, keeps the last good answer if api-v3 is unreachable, and falls back to the env list.
**Before and after, record the routed list** (the effective replica list, for example the `/explore` pills or the broker's own log line). **Stop and roll back if** the effective list after the switch differs from `MI,UT,US,VA,AZ,WA,FL,NC` (the manifest's `replica_routing` today), or the broker logs `enrollment manifest: ... could not be asked` for more than a minute. Rollback: set it back to `env` and recreate the same containers.

## Step 3: prove it
Run the daily drift check once by hand on each host (`POST /trigger/openstates-scrape/drift-check`) and `check-jurisdiction-drift.py --live prod-broker:DDP_OPENSTATES_JURISDICTIONS=<the broker's value>` with `--ddp-sync-root`. Expect exit 0 except the known MA line.

## Reply
Reply when done (or at the first stop) with: for each host, the commit running and time (UTC); the Step 0 evidence (the log lines, counts only); before and after of the broker's routed list; the drift-check outputs; whether anything was rolled back. If **MA is still the only disagreement**, say so plainly; do not try to resolve it.

## Not asked
No Massachusetts change (it joins the master list and the broker's only after readiness, the roster check and parity, per Ramon 11-01). No change to schedules, task definitions, secrets, or any state's list contents.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
