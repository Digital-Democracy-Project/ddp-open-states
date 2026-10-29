# Request (read-only): OPEN-318 proof. What did the jurisdiction drift check report, and do the live lists agree with the manifest?

2026-10-29 about 22:15 UTC. Ramon asked me to ask you. **Nothing here changes anything: no pull, no restart, no recreate, no edit, no flag.** Please do not print secrets (read variables by exact name only; report lists, counts and times).

## Why
OPEN-318 ("set the enrolled-jurisdictions list once and propagate it") is built and merged, and it is the first of the three blockers on pilot #2 (OPEN-447). What is missing is **proof from production**, and I have not read any. Your 10-28 00:50 UTC report registered `jurisdiction_drift_check` on this host for 06:20 UTC (enabled True), so it should have run at least twice (10-28 and 10-29 06:20 UTC). No note I can read carries its result. Until it is read, "the manifest agrees with the live lists" is not verified.

## Please read and answer
1. **The drift check's results.** For each run of `jurisdiction_drift_check` since the 10-28 00:43 restart (06:20 UTC on 10-28 and 10-29, and any other): did it run, how long, what it logged (agreement, or each DRIFT line verbatim), and whether it posted a Slack alert. If a run is missing, say so and what the scheduler logged instead.
2. **The manifest on this host, still what you left it.** `GET /ddp/enrollment` `manifest_mtime` against the host file `/opt/ddp-open-states/jurisdictions.yaml` mtime (they matched on 10-28 at 00:13:35.470 UTC); and the host checkout's current commit, in case a pull happened since.
3. **The live lists beside the manifest's, state by state.** Read each of these as it is *now*, and give the list next to the manifest's matching field:
   * the production broker's `DDP_OPENSTATES_JURISDICTIONS` (in `.env` and in the running web, celery and celery-beat containers) against the manifest's `replica_routing`; your 10-26 read was `MI,UT,US,VA,AZ,WA,FL,NC`;
   * ddp-sync's **effective** `ddp_openstates_jurisdictions` (the app's loaded settings, per your 10-26 correction) against the manifest. On 10-26 it held `FL,WA,US,VA,MI,MA,UT,AZ,NC`, which has **MA and the broker's does not**; please say whether that difference is what the drift check flags, and what the manifest says for MA (`replica_routing`, `scrape`, and the other enrollment fields);
   * whether `DDP_ENROLLMENT_SOURCE` is set on the broker (not set on 10-28), and the broker build now (it was `489c6578`; I believe the manifest-reading code, OPEN-329 `a7e996b5`, is not in it).
4. **If you can run it without changing anything:** `check-jurisdiction-drift.py --live prod-broker:DDP_OPENSTATES_JURISDICTIONS=<value as read in 3>` from `/opt/ddp-open-states`, and report its output and exit code. This is the exact line OPEN-330's acceptance names. If it cannot run read-only from there (missing interpreter, a write path, a secret on the command line), say which, and do not work around it.

## What I will do with the answer
Record it on OPEN-330 and OPEN-318 and in the plan (`PLAN-push-button-onboarding.md`), and tell Ramon whether blocker 1 of pilot #2 is cleared. Anything the check flags becomes its own ticket; nothing is changed in production on this request.

## Still unverified on my side
That the drift check actually ran on this host on 10-28 and 10-29 (your note says registered, not ran); the Mac's copy of the same job (06:20 UTC, enabled in its `.env` per the 10-28 plan text) is a separate read and not part of this request.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
