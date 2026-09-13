# OPEN-191 (Phase 2): partial real answer, plus a redirect on item 1

## 1. Tier 1 + Tier 2 quality checks against RDS -- please run these on the Mac instead

Ramon's call: now that the Mac has a real RDS replica (OPEN-272/273), run
`quality_check.py --coverage <jurisdiction> <session>` (and a `--tier2-limit 250
--tier2-random` sample) there instead of on this EC2 host -- avoids hogging this box's
resources/API quota for a check that has a more natural home now that a true local RDS
replica exists. Checked here first: no evidence this has ever been run against RDS
specifically (the last systematic sweep on this host,
`notes/tier1-coverage-all-jurisdictions-20260803.md`, predates OPEN-193/the RDS cutover
entirely and was against a local dev DB). Real thresholds per the ticket: Tier 1 identifier
coverage >=95% per jurisdiction/session, Tier 2 >=95% pass on the 250-bill random sample.

## 2. Freshness within the agreed window -- satisfied by today's OPEN-193/AC6 measurement

Checked the actual OPEN-191 blocking language (`PLAN-scraper-execution-migration.md`): it was
reopened specifically because "the freshness item was closed on the strength of a decision,
not a measurement" and required "freshness... re-measured against a real, live feed" once
OPEN-193 shipped. Today's AC6 measurement (`notes/open193-ac6-freshness-measurement-
20260913.md`) is exactly that -- a real measurement against the real live `cloud_path` feed,
same jurisdictions this ticket cares about. 7 of 9 clean, FL's cadence explained (deliberate,
documented demotion), MA's real failure already tracked separately as its own ticket (you said
OPEN-283) rather than a new gap here, NC not yet due. **This satisfies OPEN-191's own
freshness AC** -- no separate check needed, same underlying re-measurement the block called
for.

## 3. The actual cutover -- ddp-broker confirmed done and verified; ddp-next unknown from here

**`ddp-broker` (the production broker)**: confirmed real and verified today, not theoretical --
repointed off the old Mac-proxy path (`https://api.digitaldemocracyproject.org/openstates`)
directly onto this EC2 host's own RDS-backed api-v3 (`http://10.0.0.11:8002`), via
`DDP_OPENSTATES_API_ROOT`/`DDP_OPENSTATES_API_KEY` (BROKER-41 direct mode). Verified with a
real authenticated `/bills` call returning real data through that exact path (see
`notes/ddp-broker-repointed-to-ec2-apiv3-20260912.md`). This is a real production traffic
cutover, not just a capability check.

**`ddp-next`**: no visibility into this from this EC2 host -- no directory, no config
reference, nothing. If it's a Mac-hosted or separately-deployed service, that's yours to check
directly; I don't want to guess at something I can't actually verify.
