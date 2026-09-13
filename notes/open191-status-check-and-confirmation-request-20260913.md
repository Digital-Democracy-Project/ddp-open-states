# OPEN-191: status recap + confirmation request

Jira comment 15180 (2026-09-13 01:21, Ramon confirming directly) already resolved this
ticket's first acceptance criterion: the production broker is confirmed cut over to
RDS/the new api-v3 for real traffic, no on-prem hop. That comment asked you for two
things, and I don't see either one answered yet in the ticket:

1. Technical evidence for the cutover itself -- what changed, when, and how you'd verify
   it independently (config diff, deploy log, a live request trace, whatever's real).
2. Whether OPEN-193/AC6's freshness re-measurement (OPEN-193 closed today, 2026-09-13,
   per your 07f90a6 clean-run note) satisfies OPEN-191's own freshness AC (decided
   threshold: ≤24h primary / ≤7d secondary), or whether that needs its own separate
   check against the now-current RDS state.

Also worth folding in: Tier 1 + Tier 2 quality checks against RDS -- OPEN-191's fifth
validation item, "not yet run" as of the ticket's last update -- are running for real
right now, on the Mac, via the RDS-replica-mirrored local Postgres (confirmed earlier
this session: the Mac's api-v3 container's DATABASE_URL points at
openstates_rds_repl_20260911, not the old on-prem DB). Results so far: FL 96.8%
(1275/1317), UT 99.86% (1465/1467, 0 failures), AZ 98.4% (1325/1347, 4 failures -- 1
live-API rate-limit noise, 3 genuine local-missing-vote gaps worth a look once
everything's in). WA/VA/MI/MA/AL/US/NC still running. Will post full results here once
all 9 finish.

Can you confirm/answer items 1 and 2 above so we can close out the remaining open
threads on OPEN-191?
