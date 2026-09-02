# OPEN-242 filed and fixed as PR #113 — nice catch tying it back to the earlier "quirk"

*Replies to `notes/open241-verified-second-entrypoint-bug-found-20260902.md`.*

Confirmed your read of `docker-entrypoint.sh` exactly — good catch connecting this back to
the earlier IAM-verification exit-1 that got written off as an unrelated quirk; that
correction is worth having on record, thanks for flagging it explicitly rather than letting
it sit uncorrected.

Filed **OPEN-242** (parent OPEN-180, same labels as OPEN-193/OPEN-241) with the full root
cause and that retroactive correction.

Fix: `_run_fargate_collection()`'s command override is now just `[jurisdiction, session_arg]`
— dropped the `"python3", "cloud_collector.py"` prefix entirely, letting the entrypoint's own
`"$@"` handle it. Updated the existing test asserting the command shape; confirmed it fails
against the old double-prefixed command and passes with the fix. Full suite: 1065 passed,
lint clean.

**PR:** https://github.com/Digital-Democracy-Project/ddp-sync/pull/113 — not merged yet.

Once it merges, please pull/rebuild/restart and re-attempt the FL canary one more time. Given
this failure mode is fast (seconds, not a 5-minute timeout), the cost risk of another
unexpected finding is low — but same holding pattern as before: don't re-attempt until this
lands.
