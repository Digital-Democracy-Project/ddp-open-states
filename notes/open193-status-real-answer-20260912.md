# OPEN-193 status: real answer, checked directly against the live host

## Is `ddp-sync` actually running on EC2 with the load step writing straight to RDS?

**Yes, confirmed real and live, right now, checked directly** (not taking the ticket's or a
doc's word for it):

- Host: this same EC2 box (`ip-172-31-78-173`) -- the one running `ddp-broker`/`api-v3` too.
- Managed by systemd: `ddp-sync.service` -> `docker compose -p ddp-sync -f
  /opt/ddp-sync/infrastructure/docker-compose.prod.yml` (mirrors `ddp-broker.service`'s own
  pattern). Container: `ddp-sync-ddp-sync-1`, image `ddp-sync:prod`.
- `/opt/ddp-sync/config/sync_schedule.yaml`'s `openstates_scrape.cloud_path` block, read
  directly on this host (not a repo checkout that might be stale): `enabled: true`,
  `jurisdictions: ["fl", "wa", "usa", "va", "mi", "ma", "ut", "az", "nc"]`. Per that file's own
  comments, this has been live since 2026-09-02, git-drift-reconciled 2026-09-09, `nc` added
  2026-09-09 (PR #125). Once a jurisdiction is in this list, `_run_scrape()` triggers a real
  Fargate collection and loads straight into RDS (`pipelines/cloud_scrape_trigger.py`) --
  confirmed today by direct observation, not just reading config: this is the exact same
  mechanism/container I've been using all day to run the `us` refresh-extraction backfill
  (`docker logs ddp-sync-ddp-sync-1`, real `aws ecs describe-tasks` calls against the
  `ddp-scrapers` cluster).

**This is NOT work I did this session -- I'm confirming something that predates my
involvement.** It looks like this was built and landed across earlier sessions (the canary
work your own plan doc describes, OPEN-241 through OPEN-248). If OPEN-193's Jira ticket still
shows all 6 ACs unchecked, at least AC1 (load runs next to the database, `ddp-sync` on EC2) is
real and demonstrably done -- the ticket looks stale, not the underlying system.

## Did I do this work and not update Jira, or is it unbuilt on my end?

Neither, precisely -- see above. I didn't build it; I verified it's real and running today.

## AC6: is the data-quality backfill the same thing this AC wants?

**No -- confirmed these are two different things, not the same work under different names.**

- The `mi/ut/fl/va/wa/us` backfill I just finished (`refresh-extraction`/`recompute-diff-order
  --commit`) fixes **stale extracted TEXT** for already-loaded documents -- a poppler-version
  content-quality issue, unrelated to whether new legislative activity is currently flowing
  into RDS.
- AC6, per `PLAN-scraper-execution-migration.md`'s own Phase 4 section, wants **RDS freshness
  re-measured per jurisdiction against a real, live feed** -- i.e., confirming RDS data is
  actually current relative to real-world legislative activity, not a content-quality check.
  The same doc's history is explicit about this: an earlier freshness item was closed "on the
  strength of a decision, not a measurement" (2026-09-01), found per-jurisdiction staleness
  ranging 2 days to 2.5 months at the time, and OPEN-193 shipping for real was specifically
  called out as *what actually fixes the freshness gap* -- implying AC6 needs a fresh
  measurement taken now that the real feed (`cloud_path`, confirmed live above) has been
  running for a while, not a re-statement of the backfill's own clean numbers.

I have not done that measurement. Happy to run it if useful -- I have direct RDS access and
can check e.g. most-recent-bill-action timestamp per jurisdiction, or the cloud-path Fargate
run history (S3 watermarks / Redis flow history), against each jurisdiction's real recent
activity. Let me know if that's the right shape for what AC6 needs, or if there's a specific
methodology already decided that I should use instead of inventing one.

## The other four ACs (cadence/eligibility ownership, path ownership, failure triage to Agent
Smith, on-prem rollback demonstration)

Not verified by me either way this round -- I only checked AC1 and clarified AC6's scope.
Recommend checking OPEN-193's own Jira comment history / linked PRs for these rather than me
guessing; I'll dig into them directly if you want a real answer on any of the four specifically.
