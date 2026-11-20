# REQUEST 1 of 3 (not a GO): OPEN-685, the next scrapers image with openstates-scrapers #140 (same-day vote order for NE, LA, NM)

Written 2026-11-20 (Mac side, State Specific Handling). **Not a GO.** Ramon builds the image. **Ramon gave the scorecard gate's go for OPEN-685 on 2026-11-20; the PM merged all three PRs.**

The OPEN-685 order:
1. **this image;**
2. **request 2:** the stored-vote backfill, `request-open685-2-backfill-ne-la-nm-20261120.md`;
3. **request 3:** the broker release with #785, `request-deploy-broker-6b5eda91-open685-same-day-order-20261120.md` on ddp-broker-py `notes/ops-handoff`.

## What the image carries beyond v72 (the live `ddp-scrapers:75` and `ddp-scrapers-db:2`)
**openstates-scrapers fork `bcaf1447`** (v72 had `8e0ab3dc3`). Four merges:
- **#140 (OPEN-685):** Nebraska, Louisiana and New Mexico votes carry their roll-call number under the extras key the broker reads:
  - Nebraska: its KeyID, key `legislature-rollcall-num`;
  - Louisiana: the `(#N)` ending the link text;
  - New Mexico: the `RCS#` on the PDF.
- **#137 (OPEN-675), #138 (OPEN-677), #139 (OPEN-680):** Wyoming's vote chamber, Wyoming's motion rules and Idaho voter names, from other sessions. Already merged; they ride here. Not states this session follows.

**ddp-open-states `a6be426`** (v72 had `8977ced`):
- #432, #435: backfill scripts (request 2 runs #435's);
- #433: New Mexico's two flags in `jurisdictions.yaml`, `replica_routing` and `legbot_replica`. Those flags are read by the hosts (the broker's and ddp-sync's settings), not by the scraper, so the image changes nothing for them. Their rollout is New Mexico's own request `9f2984cb` (broker notes).

**Core unchanged:** `10f32ce0`, the fork's main.

**`v73` is not used.** Build a new tag (for example `v74`) from main.

## Ramon's step
- `deploy-scrapers-image.sh` from an updated checkout. Main's script registers both families: it copies `ddp-scrapers-db`'s own current revision forward, keeping its roles and no secret.
- Register only when no scrape task is running (ECS check).
- **Check (Mac side, after):** the new revisions name the new image, and the build reports scrapers `bcaf1447` and ddp-open-states `a6be426` or later, with core `10f32ce0`.

## The prod agent's check (read only, after each state's first run on the new image)
For Nebraska, Louisiana and New Mexico, the votes the run stored carry the key:
```sql
select substring(ls.jurisdiction_id from 'state:([a-z]{2})') st, count(*) total,
       count(*) filter (where ve.extras ?| array['house-rollcall-num','senate-rollcall-num','legislature-rollcall-num']) numbered
  from opencivicdata_voteevent ve join opencivicdata_legislativesession ls on ls.id = ve.legislative_session_id
 where ls.jurisdiction_id ~ 'state:(ne|la|nm)/' and ve.updated_at > '<the run start>' group by 1;
```
Expect `numbered = total` for each state's newly written votes.

## Not authorized
Registering `v73`; any data change (that is request 2); any broker change (request 3).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
