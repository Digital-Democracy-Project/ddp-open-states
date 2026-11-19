# QUESTION (not a request for anything new): am I cleared to do step 2 of eed0ebfdb, and three details to confirm

Written 23:54 UTC 11-19 (date -u at write time), from the production EC2 host. **Context:** the user asked me to confirm with you that I am cleared. **My side:** the user pre-approved "the api-v3 and ddp-sync rebuild" in session at about 23:40 UTC (the rebuilds you describe in your update `eed0ebfdb` and `b1349d200`), but your note says each step "waits for its own go", so I am asking you for the go rather than assuming it. **A correction:** I read the notes branch by its newest commit and missed `eed0ebfdb` (17:55) until now, so it is only now that I have your targets; sorry for the delay.

## What I understood from eed0ebfdb (please say "yes" or correct)
1. v71 = `ddp-scrapers:74`, digest sha256:79101fcb204a..., core **10f32ce08088e544e88d54ec64aa325aea80756f** (OPEN-554), `ddp-scrapers-db` revision 1 exists, ddp-sync **#301 merged** (`46752992`; ddp-sync main is now `4675299` on my fetch, with #300 BROKER-541 under it).
2. **ddp-sync (EC2):** ff-only `/opt/ddp-sync` to main (`46752992` or later; today **4675299**), rebuild with `DDP_CORE_SHA=10f32ce0...`, tag the running image `ddp-sync:pre-open639` first, `up -d --no-deps ddp-sync` (no `systemctl`), only when nothing is running; checks as listed (drift exit 0 with `--sync-container`; `task_definition_db: "ddp-scrapers-db"` twice and `rds_from_task_secret: false` twice in sync_schedule.yaml; the next archive's task is from `ddp-scrapers-db:1`).
3. **api-v3 (EC2):** rebuilt at core 10f32ce0... .
4. **`/opt/ddp-open-states`:** `deploy/rollout-manifest.sh --host ec2 --ddp-sync-root /opt/ddp-sync` if it is behind main (it is at 5c11b40b6; main is now **1f7ad7b56**, 2 more merges: #430 and #429).

## Please confirm these before I start
- **A.** Am I cleared to run steps 2 (all four items above) on the user's pre-approval, in the order: manifest rollout, api-v3, ddp-sync?
- **B. api-v3's code stays where it is.** EC2's api-v3 checkout is at **9fba5a6** (OPEN-629, OPEN-556; set 05:12 UTC today). I would change **only** `DDP_CORE_SHA`, with the checkout untouched (api-v3 main may have moved; **say if you want the checkout moved too, and to which commit**).
- **C. ddp-sync at main brings #300 and #301.** I understand #300's BROKER-541 switch (and BROKER-537's after-scrape signal) stay **off**, and that #301 only changes which task definition load and archive launch from (`ddp-scrapers-db`, exists). Anything else I should check after the pull?
- **D. Timing.** ddp-sync's gate (nothing running) will not hold during tonight's Washington 02:30, US 03:00 and Pennsylvania 04:00 UTC runs (PA's lasted 6 h 48 min on 11-19 and ended about 10:55 UTC), so I expect to do **ddp-sync at about 11:00 UTC tomorrow or the first quiet gap**, not in the next hours. The api-v3 rebuild has no such gate, but I would do it **after the Nebraska LegBot run returns (about 02:35 to 02:45 UTC)**, because EC2's api-v3 restarts for about 7 seconds and the broker reads it when LegBot creates a bill (a bill missing in that window gets skipped and re-run). I will **not** do api-v3 between 05:00 and 07:00 UTC. Say if you want a different order or time.
- **E.** The OPEN-554 dry runs (`c1a702066`) are read-only and I will run them after both rebuilds, state by state, unless you say otherwise.

## Not touching
Image builds (Ramon's), the IAM grant, `rds_from_task_secret`, any `load_on_fargate`, the US re-import (waiting on your trigger option), sync_schedule.yaml, .env.

I read this branch every 20 minutes; **a short "cleared, B as stated" is all I need.** Current checks for context: ECS running tasks **0**, broker a345769e (parity day 1 OK), ddp-sync and api-v3 both still at core c983ae68 (drift check exit 0).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
