# REQUEST (not a GO): **release v96: a new scrapers image, an api-v3 rebuild at the new core, then the Iowa re-import and checks.** 2026-11-25 ~23:50 UTC (Mac side, Onboard New States)

**Not a GO.** Ramon gives the go in your session naming this note. Parts run in order; each part's gate must pass before the next.

## What v96 contains (all merged; commits on `main`)
| Change | Repo and merge | What it does |
|---|---|---|
| OPEN-893 | openstates-core #175 (`4af91c90`, **this is core `main` now**) | Iowa's "Prefiled", "Reprinted" and "Reprinted Marked Up" versions get a stage (Stage 3 gate was 6.3% unstaged against a 5.5% limit; replay says 0.0%) |
| OPEN-894 | openstates-scrapers #295 | Iowa actions stored oldest first by date (310 of 4,206 bills step backwards today; replay says 0) |
| OPEN-892 | openstates-scrapers #296 | Oklahoma logs the address its requests leave from and how long it tried before a connection error. **Logging only.** |
| OPEN-884 | openstates-scrapers #293 | Oklahoma: skip a roll-call block that names the other chamber (SB 920) |
| OPEN-891 | openstates-scrapers #294 | Montana people: member name from the roster link |
Scrapers `main` at the time of writing: **`248c2571c8cbbf4a6dbe275b19cb68f84a390640`**. The image takes core's `main` at build, so please **read the commit the build records** (`DDP_CORE_COMMIT`) and report both commits; stop if core is not `4af91c90` or newer.

## What I need from you
1. **Part 1: the image.** You cannot launch the build (ECS denied); **Ramon builds it on the Mac** with `deploy-scrapers-image.sh` (his command). When it is done, **read the new task-definition revision and the recorded commits and tell me**: scrapers commit, core commit, and that the revision carries the stored database login as v93 did (names and lengths only, no values). Rollback = the previous revision (v95, `ddp-scrapers:97`).
2. **Part 2: api-v3 at the new core on both hosts** (the Mac one is Ramon's; the EC2 one is yours), because api-v3 imports `note_stage`. Gate: health after, version-order output unchanged for a state other than Iowa (report one sample bill).
3. **Part 3: Iowa re-import** once Part 1 is live and nothing is in flight: `ia?full=true&sessions=2025,2026,2026s1` (**check the list against the sessions the manifest and replica hold and tell me if it differs**). It replaces the stored actions with date-sorted ones and re-stages the 418 versions. One run at a time; Georgia's runs go first if still going.
4. **Part 4: the recompute, dry run first.** Iowa `recompute-diff-order ia --dry-run` with the new core, **report the exact lines, do not commit**; I read them on the replica too. Commit **holds until a go note**.
5. **Part 5:** the broker's `refresh_bill_version_order --jurisdiction IA` (Broker Upgrades' command; on their go), then I re-run Stage 3.

## What I check on the Mac side afterwards
Iowa: bills stepping backwards in date **0 of 4,206** and action counts unchanged; versions with no stage **0** (`quality_check.py --structural ia`); attribution still 277 of 111,094 "Open" placeholders only. Oklahoma log shows the two new line kinds on its next run (not before). Nothing else changes: **no other state's stage or order should move** (I replayed 81,604 note pairs: only 6 Iowa pairs change).

## Not authorized
The Oklahoma retry (a separate request after this one, on Ramon's go); any other state's re-import or scrape; a manifest change; `replica_routing`/`legbot_replica`; a ddp-sync restart; the recompute commit.

Tickets: OPEN-893, OPEN-894, OPEN-892, OPEN-884, OPEN-891, OPEN-673 (Iowa go-live), OPEN-887 (Oklahoma), OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
