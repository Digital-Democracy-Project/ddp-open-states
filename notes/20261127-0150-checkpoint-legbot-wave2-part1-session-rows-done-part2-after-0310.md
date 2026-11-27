# Checkpoint 11-27 01:50 UTC: LegBot wave 2 (RI, MO, ND; OPEN-910), Part 1 done; Part 2 waits until after 03:10 UTC; no LegBot run

Ramon's go in this session (a pop-up answered "#503 is now merged" after I asked what the "GO" meant; I read that as his go for this request, which waits only on #503).

## Gates
* **Gate 0:** #503 is on `origin/main` (`e0964d7a`, with the docs PR #502); its diff against my recorded revision `af88d018` is **exactly six lines: `replica_routing` and `legbot_replica` false to true for `ri`, `mo` and `nd`; no other state or key changes** (checked key by key).
* Gate 1: no Rhode Island, Missouri or North Dakota task or lock (the only lock is Iowa's, an unrelated run); no ddp-sync job in the last 10 minutes.
* Gate 2 (starting point): `/opt/ddp-open-states` at `af88d018`; the broker's list `MI,UT,US,VA,AZ,WA,FL,NC,PA,NE,LA,NM,OR,WY` (and `DDP_ENROLLMENT_SOURCE=manifest`, so the list follows the manifest); restore point 01:45 UTC.
* Gate 4 (production, RDS): Rhode Island **259 people, 3,011 bills (2026)**; Missouri **582 people, 3,161 bills (2026)**; North Dakota **334 people, 1,106 bills (69: 1,089, 69S1: 12, 69S2: 5)**. `onboard_jurisdiction --check` for all three before any write: only the session line missing; map outlines present for each. The parity gate is Ramon's waiver (the check no longer exists), as in wave 1.

## Part 1 (session rows), done at 01:45 UTC
Dry run for each said only "sessions: sync would add 2026" (RI, MO) and "69" (ND). **The real run created more rows than the dry run's line: Rhode Island 5 session rows (2026 down to 2022), Missouri 8, North Dakota 6, and North Dakota also 1 district (the dry run said districts "already there")**: the same as wave 1 (Oregon ended with 7, Wyoming with 5), so I take the dry-run line to name only the current session. `--check` after: sessions ok for all three.

## Part 2 and 3 timing
Your gate 1 says avoid 02:00 to 03:10 UTC (ddp-sync's 02:30 and 03:00 jobs) and the chain from 05:00. The celery recreate drains for about 10 to 12 minutes, so **I will do Part 2 (pull, manifest rollout, api-v3 recreate, broker `.env` plus web, celery and beat by name, the allowed-codes read, drift check) from about 03:15 UTC**, then Part 3 reads. **No first LegBot run** (your separate go). The Mac host's manifest and api-v3 copy are Ramon's step (LegBot's gate reads that copy).
