# REQUEST (not a GO): Rhode Island's three fixes (OPEN-784 version stages, OPEN-785 presiding officers, OPEN-786 "Appollonio, Jr."). Five steps in order: (1) core `40c36019` on both api-v3 copies and EC2 ddp-sync, (2) manifest rollout (pull first), (3) a new scrapers image, (4) people refresh for `ri`, (5) ONE full re-import of Rhode Island 2026. 2026-11-23 (Mac side, Onboard New States)

**Not a GO.** Each step waits on Ramon's go. Step 3 is Ramon's build (`deploy-scrapers-image.sh`). Steps 1, 2, 4 and 5 are the prod agent's, each after a GO note.

## Why
Rhode Island's rerun (`ri-397bc21f0bff`, rev 81, ddp-sync notes `10ff50d`) loaded 3,011 bills with no repeat. On the Mac replica (OPEN-665) it:
* **fails Stage 3's version-stage gate: 2,936 of 3,011 versions (97.5%) have no stage**. Each bill had one version, named by its number ("7603");
* has **2,212 unmatched votes**: "Madam President" 779, "Appollonio, Jr." 779, "Mr. Speaker" 654.

| Merge | Ticket | What |
|---|---|---|
| openstates-core #140 `40c36019` | OPEN-784 | exact-name ranks so a bill's several substitutes ("As Amended", "Substitute A", "Substitute A As Amended", "Substitute B" …) order as printed. Changes the rank of 0 of the replica's 29,086 other (state, name) pairs |
| scrapers #235 `c1ae4322` | OPEN-784 | reads RI's per-chamber text index and stores each bill's texts up to the current one, named by stage (it had skipped earlier texts on 305 bills) |
| ddp-open-states #469 `ce2d4cc7` | OPEN-785 | RI 2026 presiding officers in the manifest, **dated**:<br>• House: Joe Shekarchi from 2026-01-06; Christopher Blazejewski from 2026-05-07 (House Journal: elected Speaker "for the remainder of the 2026 Session")<br>• Senate: Senate President Val Lawson<br>The validator now accepts the dated form (la and ri only) |
| scrapers #236 `2688a473` | OPEN-785 | one shared officer reader (`scrapers/utils/presiding_officers.py`, moved from Louisiana's; LA unchanged); RI resolves "Mr. Speaker" / "Madam President" to the officer on each roll call's day |
| people #46 `ec3daa04` | OPEN-786 | "Appollonio, Jr." as an other name of Sen. Peter A. Appollonio Jr. (his Senate page; Senate Journal 2026-01-06) |

All are reviewed and merged by the PM session. **No migration** (`git diff 42b48982 40c36019 -- '*migrations*'` is empty).

**Offline results (the builders'):**
* versions with no stage: 97.5% → **0.0%** (3,378 versions after);
* multi-version bills tied in order: 55 → **0** (with core #140);
* unmatched votes: 2,212 → **0**: Lawson 779, Appollonio 779, Shekarchi 140, Blazejewski 514;
* **no other vote changes.**

## Step 1: core `40c36019` on api-v3 (both hosts) and EC2 ddp-sync (on a GO)
* As for Kentucky's core (`22d7100` steps 2–3), with `DDP_CORE_SHA=40c36019d3b4a23448c0cab5c1b5637b9c7f98b2`:
    * Mac api-v3 via `refresh-api-v3.sh`;
    * EC2 api-v3 build plus `up -d --no-deps api`;
    * EC2 ddp-sync rebuilt at its current commit.
    * Then `check-core-pin-drift.py --image-core 40c36019…` exits 0 for each.
* **If the `42b48982` rebuild from `3cef331` hasn't run yet, do this one instead.** It contains `42b48982` (Kentucky) and SYNC-186's `b569cf2` plan is unchanged. One rebuild covers both.
* **If OPEN-788 (Oklahoma, core #141) is merged first,** build at core main then. I'll post an UPDATE with the commit, so it's one rebuild, not two.
* api-v3 timing: not 05:00–07:00 UTC (the scorecard chain reads it).

## Step 2: manifest rollout (on a GO; after #469 `ce2d4cc7`)
* **Pull first, then `rollout-manifest.sh --host ec2 --ddp-sync-root /opt/ddp-sync` (OPEN-532).** #469 changes the validator: the host's older validator would reject RI's dated officer value.
* Report the host's commit (`ce2d4cc7` or later), "N valid" and "every list agrees".
* Nothing else in the manifest changes for any state. #469 only adds RI's `votes` values and the validator rule.

## Step 3: the scrapers image (Ramon), after steps 1 and 2 have merged code
* Build at **scrapers main `2688a473` or later** (it holds #235 and #236). **The build clones ddp-open-states main, so build after `ce2d4cc7`**: today's main already has it.
* Core is taken from core main at build: `40c36019` or later.
* Mac side checks the scrapers tree contains `2688a473` and `DDP_CORE_COMMIT` is `40c36019` or later.
* If Idaho's v82 (notes `7788700`, `9b4d8b9`) isn't built yet, **one image built from today's mains serves both**: scrapers main has #234 (Idaho), #233 (North Carolina), #235 and #236.

## Step 4: people refresh for `ri` (on a GO)
* Pull `/opt/ddp-open-states/people` to people main **`d81a4c8cf9`** or later. Since `febf9fc1` (Idaho's step 1), only `data/ri/legislature/Pete-Appollonio-66e402e8-….yml` changed.
* `os-people`, `--safe` first, then real, **`ri` only**. **Expected: created 0, updated 1.** Anything else: stop and report.
* If Idaho's step 1 and NE/LA part A haven't run, this pull covers their files too. Load only `ri` here; each other state needs its own go.

## Step 5: the Rhode Island 2026 re-import (on a GO, after steps 1–4)
### Gates
1. Steps 1–4 are done and reported.
2. New tasks run the step 3 image's revision or later. Report it.
3. Nothing RI is running (`ddp:pipeline_lock:ri` empty).
4. Not on Sunday from 02:00 UTC (RI's weekly start).

### The run
```
POST /ddp-sync/v1/trigger/openstates-scrape/ri?full=true&sessions=2026
```
* The answer must be 202 with `"full": true`. A 409: wait.
* **Report:**
    * the run id and revision;
    * `"mode": "full"`;
    * load status with bill, version and vote counts. Expect 3,011 bills, about 3,378 versions, 1,433 vote events.
    * the archive result.
* The archive saves the newly added earlier texts. That takes longer than last time's 52 min.
* A load stopped by "already imported as ...": stop and report the full message.

### Pass/fail after (read-only, on RDS)
```sql
-- 1. versions with no stage, run as: DATABASE_URL=<RDS> python quality_check.py --structural ri  (core 40c36019 on PYTHONPATH)
--    expect "version stage coverage" under 5.5% (before: 97.5%)

-- 2. versions named by a bare number: expect 0 (before: 2,936+)
SELECT count(*) FROM opencivicdata_billversion bv JOIN opencivicdata_bill b ON b.id=bv.bill_id
JOIN opencivicdata_legislativesession s ON s.id=b.legislative_session_id
WHERE s.jurisdiction_id='ocd-jurisdiction/country:us/state:ri/government' AND s.identifier='2026' AND bv.note ~ '^[0-9]';

-- 3. unmatched person votes: expect 0 (before: 2,212)
SELECT pv.voter_name, count(*) FROM opencivicdata_personvote pv
JOIN opencivicdata_voteevent v ON v.id=pv.vote_event_id JOIN opencivicdata_legislativesession s ON s.id=v.legislative_session_id
WHERE s.jurisdiction_id='ocd-jurisdiction/country:us/state:ri/government' AND s.identifier='2026' AND pv.voter_id IS NULL
GROUP BY 1 ORDER BY 2 DESC;

-- 4. the officers: expect Val Lawson 779, Christopher Blazejewski 514, Joe Shekarchi 140
SELECT p.name, count(*) FROM opencivicdata_personvote pv JOIN opencivicdata_person p ON p.id=pv.voter_id
JOIN opencivicdata_voteevent v ON v.id=pv.vote_event_id JOIN opencivicdata_legislativesession s ON s.id=v.legislative_session_id
WHERE s.jurisdiction_id='ocd-jurisdiction/country:us/state:ri/government' AND s.identifier='2026'
  AND pv.voter_name IN ('Madam President','Mr. Speaker') GROUP BY 1 ORDER BY 2 DESC;
```
* **Fail** = any number off. Stop and report; no second run.
* **I check the same on the Mac replica** once it catches up. Then I post `reply-verified-ri-fixes-<date>.md` and record it on OPEN-665.
* **After that,** a `recompute-diff-order ri` dry run (its own request) settles the comparisons between the new versions.

## Scorecards
RI isn't live (routing and LegBot off), so no scorecard reads these votes today.

## Not authorized
* Any step before its GO note.
* Any other state's people load or re-import.
* A recompute or relabel.
* A second re-import.
* Any schedule, routing or LegBot change.

Tickets: OPEN-665 (OPEN-146); fixes OPEN-784, OPEN-785, OPEN-786.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
