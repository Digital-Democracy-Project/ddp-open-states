# REQUEST (waits on Ramon's go): scrapers image v64 with the PA/LA vote-type rules (OPEN-582, 583, and 617 if merged), Nevada's 2027 switch (OPEN-606), and the relabel tool fixes (OPEN-615, core #117); then api-v3 on both hosts at that core. 2026-11-17 (Mac side)

**Not a GO yet.** Ramon builds v64 with `deploy-scrapers-image.sh` from his own Terminal (`CONFIRM=1` asks before registering; it needs a real terminal, see `125dc85`). The prod agent's part starts only after a GO naming the revision.

## What v64 carries (main since v63 = `ddp-scrapers:66`)
**The image is built from each fork's main at build time**, so whatever is merged then goes in.
| Repo | Commit | Change | What anyone would notice |
|---|---|---|---|
| openstates-scrapers | `3cc2a4e7d` (#120, OPEN-582) | PA: a floor vote adopting a resolution ("House Resolution 401") is `passage` | Nothing published: PA is `scraping`, not live |
| openstates-scrapers | `9063af8cf` (#121, OPEN-583) | LA: concurrences, conference reports, Senate bare CONCUR/ADOPT, House FINAL CONSIDERATION are `passage` (Ramon: keep all three extras) | Nothing published: LA is `scraping` |
| openstates-scrapers | `d17ba4346` (#122, OPEN-606) | NV: `2025Special36` stays the only active session until 2027-01-31; from 2027-02-01 only `84` is active (a date check in `nv/__init__.py`) | Nothing until Feb 1. **Must be in an image registered before 2027-02-01** |
| openstates-scrapers | **only if merged before the build:** #123 (OPEN-617, head `7e201c6b4`, In Review) | PA: four exact concurrence wordings are `passage`; the scraper's own `amendment` branch for them is removed | Nothing published: PA is `scraping` |
| openstates-core | `71fd44d61ce7f116a23933e29fbe9ea01372a99c` (#117, OPEN-615) | `os-text-extract relabel` counts every computed field it changes (dry run and commit); docstrings corrected | Nothing by itself; nobody runs relabel yet |
| ddp-open-states | `22b6a00` (#406, OPEN-616) | The api-v3 build imports the app, so an image that can't start fails at build time | Applies at the api-v3 rebuild below |

* **No core database migration** since v63 (checked: `git diff --name-only b5728c43 71fd44d6` shows none; only `cli/text_extract.py`, `ddp_states/__init__.py` and a test).
* **Stored votes are not relabelled.** Ramon, 2026-11-17: PA's and LA's stored votes (PA 318, plus 79 if OPEN-617 ships; LA 845) are relabelled **just before each state goes live**, from a targeted dry-run list he approves, as part of its scorecard gate. Until then, new PA/LA scrapes write the new labels on the bills they touch, so stored labels are mixed. That is expected, and nothing is published for either state. **Do not run `backfill-motion-classification.py` for pa or la:** it has no entry for them and would wipe the scraper's `amendment` labels.

## Rules
* Register only when no scrape is running for pa, la or nv (ECS check). PA's nightly is at 04:00 UTC and runs about 8.5 h: register outside it.
* At most two state pipelines at once. A stop is harmless: report it; no retry past a gate.

## Prod agent, after Ramon registers v64 and posts the GO
1. **Check:** the next launched task reports the new revision and image v64. Read its `DDP_CORE_COMMIT`: it must be `71fd44d61ce7f116a23933e29fbe9ea01372a99c`. If it's a later core, stop and report: a core merge landed after this note.
2. **api-v3 on EC2** (the RUNBOOK's api-v3 release; release order: image first, then api-v3):
   * Bring `/opt/ddp-open-states` to main at or after `22b6a00` (it carries #406's build step).
   * Tag the running image `ddp-openstates-api:pre-v64` for rollback.
   * Build with `docker-compose.rds.yml`, passing `DDP_CORE_SHA=71fd44d61ce7f116a23933e29fbe9ea01372a99c`, then `up -d --no-deps api` only.
   * **Gate:** the build's import step passes; `/healthz` returns 200; `check-core-pin-drift.py --image-core 71fd44d61ce7f116a23933e29fbe9ea01372a99c --container ddp-openstates-api-1` exits 0.
   * **Rollback:** retag `pre-v64` as `:local` and recreate `api` only.
3. **Report** the first PA, LA and NV runs on the new revision: status and failed count. NV should still show `{'2025Special36'}` as its active session.
4. The **Mac api-v3** is rebuilt by the Mac side at the same core. Same gate.

## Not authorized
Any stored-data change (relabel or backfill included), manifest change, broker or ddp-sync change, or extra scrape.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
