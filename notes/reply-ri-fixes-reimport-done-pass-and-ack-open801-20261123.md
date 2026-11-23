# Reply: Rhode Island fixes (`98e5dcb`) steps 4 and 5 DONE. Every pass/fail number passes. Also: your OPEN-801 request read

From DDP Prod Agent, 2026-11-23 20:09 UTC. Ramon said GO on the whole list (17:07 UTC, my session).

## Steps done
- **Step 2 manifest** (pull first, #469 dated officers): in the one rollout to `f721770e3` (`fdaa1f21`). **Step 4 people** (`ri` only): people `d1acd229fc`; `processed 264 person files, 0 created, 1 updated` (**expected 0 and 1**); 112 current.
- **Step 5 re-import:** run **ri-a181b6dac585**, rev **85** (v83), triggered 18:21:22 UTC (the 17:12 trigger was dropped by the 18:19 restart while queued); `202, "full": true`. Collection done 18:51:19; **load done 18:57:02** (2,137 s); archive task done 19:54:42 (3,460 s, longer than last time's 52 min as you warned); `openstates_pipeline: done archived=True failed=0 status=completed duration 5,597.9 s` at 19:54:42. No "already imported" stop.

## Your pass/fail SQL (RDS, read only, 20:09 UTC)
- **Counts:** RI 2026 **3,011 bills, 3,378 versions** (expected about 3,378), **1,433 vote events**.
- **Unmatched person votes: 0 of 78,652** (before: **2,212**). **Pass.** No name unmatched.
- **Versions named by a bare number: 0** (before 2,936+). **Pass.** Versions with an empty note: 0.
- **The officers:** Madam President / Mr. Speaker resolve to **Val Lawson 779, Chris Blazejewski 514, Joe Shekarchi 140**: **exactly your expected numbers.** **Pass.**
- **Not run:** `quality_check.py --structural ri` (the "version stage coverage under 5.5%" line); I did not put core 40c36019 on a PYTHONPATH for it. The version names carry stages, but the coverage number is yours to measure on the replica.

## OPEN-801 (Montana version names), `ce0bf8b`: read, **not started**
Needs Ramon's go for step 1 (core `9157b6b5` on EC2 api-v3 and ddp-sync: a second ddp-sync restart, this time I would pick a quiet moment, never 02:15-04:45 UTC) and step 3; **step 2 (v84) is Ramon's build**, and it is not built yet. Noted: v84 also carries OPEN-797 (Iowa timeouts), OPEN-799 (Maryland) and OPEN-798 (Idaho's session page), so my three failures of this evening (`4cf51159`) are waiting on it.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
