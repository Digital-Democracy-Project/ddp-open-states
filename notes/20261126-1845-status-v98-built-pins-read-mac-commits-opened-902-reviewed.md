# Status 11-26 18:45 UTC: v98 is built (Ramon's script output); what I read from it, and the Mac's commits

## v98, from Ramon's build output (relayed; this role cannot read task definitions)
* Tag **v98**, task-definition revisions **`ddp-scrapers:100` and `ddp-scrapers-db:27`** (the db revision carries the stored database login: the script printed "RDS secret in ddp-scrapers-db: yes", "in ddp-scrapers: no"). Core recorded in the image: **`647bb3994ed819ba4194820b379147f525219479`: the same as v97**, so api-v3 on both hosts and this host's ddp-sync are already on it. I ran the core-pin drift check against that core on this host: **OK, exit 0**. No api-v3 rebuild is needed for v98.
* **Scrapers commit: the image does not print one.** Scrapers `main` is `aed388240e022b65abe45ec31fe00d96f22387ae` (the #299 merge, 13:30 EST = 18:30 UTC) and nothing was merged after it; the image was built at about 18:33 to 18:36 UTC from a fresh clone of `main`. So I take **`DDP_SCRAPERS_SHA=aed388240e022b65abe45ec31fe00d96f22387ae`** for ddp-sync's own copy. That is an inference from timing and `main`'s history, not a recorded value; tell me if the build's clone line says otherwise.
* v98 holds #298 (Mississippi) and #299 (OPEN-902, Louisiana). I reviewed #299 on OPEN-902 (comment 23729): 4,509 passed vs 4,506 on clean main, the new tests fail without the fix; Ramon merged it.
* The Louisiana nightly at 12:00 UTC (11-27) will launch revision 100 (ECS takes the latest active revision), so it should get the fix. Not retried by me in the meantime.

## What I will do, and when
* **ddp-sync rebuild at the new scrapers commit, then a guarded restart:** only between runs. Iowa `2026s1` (since 16:27 UTC) still holds its lock; I will not restart while it does. After it finishes I will rebuild, restart under the narrow rule, then start the v96 Iowa re-import.
* Note that Iowa's own database load will run on revision 27 (v98) if it starts after 18:3x; same core, so no drift.

## The Mac's commits (Ramon told me): for your records
* Mac ddp-sync **`39195e4`** (the merge of #319, SYNC-197; includes #315 to #318). Mac ddp-agents **`7b100ed22`** (the merge of #494, AGENTS-267 prompt v3 revert; includes #488 and #489). Mac manifest and api-v3 (v97 core) checkpoint is `31e935af`. Nothing else switched on: this host's ddp-sync has no `include_policy_statement`, `LEGBOT_POLICY_MATCHING_MODE` is absent.
