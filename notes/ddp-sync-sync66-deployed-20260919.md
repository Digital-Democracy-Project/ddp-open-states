# SYNC-66 deployed to Mac Studio ddp-sync (2026-09-19)

Follow-on to `notes/wa-legbot-backlog-run-complete-20260918.md` -- with the WA backlog run
finished, the `ddp-sync` deploy that had been held pending its completion went out. No new
diagnosis this note, just a deployment record.

## What shipped

`ddp-sync` `main` had a few commits waiting to deploy: **SYNC-66** (`a2c4437` -- fixes
`resolve_touched_sessions()` conflating "genuinely nothing touched" with "couldn't check at
all," which had silently dropped an entire archive run's new content from reaching LegBot; adds
a small fixed retry for the confirmed-transient connection-failure case) plus two docs-only
commits (three-instance topology writeup, votebot/ddp-api EC2's deliberately-diverged branch
note). Deploy was held specifically because a daemon restart would have killed the in-progress
WA full-backlog run (`run_id=938895ee-...`) -- see last night's/this afternoon's notes.

Deployed to the Mac Studio instance only, per the newly-documented three-instance topology:
`git pull origin main` (`4caf8bd` -> `848c068`) then `sudo launchctl kickstart -k
system/com.ddp.ddp-sync`. Confirmed clean: scheduler restarted with the same 2 registered jobs
(`mi_cookie_publish`, `session_pipeline_batch`), congress-legislators cache pre-warmed, no
startup errors, no in-flight run existed at restart time so nothing was lost.

**Deliberately not touched:** the votebot/ddp-api EC2 instance -- CLAUDE.md's new topology
section is explicit that it runs its own permanently-diverged branch
(`feat/rds-openstates-routing-standalone`) and must not be pulled up to `main`. Didn't touch the
EC2-broker instance either; out of scope for this deploy, not confirmed whether it needs SYNC-66
separately.

## Still open, unaffected by this deploy

OPEN-297 (the "No Bill exists" write-rejection bug) is a different code path from SYNC-66 and
was NOT part of this deploy -- still unimplemented. Confirmed still actively recurring
post-restart: the same stuck `bill_openstates_id=ae29346d...` `bill_changelog` answer fails the
identical write on every ~30-min recovery sweep, before and after the restart -- it will keep
doing so indefinitely until OPEN-297 is fixed (harmless log noise, but real evidence the bug is
live). `bill_opposing_orgs` (46.1% failure in the finished WA run) also unaffected and unscoped.

## Ask for whoever picks this up next

1. OPEN-297 is scoped with an agreed fix direction, ready for someone to implement in
   `ddp-sync-dev`.
2. Worth confirming whether SYNC-66 needs deploying to the EC2-broker instance too (not just
   Mac Studio) -- not checked this session.
