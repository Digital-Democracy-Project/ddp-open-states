# GO: roll out the state list with North Carolina `newest_first: false` (#380 merged), step A.3 of `a774838`. 2026-11-16 (Mac side)

**Ramon, 2026-11-16: "i merged 380".** Your `35fa65f` reports the NC flip committed (`reversed=2343`; the second dry run at 0). The Mac replica agrees: 2,327 NC bills oldest first, 0 newest first, and HB 116's latest action is "Ch. SL 2026-56".

## What I need from you
1. **Gates:** 0 running scraper tasks, and no ddp-sync line in the last 10 minutes.
2. `git -C /opt/ddp-open-states merge --ff-only origin/main`. Expect it to include **#380** (merge `e38af9c3`), plus whatever else is on main.
3. `rollout-manifest.sh --host ec2 --ddp-sync-root /opt/ddp-sync`. Expect exit 0 and drift OK.
4. **Gate:** `/ddp/enrollment` 200, 13 states, `newest_first` true for **us only**, and the md5 equal in the checkout, api-v3's copy and the container.
5. A short reply with the values.

The production broker keeps the state list for up to an hour, so it reads nc false within an hour of the rollout. There is no scheduled bill-event task, so nothing to re-bootstrap.

## Not authorized
Any scrape (NC is still held until 11-22 02:00 UTC as scheduled); ddp-sync; the broker.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
