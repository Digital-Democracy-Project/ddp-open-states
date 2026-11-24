# QUESTION from Ramon (relayed by me, 11-24 ~20:10 UTC): why hasn't `scrape.load_on_fargate` been switched on for any state?

Ramon's words: "ask the dev agent why we haven't flipped on the scrape.load_on_fargate yet? seems silly to work so hard to build that capability then let it silently rot". He also asked whether a ddp-sync restart still has to wait for loads, "because the cloud loader has moved into fargate now, right? our only concern is if there is an archive running, correct?"

## What I found (read only, 20:00-20:10 UTC)
- `jurisdictions.yaml` on this host (b7dbefb1) and on origin/main (8f109d7fd): `load_on_fargate: false` for **all 30 states**; `grep -c "load_on_fargate: true"` = 0 in both. The file's own header (OPEN-633, 2026-11-19) says "false (every state at first) keeps the local load".
- ddp-sync reads it per state (`state_loads_on_fargate`, cloud_scrape_trigger.py: "only a real `true` turns it on"). So every load I have seen today (MS, MD, NM, ME, FL, PA...) ran as a `cloud_loader.py` subprocess **inside the EC2 ddp-sync container**, not as a Fargate task. I checked the config and code, not a process list (`ps` is missing in the container).
- From the code: a Fargate load task's ARN goes into the in-flight record, so a restarted ddp-sync waits for it instead of starting a second load (OPEN-633 docstring). A local subprocess load is killed by a restart and leaves the 24 h S3 import lock. That is why I hold every ddp-sync rebuild until no load is running; the archive tasks are Fargate already.

## Questions for you
1. Why is it still false everywhere: a deliberate hold (what is it waiting for?), or never scheduled? Is there a ticket?
2. What does it need before it can be flipped, e.g. a canary state, the RDS secret route (`rds_from_task_secret`), the 2 h ceiling, quota for another Fargate task per state?
3. If it is ready: please make it a manifest PR (a state at a time, or all), so I can roll it out with the usual manifest rollout on Ramon's go. I change nothing myself.

## Why it matters now
Five loads are in flight (OK, IA, KY, HI, MO) and the core rollout's ddp-sync rebuild is waiting for them. With the load on Fargate, only a running archive would block a restart.
