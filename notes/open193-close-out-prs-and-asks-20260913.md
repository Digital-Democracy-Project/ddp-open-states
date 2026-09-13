# Closing out OPEN-193/285/286: PRs filed, a few real asks for you

Ramon asked me to actually close OPEN-193 plus its two blocking follow-ups (OPEN-285,
OPEN-286) -- filing PRs, sending each through pm-review, then setting them to In Review.
Working through that now. Three things I need from you (all real production checks, not
guesses I can make from the Mac):

## 1. OPEN-285 (stray hourly people-refresh cron) -- confirm `ddp-sync`'s replacement job actually works

I'm removing `ddp-broker-py/infra/scripts/refresh-openstates-people.sh` (PR
Digital-Democracy-Project/ddp-broker-py#375) on the claim that `ddp-sync`'s own weekly
`openstates_people_refresh` job already covers the exact same checkout via a fuller
pull-then-load (not just `git pull`). Before I say this is safe pm-review's own pushback
was fair: I have the code confirming the mechanism *should* work, but not confirmation it
*has* actually succeeded recently on this host. Can you check real evidence (Redis
flow-history key, likely something like a `people_refresh`-named entry, or CloudWatch
logs for the container) that `openstates_people_refresh` has completed successfully at
least once recently on this EC2 host? If it's never actually run successfully here, that
changes the picture -- I'd want to know before treating the cron's removal as riskless.

Also: please go ahead and remove the live crontab entry itself now
(`17 * * * * /opt/ddp-broker-py/infra/scripts/refresh-openstates-people.sh ...`) --
it's already broken (dubious-ownership error) so there's no downside to removing it
immediately rather than waiting on the PR to merge first.

## 2. OPEN-286 (missing Slack/CAMS alerting credentials) -- can you source real ones?

PR Digital-Democracy-Project/ddp-sync#140 adds a loud startup warning when
`SLACK_BOT_TOKEN` is missing in production -- that's the code-side floor, not the actual
fix. The real fix is provisioning `SLACK_BOT_TOKEN` (and `CAMS_API_TOKEN`/`CAMS_BASE_URL`
if that secondary path is still wanted) on this host's `.env`. `ddp-agents`' own
`failure_watcher.py` already listens on `#automation-errors` for exactly this kind of
alert (its docstring names that channel directly), so a working Slack bot token already
exists somewhere in this fleet for that channel -- do you have access to find/reuse that
same token (Secrets Manager, another host's `.env`, wherever CAMS/Agent Smith's own
Slack credential lives), or does a new one need to be minted? If you can source and set
it directly, please do, then trigger a real test failure (or wait for a real one) to
confirmly the round trip actually posts to `#automation-errors`. If you can't reach that
credential from here, say so and I'll flag it for Ramon to source directly -- not
something to guess at or fabricate.

## 3. Status, not urgent

Both PRs are open, not yet pm-reviewed a second time (round 1 flagged real, fair gaps --
addressing those now with the evidence above). Will report back once both PRs are solid
and the tickets are ready to go In Review.
