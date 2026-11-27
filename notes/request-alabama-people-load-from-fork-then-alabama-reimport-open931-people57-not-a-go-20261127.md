# REQUEST (not a GO): **Alabama: a people load from the fork (two `other_names`), then an Alabama re-import, so 26 sponsorships link to a person (OPEN-931).** 2026-11-27 (Mac side, Onboard New States)

**Not a GO.** Ramon gives each go in your session naming this note. It follows Alabama's rollout request (`request-golive-alabama-manifest-rollout-dry-run-first-pr513-20261127.md` in this branch) and does **not** block it: Alabama's sponsorship gate already passes (26 of 1,507 unresolved, 1.7%, limit 4.7%).

## What it does
ALISON prints two sponsors as "Elliott (C)" (22 bills) and "Morris (T)" (4 bills); the people files had no matching `other_names`, so those 26 sponsorships have no person. `Digital-Democracy-Project/people` **#57 (merge `9de9cd03`, data only, two lines)** adds them to Senator Chris Elliott's and Representative TaShina Morris's files. I confirmed the two people on the legislature's own member pages (Senate District 32, House District 77).

## What I need from you (after each go, in order)
1. **Part 1: people load for Alabama from the fork at `9de9cd03` or newer** (production reads upstream's people until the hosts switch to the fork, OPEN-341/342: use whatever path the earlier fork people loads used, and tell me which). Gate: nothing in flight for Alabama; report the load's exact output lines (people added/updated: expect only these two people updated; **anything else changed: stop and report**).
2. **Part 2: Alabama re-import on Fargate** (`al` with the sessions the manifest and replica hold; **tell me if the session list differs**). One run at a time; not while Alabama's rollout or its first embedding pass is running.
3. Tell me after each part. I check on the Mac replica: `quality_check.py --structural al` reads **0 of 1,507** sponsorships unresolved, **22 rows to Elliott and 4 to Morris**, no other Alabama person's sponsor count moves.

## Not authorized
Any other state; a manifest change; `legbot_replica`; a ddp-sync restart; a people load for any other state; a scrape beyond the Alabama re-import.

Tickets: OPEN-931; Alabama go-live OPEN-523; OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
