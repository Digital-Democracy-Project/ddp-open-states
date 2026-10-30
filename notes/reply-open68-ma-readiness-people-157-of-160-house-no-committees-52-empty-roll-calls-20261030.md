# Reply (read-only) for OPEN-68: is MA ready to be served from our database? Not yet complete: 3 House members short, no committees at all, 52 roll calls with a tally but no voters

Prod agent, Fri 2026-10-30 16:50 UTC. The operator said "Option A, run both" (this and the VoteBot deploy). **Read-only: `SELECT`s in a read-only session; counts only, no personal data; nothing changed.** Database read: the RDS instance behind api-v3 and the broker's replica reads (the same one the NC gate used), through ddp-sync's Secrets Manager credentials. Script and output in `/home/bitnami/ops/ma-readiness-20261030T1641Z/` (`ma_readiness.py`, `output.txt`). Read at 16:41 UTC; exactly one MA jurisdiction row.

## 1. People (current = a membership in an upper or lower MA chamber with no end date or one in the future)
* **Lower (House): 157. Upper (Senate): 40. Total 197.** Public OpenStates is 160 + 40 = 200 (your number, I did not read it): **the Senate matches; the House is 3 short** (vacancies, or three people not loaded; I cannot tell which from the database).
* For context: all-time distinct people with a chamber membership: 336 House, 84 Senate (any dates); 415 people have any membership in an MA organization.

## 2. Sessions and bills
Sessions present: the 194th (2025-2026, 2025-01-01 to 2026-07-31) down to the 184th (2005-2006), **11 rows**. **Bills: 194th = 11,840**; every older session shows **0 bills** (193rd and earlier). I did not read the public OpenStates count (it needs an outside call, see 5). For reference the broker itself holds 11,016 MA bills for the 194th.

## 3. Roll calls
**529 MA vote events in total; 64 have no recorded voters; 52 of those have a tally (a count above zero) but no recorded voters** (your Mac-copy number was 152, so production is different from that copy). **46,448 recorded voter rows.** (Same figure for MA as on 10-27: 529 vote events and 46,448 person votes.)

## 4. Committees
**0 committees and 0 committee memberships** in MA (no organization classified `committee`), **so the committee gap in OPEN-68 is real: there is nothing there at all.**

## 5. Other state-level checks
The NC gate (BROKER-302) compares the replica against the **public OpenStates** API for counts (legislators, bills, votes). **That needs outside calls to openstates.org with the key from the broker's environment (reads only, but outside this host), so I did not run it.** I can run it for MA on the operator's say-so; without it, the figures above are database-only. I ran no other MA check.

## The raw drift lines you asked me to quote (ddp-sync, both runs)
* 10-28 06:20:00 UTC: `jurisdiction_manifest_agrees manifest_mtime=2026-10-28T00:13:35.470006+00:00 mode=shadow`, then `jurisdiction_drift_check: done alerted=True drift=1 env_lists_not_set_on_this_host=['LEGBOT_RDS_REPLICA_JURISDICTION_ALLOWLIST'] status=drift unverifiable=[]`
* 10-29 06:20:00 UTC: `jurisdiction_manifest_agrees manifest_mtime=2026-10-28T00:13:35.470006+00:00 mode=shadow`, then `jurisdiction_drift_check: done alerted=False drift=1 env_lists_not_set_on_this_host=['LEGBOT_RDS_REPLICA_JURISDICTION_ALLOWLIST'] status=drift unverifiable=[]`
* (The log does not name which list drifts; the script run in my 00:00 note found MA in ddp-sync's list as the only disagreement. I did not see the Slack message of either day.)

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
