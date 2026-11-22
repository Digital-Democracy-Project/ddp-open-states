# UPDATE to `9e2caaa` (the next scrapers image after v78): it now also carries a **core change**, OPEN-767 (openstates-core #138, `3ac06b6a`), plus OPEN-769 (Idaho/Wyoming vote keys) and BROKER-579 (PA/NE/LA veto overrides). Scrapers main is `f2ccc75a`, core main is `3ac06b6a`. 2026-11-22 (Mac side, State Specific Handling)

**Not a GO.** Everything in `9e2caaa` stands. The PM asked for the core release to ride this image.

## The core change
* **OPEN-767**, openstates-core #138, merged `3ac06b6a865adfd0fe230fc3bd81d589d18baafb`.
  * When a roll call's voter name matches several people, the voter is now chosen by the vote's own date.
  * Regression run by Onboard New States over 2.43M stored votes: 0 lost and 0 switched in every state.
  * Docs: ddp-open-states #464 (`b255d694`).
* It is the **only core change since `7f531958`**, and it has **no migration** (checked: `git diff 7f531958 3ac06b6a -- '*migrations*'` is empty).
* **Core pin:** there is no separate pin. The image takes core `main` at build, so it builds at `3ac06b6a`. Confirm afterwards with the image's `/opt/openstates-core/DDP_CORE_COMMIT`.

## Release order (each step's own procedure; stop if a check fails)
1. **Build the scrapers image** at scrapers `main` `f2ccc75a` or later; core `3ac06b6a`. The Mac side then checks it, as for v77 and v78.
2. **Both api-v3 copies** rebuilt at the image's core: Mac via `refresh-api-v3.sh`; EC2 with `DDP_CORE_SHA=3ac06b6a…` (RUNBOOK).
3. **EC2 ddp-sync** rebuilt with `DDP_CORE_SHA=3ac06b6a…`, since cloud scrapes are loaded with ddp-sync's own core (SYNC-180).
   * Until this step, new loads still match voters the old way.
   * Then `check-core-pin-drift.py --image-core 3ac06b6a… --sync-container …` must exit 0.

## Scrapers added since `9e2caaa` (main now `f2ccc75a77986c0894152702987681212a02f6c2`)
| Merge | What |
|---|---|
| #222 (BROKER-579, `6a6f0b8c`; this session) | Pennsylvania, Nebraska and Louisiana veto-override roll calls count as passage. Each replaces the chamber's earlier passage vote (Ramon: "Override replaces it"). Nebraska's six stored overrides (2025 LB 319, LB 287; 2026 LB 1256, LB 878, LB 839, LB 929) change only after an NE session-109 re-import |
| #223 (OPEN-769, `f2ccc75a`; Onboard New States) | Idaho and Wyoming votes keyed on the source's own roll-call identity (the ND failure's fix). Frees Idaho, with OPEN-770 still to come |

* **OPEN-771 (Rhode Island's repeated bill)** is urgent for RI's run on Sun 11-29 02:00 UTC and still being built. If it merges before the build, include it. Otherwise it needs one more image registered before that run.

## Data steps after the image, each on Ramon's go (requests come separately)
* **One NE session-109 re-import** covers OPEN-761 ("*" names) and BROKER-579 (overrides).
* **NE and LA people loads** (people #40–#43, merged), then re-linking the stored NE "Meyer" and LA "Henry" votes (OPEN-611 dry run) or a re-import. From Onboard New States.
* **North Carolina:** OPEN-611's Tillett re-link after this image is live (see `9e2caaa`).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
