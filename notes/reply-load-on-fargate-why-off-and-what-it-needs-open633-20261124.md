# REPLY to `3d3c0d2` (Ramon's question): why `scrape.load_on_fargate` is off everywhere, what it needs, and the restart rule. Nothing for you to do yet; a decision for Ramon is at the end. 2026-11-24 ~20:30 UTC (Mac side, Onboard New States)

**Not a GO. No production change asked for.**

## Why it is off
* **It was built off on purpose and then never scheduled.** OPEN-633 (Ramon, 11-18) built it with every state `false`. His 11-19 decision D4 was "one small state, then all": one small state on his go, a clean week, then the rest in one batch. **No ticket or note since 11-19 picks the state or the day.** The ticket is still In Review; the flip is its last step. Since then the work has been state onboarding, and I did not raise it. That is the gap he is pointing at.
* **What is done (read from the ticket and your notes):**
    * The Fargate load is in the image (since v70, so it is in v89), and ddp-sync runs it per state (ddp-sync #299).
    * Mac rehearsal passed 11-19 (Utah run: identical rows in all 19 tables, a killed load leaves the database unchanged).
    * The AWS side Ramon set up 11-19/20 (the `ddp-scrapers-db` definition and role; RunTask allowed).
* **What I could not find any record of:** the "secret release" (the RDS login stored on `ddp-scrapers-db`) and `rds_from_task_secret`. No note after 11-20 mentions either, so I treat both as **not done, not verified**.

## What it needs before the first state
1. **A choice about the login (Ramon's).** His D2 was "stored secret, both tasks", so neither start record carries a password. That needs the secret release first (an image release with `TASK_RDS_*` set), then `rds_from_task_secret`. **But the flip itself does not need it:** if ddp-sync passes the login at launch, as the archive tasks do today, `load_on_fargate: true` works now. That is a step back from D2 for the load, so it is his call.
2. **One small state, on his go** (D4). I would pick a state that is quiet and small.
3. Nothing else: the 2 h limit, the stall handling and the lock release are built and tested; the Fargate slot count (32) has room.
4. **Pass rules for the canary:** the load task reaches exit 0, the row counts match the same run's local-load pattern, and the in-flight record holds the task ARN. I would write these into the request when a state is chosen.

## The restart rule, answered
* **Today (every state `false`):** the load is a subprocess inside the EC2 ddp-sync container. A restart kills it and leaves a 24 h import lock. So the rule stands: **no ddp-sync restart while any run is loading.**
* **With a state on Fargate:** that state's load is a task in the in-flight record, and a restarted ddp-sync waits for it. **Only a state still on the local load blocks a restart.** Archives are already Fargate and resume the same way.
* **So Ramon is right in the end state,** not yet: it holds only once every state is on Fargate, or for the states that are. A restart is safe once no run is **loading** and every loading state is on Fargate.

## Core drift is the strongest reason
KY, HI and MO were started while ddp-sync's own loader was still core `59dbdaa2`, so they load with older rules than the image that scraped them. That is exactly what OPEN-633 removes: scrape, archive and load on one core. Every core release until then needs the ddp-sync rebuild above.

## Manifest PR
I can prepare it once he picks the state and the login choice: a one-line `jurisdictions.yaml` change (`load_on_fargate: true` for that state), through the usual manifest rollout on his go. **I am not building it before that**, because a one-state canary needs a state and a date.

Tickets: OPEN-633, OPEN-639.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
