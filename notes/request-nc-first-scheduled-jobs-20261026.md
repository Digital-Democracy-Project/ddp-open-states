# Please report how NC did in the first scheduled jobs after the flip, and a few NC checks (read-only)

**To:** the prod agent on the EC2-broker host. **From:** the ddp-infra session, for Ramon. **Date:** 2026-10-26. **Read-only: change nothing, restart nothing, trigger nothing, deploy nothing, and do not print any secret.** Read variables by exact name only (never a pattern that can match `*_KEY` or `*_TOKEN`).

## Why
Your weekly-cycle report (`report-weekly-cycle-1025-...`) answered the Sunday NC scrape: clean, with RDS read back unchanged. Your flip report (BROKER-302, 2026-10-23 02:23 UTC) listed what it could not check: the 03:00 UTC USA/people jobs and the 04:00 UTC scorecard chain with NC in the list, BROKER-300 behaviour, and the public-side vote contents. BROKER-302 and OPEN-231 stay In Progress until Ramon has read these. The flip was at 2026-10-23 02:15 UTC, so every daily run from 10-23 03:00 UTC on has NC in the broker's list.

## Please report (times UTC; quote the log lines you rely on)
1. **The 03:00 jobs, 10-23 through 10-26.** For each day: did the USA scrape and the people pull run, did they finish, how long, any error. For the people pull, does it include NC, and is NC's people count in api-v3 still **173** (Mac and production both showed 173 on 2026-10-26 from here).
2. **The 04:00 scorecard chain, 10-23 through 10-26.** For each day: did it run to completion, how long, any error or warning that names NC or a legislator or bill from NC. Say if the chain's logs show NC at all, or only the other states.
3. **Broker errors since the flip.** In the `web`, `celery` and `celery-beat` logs from 2026-10-23 02:15 onward: any error, warning or traceback that names NC, North Carolina, `ocd-jurisdiction/country:us/state:nc` or a NC bill id. Also nginx 5xx counts per day. "None found" is an answer; say what you searched for.
4. **NC smoke checks again** (GET only): `/api/openstates-jurisdictions/` still lists NC; `/api/openstates-bills/?jurisdiction=NC&session=2025` total (was 2,338); `/api/search/?q=school&jurisdiction=NC` (was 165, partial false); a legislator lookup `/api/search/?q=Eddie+Settle` and `?q=Edie+Settel`: does a `representative` named Eddie Settle (id `b4b6f0a7-baca-4062-947a-989cb9f98356`) come back, and at what rank.
5. **The nightly search jobs.** The nightly search coverage report and the search-document rebuild: did they run each night since the flip, and do their output lines mention NC (counts for NC bills, people)? Quote the NC lines.
6. **Parity, one more time.** `check_replica_parity --jurisdiction NC --sessions 2025,2025E1` (it is read-only). Report every line. In particular: what the public count is now for 2025 vote events (771 on 10-23) and 2025E1 vote events (5 on 10-23; ours is 7). Exit code 1 on the waived 2025E1 line is expected; say if anything else differs.
7. **Which broker build is running.** The broker `HEAD` and whether it contains BROKER-300 (the endpoint ddp-sync will call after a scrape). Do not deploy; just say what is there, and whether the SYNC-128 hook is on in ddp-sync (the flag by exact name, value only if it is not a secret).

## Not asked
No re-run of any scrape, no FL work (your 10-26 follow-up covered it), no changes to `.env`, containers or ddp-sync.

## Reply
A new note on this branch (`reply-nc-first-scheduled-jobs-<date>.md`). Do not edit this note. Say plainly what you could not read and why, rather than guessing. Leave BROKER-302 and OPEN-231 In Progress; Ramon closes them after he has read your reply.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
