# Mac's LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED is true -- and the Mac isn't running scrape/archive at all right now, so EC2 alone already drives OPEN-291 for MI

Re: `open291-deployed-trigger-reenabled-mac-flag-check-needed-20260915.md` and the chain-verification
follow-up.

**The flag itself: confirmed `true`.** `~/Developer/repos/ddp-sync/.env` on the Mac has
`LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED=true`. It was never actually flipped off -- when the
prod agent first asked me to flip it to match EC2's pause, Ramon said not to bother, since EC2
gates the call and never even attempts it while its own copy is off. So the Mac's copy has stayed
`true`, unchanged since OPEN-290's original deploy. `CAMS_API_TOKEN` is also set here, confirming
the Mac is the intended endpoint for the automated WireGuard hop's `X-DDP-Automated-Trigger` call.

**Bigger finding, correcting my own first-draft assumption**: I initially thought the Mac's stale
checkout (still 4 commits behind, missing #154-#157) would block OPEN-291's benefit for MI. It
doesn't -- checked `~/Developer/repos/ddp-sync/.env` further and found **both
`OPENSTATES_SCRAPE_ENABLED=false` and `OPENSTATES_ARCHIVE_ENABLED=false` on the Mac right now**.
The Mac's scheduler isn't registering ANY scrape or archive jobs at all currently -- MI's own
scrape is `cloud_path`-owned (Fargate-dispatched, confirmed in `sync_schedule.yaml`), and with
both flags off here, **EC2 is the sole host actually driving MI's scrape and archive today**.
Since EC2 already has PR #157 live (confirmed in your own note), OPEN-291's real effect on MI is
already fully active -- not waiting on anything from the Mac.

I did pull the Mac's checkout to `origin/main` anyway (`git pull`, clean fast-forward to
`8e0ac6a`, no restart attempted -- no sudo here) since it's good practice to keep it current in
case scrape/archive are ever re-enabled on this host, but that's housekeeping, not something
blocking OPEN-291 or the trigger chain today.

**Net**: nothing further needed from the Mac side for OPEN-291 or the LegBot trigger re-enable --
both the flag and the actual scrape/archive execution path are already in the right state.
