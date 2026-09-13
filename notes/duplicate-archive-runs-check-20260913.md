# Please check: how many duplicate archive runs since OPENSTATES_ARCHIVE_ENABLED went true on EC2?

Ramon just turned `OPENSTATES_ARCHIVE_ENABLED` off on the Mac (it had been `true` there the
whole time, alongside your EC2 host also having it `true` since the OPEN-192 cutover). Neither
`sync_schedule.yaml`'s `openstates_archive` block nor anything else I can find has a per-
jurisdiction host-ownership split for archiving the way `openstates_scrape.cloud_path` does for
scraping -- both hosts appear to have been reading the same `jurisdictions`/`schedule` list this
whole time, with nothing I can see stopping both from launching the same day's Fargate archive
task independently.

**What I checked from the Mac, and where my visibility runs out:**

- The Mac's own `ddp-sync` Redis flow-status (`ddp:flow:openstates_archive`, 7-day TTL) has no
  entry at all -- odd, since today (Sunday) is `us`'s scheduled day at 05:00 UTC, and if the
  Mac's own scheduler had been running through that window it should have recorded an attempt.
  Can't tell from here whether that means the Mac's scheduler genuinely never fired archiving, or
  just wasn't up continuously through the last several 05:00 UTC windows.
- I have no ECS or CloudWatch access from this Mac's `ddp-scraper` credential (`ecs:ListTasks`
  and `logs:DescribeLogGroups` both `AccessDeniedException` -- same visibility gap OPEN-285
  already flagged), so I can't pull real Fargate task history myself.

**Could you check, from your side:**

1. ECS task history for the `ddp-scrapers` cluster/task-definition family over roughly the last
   3-4 days (since whenever the EC2 host's `OPENSTATES_ARCHIVE_ENABLED` actually flipped true) --
   specifically, any day where the SAME jurisdiction got two `cloud_archiver.py` task launches
   close together (the schedule is one shot at 05:00 UTC per jurisdiction's assigned day: fl/ut
   Monday, az Tuesday, wa/va Wednesday, mi/nc Thursday, ma Friday, al Saturday, us Sunday).
2. If duplicates did happen: whether they actually did double real work against a jurisdiction's
   legislature site (re-fetching documents already archived), or whether `archive_bill_versions()`'s
   own natural-key skip check made the second run a fast no-op against already-archived rows --
   this matters most for MI specifically, given its WAF sensitivity.

Not urgent-urgent (archiving is now off on the Mac, so no further duplication risk going
forward), but Ramon wants to know the actual exposure from the last few days before deciding
anything else.
