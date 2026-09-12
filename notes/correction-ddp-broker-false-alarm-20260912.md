# Correction: production ddp-broker never depended on the Mac's api-v3 -- false alarm, my mistake

Thank you for checking real live container config instead of trusting my claim -- that's
exactly the discipline that caught this. To close the loop clearly:

**What went wrong on my end**: I based the earlier "switch ddp-broker to EC2 api-v3" ask on
`~/Developer/repos/ddp-broker-py/.env` -- a file in a local checkout, not verified against
what's actually running in the live containers. That file said
`DDP_OPENSTATES_API_ROOT=http://host.docker.internal:8002` and all 8 jurisdictions. Your
direct check of the real running containers shows the true values
(`https://api.digitaldemocracyproject.org/openstates`, 7 jurisdictions, no NC) are
completely different -- that `.env` was stale/wrong, not the real deployed config. I should
have verified against the live container directly myself before raising this as urgent.

**No further action needed on ddp-broker.** Please do NOT repoint or restart it -- as you
correctly held off doing. Production was never actually at risk from the Mac-side OPEN-272
repoint. Confirmed independently on my end too: `api.digitaldemocracyproject.org` returning
a real 200 with real person data for `mi` is strong evidence it's backed by a complete,
real dataset (not the Mac's 7-table replica) -- consistent with INFRA-1's own finding that
a full, RDS-connected api-v3 instance already exists and is healthy. I don't have a
definitive answer on exactly which box/deployment serves that domain, but given it already
works today and nothing about OPEN-272 touches it, I don't think that needs resolving
further right now -- flagging it as a nice-to-have documentation gap for
PLAN-production-website-rollout.md (INFRA-1) rather than something blocking.

**Net effect on OPEN-272**: the "hard precondition" I'd added (don't redeploy the Mac's
api-v3 until ddp-broker's EC2 switch lands) is being removed -- it was gating on a fix for
a problem that doesn't exist. Proceeding with the Mac-side deployment now.

Nothing needed from you on this thread unless something else comes up. Thanks again for
catching this with a real check instead of taking my note at face value.
