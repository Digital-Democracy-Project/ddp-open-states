# OPEN-180: status check on the 4 tickets, from real EC2/production evidence

Checked each directly rather than trusting the ticket text or Ramon's own read. Mixed results --
two look genuinely close/done, one has a real remaining gap worth knowing about before closing,
one I can't confirm from this vantage point at all.

## OPEN-191 (Phase 2: move DB + api-v3 to AWS) -- real gap found, not ready to close

**ddp-broker-py is confirmed fully cut over**, both tiers: `DDP_OPENSTATES_API_ROOT=
http://10.0.0.11:8002` live in both `web` and `celery` containers right now, and real production
traffic has been flowing through it for days (this session's own earlier verification, plus
tonight's real reads for the OPEN-293 backfill check and the MI run).

**But the public domain itself doesn't resolve to either the Mac or this host** --
`api.digitaldemocracyproject.org` -> `52.204.100.187`, which I confirmed via
`ec2:DescribeInstances` is a **third** EC2 instance in this account: `i-09381338adcbb35e2`,
tagged "DDP API, VoteBot and Wireguard VPN". I have no access to that host from here, so I can't
confirm what its own api-v3/proxy config actually points at -- whether it's already AWS-native
end to end, or still forwarding through to the Mac the way earlier notes this session described.
**This is also the same host Ramon referred to as "the other EC2" for VoteBot** in an earlier
thread tonight (repointing `ddp-api`'s `OPENSTATES_PROXY_KEY`/`LOCAL_OPENSTATES_API_KEY` at this
EC2's api-v3) -- that thread stalled on a security-group gap (port 8002 has zero inbound rules,
and I don't have `ec2:AuthorizeSecurityGroupIngress` to fix it myself, confirmed by direct
dry-run). If that repoint never completed, `ddp-api`/VoteBot may still be reading OpenStates data
through whatever path it used before, unrelated to the ddp-broker-py migration being fully done.

**Not ready to mark Done** -- please check `ddp-api`'s own config on that third host directly
(I can't), and confirm whether the security-group change ever landed.

## OPEN-265 (LegBot Mac bill-text read path for RDS-only jurisdictions) -- can't confirm from here

Found the ticket's own history in `ddp-infra/PLAN-legbot.md`'s commit log ("repoint held on a
ddp-broker dependency", 09-13) but no live text in the current doc to check against, and no code
change in `ddp-sync`'s own git history referencing OPEN-265 by number. The dependency it names
(ddp-broker's own repoint) is confirmed cleared as of OPEN-191 above. Whether LegBot's own
Mac-side bill-text reads have since been switched over (or now rely on OPEN-280's replication
making the Mac's *local* api-v3 already RDS-current, which may satisfy this ticket's intent
without a literal repoint) isn't something I can verify from EC2 -- this needs checking against
the Mac's own `ddp-sync` source/config directly.

## OPEN-290 (consolidate the two LegBot trigger endpoints) -- confirmed done

Re-checked: `grep`ing this host's live `ddp-sync` source for `scraper-session-legbot` finds only
comments referencing the old, removed endpoint -- no route registration anywhere. The archive
hook confirmed pointed at the consolidated `/trigger/bill-artifact-generation` (same thing this
session verified end-to-end during FL 2026E testing and again tonight during the real `us`/`wa`
archive runs). **Looks genuinely closeable.**

## OPEN-292 (LegBot lock lease renewal, PR #158) -- EC2 confirmed, Mac unconfirmed

EC2 side: deployed, confirmed live (this session's own work). Mac side: I checked the Mac's
`/health` endpoint just now -- it reports a static `"version": "0.1.0"` that doesn't distinguish
which commit is actually running, so I can't tell from here whether the Mac's LaunchDaemon
restart (deliberately held until the MI full-session run finished, per
`mi-full-session-run-complete-20260916.md`) has actually happened yet. **Please confirm the
restart landed on your side before treating this as validated** -- if it hasn't restarted yet,
the real-world evidence Ramon's note points to (a 31.4h run completing without a lock issue)
was under the OLD flat-4h-TTL code, which doesn't actually prove the NEW lease-renewal fix works
-- it just means the old TTL's gap didn't happen to get hit that specific run.

## Separate finding, not part of the 4 tickets, flagging since it's real: `apply-local-patches.sh` is broken on EC2

Ramon asked how patch-refresh works now that scraping runs on Fargate. Checked the actual
script (`/opt/ddp-open-states/apply-local-patches.sh`, runs nightly at 01:00 UTC via `ddp-sync`'s
own `openstates_patch_refresh` job): its `REPOS` array is hardcoded to
`/Users/agentsmith/Developer/repos/ddp-open-states/{openstates-core,openstates-scrapers}` -- the
**Mac's own local paths**, which don't exist on this EC2 host at all (confirmed). Every run here
should fail at the first `cd`. Checked Redis for this job's own flow-status record
(`get_flow_status("openstates_patch_refresh")`) and found nothing ever written -- either it's
been silently failing with the failure-alert path also not firing (AC3's already-known broken
alerting, [[open193_cloud_scrape_deploy_status]] if that's still accurate), or it simply hasn't
had a real chance to fire yet on this host's uptime.

**Bigger point, worth deciding regardless of the path bug**: every jurisdiction actually scraped
today runs through `cloud_path` (Fargate, frozen images built fresh from GitHub at build time) --
this host's own local `openstates-core`/`openstates-scrapers` checkouts have no connection to
what those containers run at all. Alabama is the one jurisdiction not scraped via `ddp-sync`.
So even fixing the hardcoded path likely wouldn't restore any real effect -- this job may be
entirely vestigial now, not just misconfigured. Worth a decision: fix the path (if something
still depends on this host's local checkout), or retire the job outright.

Not fixing any of this myself -- all four ticket questions and the patch-refresh finding need
either your own visibility (the third EC2 host, the Mac's actual running commit) or a real
decision (retire vs. fix a job), not something to guess at from here.
