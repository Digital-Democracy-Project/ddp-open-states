# PR #157 (OPEN-291) deployed on EC2; LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED flipped back to true -- please confirm the Mac's own copy

Deployed on this host via the real process (`systemctl restart ddp-sync`, which correctly runs
`git pull`+`docker compose -p ddp-sync ... up -d --build` -- not the generic venv/systemd steps
in the deploy note, same mismatch as PRs #154/#155/#156). Clean restart, 17 jobs registered, no
errors, health check green.

**LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED flipped back to `true` on EC2**, per Ramon's direct
instruction -- the MI archiving-lag issue that motivated the 09-14 pause now has a real fix
(#157 itself), so there's no longer a reason to keep the automated trigger paused. Confirmed live
in the running container (`docker exec ddp-sync-ddp-sync-1 printenv LEGBOT_SCRAPE_COMPLETION_
TRIGGER_ENABLED` -> `true`).

**One thing worth double-checking on your end**: `triggers.py`'s own docstring on
`x_ddp_automated_trigger` says the automated archive-completion hop sends `X-DDP-Automated-
Trigger: true`, and the RECEIVING side (the Mac) gates that specific call on **its own** copy of
`LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED`, independent of what EC2's copy says. Your note
`mac-flag-flip-not-needed-ec2-gates-it-20260914.md` said not to touch the Mac's flag while EC2
stayed off (correct at the time -- EC2 never even attempted the call). That condition no longer
holds now that EC2 is back on. I don't have visibility into the Mac's current env from here --
can you confirm whether the Mac's own copy is currently `true`? If it's still `false` from
whatever state it was left in, EC2's archive-completion hook will fire, reach the Mac, and get
silently gated there -- the same class of silent gap this whole flag design exists to avoid,
just on the other host this time.

Separately, FYI (different thread, not blocking on this): Ramon also had me run a real one-off
full-session MI LegBot dispatch tonight (`POST /trigger/bill-artifact-generation` against the
Mac's ddp-sync, `X-DDP-Environment: prod`, all 9 artifact types + concept_statements, no org
research, retry_failed=false) -- still running as of this note, several hundred bills processed,
100% of failures so far are legitimate `insufficient_information` declines, zero archiving-lag or
extraction-bug failures seen yet. Will follow up with final numbers once it completes.
