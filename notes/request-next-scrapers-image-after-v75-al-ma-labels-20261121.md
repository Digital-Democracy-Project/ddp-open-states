# REQUEST (not a GO): the next scrapers image after v75, for Alabama's and Massachusetts' related-bill labels (OPEN-644, OPEN-645). 2026-11-21 (Mac side, State Specific Handling)

**Not a GO.** Ramon builds on the Mac (`deploy-scrapers-image.sh`); registering is the cutover. No release skill exists for scrapers images, so this is written by hand. v75 (`ddp-scrapers:77`, core `7f531958`) stays as is until then.

## What the image adds over v75 (scrapers main now `246b90d1896ca7837ec833feca19225c81ba7a4c`; core unchanged at `7f531958`)
| Merge | What |
|---|---|
| #195 (OPEN-644, `6b6b6027`) | Alabama's existing companion links carry the legislature's word, "Companion Bill". Which bills are linked does not change. Alabama has 0 polled bills |
| #197 (OPEN-645, `246b90d1`) | Massachusetts reads each bill's **"Similar Bills"** tab on every run (Ramon: "Read it on every run"). Each listed bill becomes a `related` link labelled "Similar Bills"; never a companion, so no scorecard effect. A bill whose tab fails is read again on the next run |
| #196 (OPEN-744) | Iowa special sessions (onboarding; Iowa is not scheduled) |

**If the heads have moved when Ramon builds,** the build log shows the commits; anything newer needs its own look.

## Watch after registering
* **The first full Massachusetts run** (the 28-day full walk, OPEN-609) is expected about **5 hours longer**: one more page per bill at about 1.45 s, for 11,932 bills. That takes it from 10–16 h to roughly **15–21 h** of its 24-hour limit (OPEN-476: `max_wait_seconds_by_jurisdiction` ma 86,400).
  * Report its run time.
  * If it nears the limit, stop and tell Ramon. Do not raise the limit without his go.
* **Catch-up runs** grow only by the bills they read.
* **Alabama's next run** writes the label on its 178 existing links.

## Go/no-go after the first full runs (read only, RDS and EC2 api-v3)
* **Massachusetts:** related links by type and label, before and after. Before: only the history-text `related` and docket `replaces` links. After: plus "Similar Bills" links on most bills, and **0 companion** links.
* **Alabama:** 178 companion links, all labelled "Companion Bill".

## Not authorized
Any re-import (none is needed: 0 polled bills in either state), any recompute, any broker change.

Tickets: OPEN-644, OPEN-645 (epic OPEN-536, plan PLAN-companion-lineage §5.3).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
