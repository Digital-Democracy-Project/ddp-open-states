# REQUEST (not a GO): the next scrapers image (v82) at scrapers main `4e22ce72` or later carries the Nebraska, Louisiana and New Mexico related-bill links (OPEN-794/795/796). Then the re-imports that load them: **NE 109 and LA 2026 by running `df508b7`'s part B on that image** (not a second re-import), and NM 2026. 2026-11-23 (Mac side, State Specific Handling)

**Not a GO.** Ramon builds the image (`deploy-scrapers-image.sh`). Every re-import is the prod agent's, after a GO note from Ramon. Ramon decided the links on 2026-11-23 ("Store all three", OPEN-653 comment 22780). Each one is `related` (or `replaces`/`replaced-by`) with the legislature's own label, **never `companion`**, so no scorecard changes.

## What is merged (scrapers main, reviewed and merged by the PM session)
| Merge | Ticket | What the scraper now stores | Expected on the Mac replica measure |
|---|---|---|---|
| #243 `05ee6bc9` | OPEN-796 New Mexico | the bill a "Succeeding entries" action (code 7798) names: `related`, label "Succeeding entries" | 2026: 1 link (HB 3 → HB 2); 2025 has 2 more (HB 3 → HB 2, SB 22 → SB 21), but 2025 isn't loaded (below). Measured on the legislature's own `LegInfo25`/`LegInfo26` databases |
| #244 `860751a6` | OPEN-795 Louisiana | each committee substitution: the original `replaced-by` the substitute (label "Becomes"), the substitute `replaces` the original (label "substitute for") | 2026: 88 links on 88 bills, 44 of each type |
| #245 `4e22ce72` | OPEN-794 Nebraska | each "Provisions/portions of LB … amended into LB …" pair on a bill's own history: `related`, label "amended into" (carried bill) or "provisions amended in" (carrying bill) | 109: 583 links on 376 bills (291 "amended into", 292 "provisions amended in") |

* **No core, people or migration change.** The labels need a loader at core `7f531958` or later, which the current loader already is (`939e4a2c`, prod status `0e5f573`). The same gate held for the UT and AZ re-imports.
* **The Nebraska one-way question** (LB 958 lists LB 1033, LB 1033's own page doesn't list LB 958) is with Ramon. If he wants it two-way, that's a later change and a later re-import. It doesn't hold this one.

## Part 1: the image (Ramon)
* **Build v82 at scrapers main `4e22ce72` or later.** It's the same next image the Idaho request needs (`9b4d8b9`: `02ba6f4e` or later; `4e22ce72` contains it), so one build covers both.
* **Mac side** checks the image's scrapers tree contains `4e22ce72`.
* **Prod side:** please report the tag and task-definition revision, called **rev R** below.
* **"Rev R or later" below means an image whose scrapers tree contains all three merges** (`05ee6bc9`, `860751a6`, `4e22ce72`). The Mac side confirms that for rev R. A higher number alone isn't enough.
* For reference: **rev 83 is v81, built at scrapers `d8e1bf5d`** (prod notes `9b4d8b9` and `0e5f573`). That commit contains none of the three merges (checked on scrapers history). So a run on rev 83 does not load these links.

## Part 2: Nebraska 109 and Louisiana 2026, through `df508b7` part B (no new re-import)
`df508b7` (Onboard New States, OPEN-479/480) already asks for one whole-session re-import of **NE `109`** and **LA `2026`**, pre-approved overnight and queued after the WY/UT/AZ loads. It also says "not authorized: a second re-import of the same session".

**So please run that part B on rev R or later, not on rev 83:** its gate G2 (ddp-scrapers:81 or later) becomes **rev R or later**. Everything else in `df508b7` stands. One re-import per state then carries both changes, and the Nebraska one also covers the re-import owed for BROKER-579.
* **If part B already ran before you read this:** report the revision it ran on. If that image's scrapers tree lacks the state's merge (Nebraska `4e22ce72`, Louisiana `860751a6`), as rev 83 does, the state needs one more full re-import on rev R, on Ramon's go, with the same triggers:
```
POST /ddp-sync/v1/trigger/openstates-scrape/ne?full=true&sessions=109
POST /ddp-sync/v1/trigger/openstates-scrape/la?full=true&sessions=2026
```

## Part 3: New Mexico 2026 (prod agent, on a GO note)
New Mexico's weekly runs are incremental, so an unchanged bill wouldn't pick up its link. Its **2026** session needs a full re-import (SYNC-181):
```
POST /ddp-sync/v1/trigger/openstates-scrape/nm?full=true&sessions=2026
```
* **Not 2025:** the Mac replica holds no New Mexico 2025 bill (2026-11-23: 812 bills in 2026, 0 in every other session). A 2025 run would be a first load of a whole session, which is onboarding's decision, not this change's. If 2025 is ever loaded, its 2 links come with it.
**Gates** (stop and report if one fails):
1. New tasks run rev R or later.
2. Nothing New Mexico is running: no `nm` collection, load, archive or text-extract task, and `ddp:pipeline_lock:nm` empty.
3. Not during another state's heavy load (one at a time, as in `df508b7`).

The answer must be **202** with `"full": true` and the session echoed. A 409: wait, don't force.

## Pass/fail (read-only, on RDS, after each state's load)
```sql
SELECT j.name, s.identifier, r.relation_type, r.ddp_relation_label, count(*)
FROM opencivicdata_relatedbill r
JOIN opencivicdata_bill b ON b.id = r.bill_id
JOIN opencivicdata_legislativesession s ON s.id = b.legislative_session_id
JOIN opencivicdata_jurisdiction j ON j.id = s.jurisdiction_id
WHERE j.name IN ('New Mexico', 'Louisiana', 'Nebraska')
  AND (j.name, s.identifier) IN (('New Mexico','2026'), ('Louisiana','2026'), ('Nebraska','109'))
GROUP BY 1, 2, 3, 4 ORDER BY 1, 2, 3, 4;
```
**Pass, exactly** (all three sessions are over, so a full re-import gives exact counts; any difference is a **fail**, reported with the numbers, and the Mac side then re-measures on the replica):

| State | Session | Rows (`relation_type`, label → count) |
|---|---|---|
| New Mexico | 2026 | `related`, "Succeeding entries" → 1 |
| Louisiana | 2026 | `replaced-by`, "Becomes" → 44; `replaces`, "substitute for" → 44 |
| Nebraska | 109 | `related`, "amended into" → 291; `related`, "provisions amended in" → 292 |

* **No `companion` row**, and no other label for any of the three. Before these changes none of them stored a related link: 0 rows on the Mac replica, 2026-11-23. So any other row is a fail too, reported with its rows.

**Through api-v3** (one of each):
* `/bills?jurisdiction=ne&session=109&identifier=LB 958&include=related_bills` lists LB 1033, LB 701, LB 773 and LB 777, each with `"label": "provisions amended in"`;
* `/bills?jurisdiction=la&session=2026&identifier=HB 1257&include=related_bills` lists HB 123 with `"relation_type": "replaces"` and `"label": "substitute for"`;
* `/bills?jurisdiction=nm&session=2026&identifier=HB 3&include=related_bills` lists HB 2 with `"label": "Succeeding entries"`.

## Scorecards
No change: the broker follows only `companion`, and none of these is one.
* The dev broker copy holds no New Mexico bill and no Nebraska or Louisiana polled bill.
* BROKER-554 (#808, not live) is what would show these labels on the broker's bill detail. Until it's live they're in api-v3 only.

## Not asked
No people refresh beyond `df508b7`'s part A, no scorecard step, nothing on the broker.
