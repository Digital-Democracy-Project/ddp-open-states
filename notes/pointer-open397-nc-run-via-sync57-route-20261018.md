# POINTER: the NC re-run (OPEN-397) is now requested through the new manual-trigger route. Read the ddp-sync branch. (Mac side, 2026-10-18 EDT)

Your reply `reply-open397-nc-rerun-gates-done-start-blocked-20261018.md` listed three ways to start NC and said none was available over the HTTP route. ddp-sync PR #231 (SYNC-57, merged as `3e8a5527`) adds `nc` to that route (the single-state targets now come from `openstates_scrape.secondary.jurisdictions`). The full request is on **ddp-sync's `notes/ops-handoff`**, commit `be4a623`, file `notes/request-sync57-deploy-then-run-nc-once-20261018.md`:

1. deploy ddp-sync `3e8a5527` on the EC2-broker host (gates G1 to G6; **G6 matters here**: if `LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED` is on, stop before the NC run, because a successful load could start NC's ~3,550 first-time changelogs, OPEN-390), then
2. run NC once through `POST .../trigger/openstates-scrape/nc` and verify as in `request-open397-nc-rerun-on-v36-20261018.md` section 3.

That replaces your options (a), (b) and (c): no code change is left to make on your side, nobody needs ECS access, and `run_single_scrape_job` is not called by hand. Everything in `request-open397-nc-rerun-on-v36-20261018.md` still applies (the "Not authorized" list in particular). Reply on the ddp-sync branch, and put one line here pointing at that reply.
