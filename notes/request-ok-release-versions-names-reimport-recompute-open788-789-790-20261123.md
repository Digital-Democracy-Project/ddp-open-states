# REQUEST (not a GO): Oklahoma's three fixes (OPEN-788 version stages, OPEN-789 "Crosswhite Hader", OPEN-790 "Mr. Speaker"). Steps in order: (1) the one core rebuild at `939e4a2c`, (2) manifest rollout (pull first), (3) the next scrapers image, (4) ONE full re-import of Oklahoma 2025 and 2026, (5) `recompute-diff-order ok`, dry run then commit. 2026-11-23 (Mac side, Onboard New States)

**Not a GO.** Each step waits on Ramon's go. Step 3 is Ramon's build. Steps 1, 2, 4 and 5 are the prod agent's, each after a GO note. **No people refresh is needed.**

## Why
Oklahoma's first scrape (`ok-7192f1fe4328`, rev 80, ddp-sync notes `55c4d90`), checked on the Mac replica (OPEN-666):
* **fails Stage 3's version-stage gate: 4,522 / 17,556 versions (25.8%) have no stage.** Many stored "versions" are amendments or proposals, not bill texts;
* has **3,451 unmatched votes**: "Hader" 1,928 and "Mr. Speaker" 1,479, plus 44 on one roll call;
* **and, found while fixing:** the scraper split "Crosswhite Hader" into two names. The extra name took a place in its section's count, so **the last voter listed in that section was dropped, 1,928 times** (453 times "Mr. Speaker", 1,475 times a member).

| Merge | Ticket | What |
|---|---|---|
| openstates-core #141 `939e4a2c` | OPEN-788 | OK version stages; amendment and proposal papers marked not-a-version (`openstates/ddp_states/ok.py`); versions ordered by the bill's own chamber. Whole-replica comparison: 895 (state, name) rows change, all Oklahoma |
| scrapers #237 `1726c4ce` | OPEN-789 | "Crosswhite Hader" kept as one name (House Journals 2025-01-07, 2026-02-02). Restores the 1,928 dropped voters. **Not** a people change (Ramon to confirm the switch; flagged by the PM session) |
| scrapers #238 `c29cfa4f` | OPEN-790 | OK resolves "Mr. Speaker" from the manifest through the shared reader (`utils/presiding_officers.py`) |
| ddp-open-states #470 `7c7deb12` | OPEN-790 | `ok.votes.house_speaker_by_session`: Kyle Hilbert for `2025` and `2026` (Journals 2025-01-07: elected Speaker; 2026-02-02: "called to order by Speaker Hilbert"). The Senate prints no title |

All are reviewed and merged by the PM session; Oklahoma's 99 tests pass on merged main.

**Offline results (the builders'):**
* versions with no stage: 25.8% → **0.0%**;
* unmatched votes: 3,451 → **44**. The 44 are the 2025-05-07 SB 920 "Committee Vote", whose page lists senators on a House roll call; outside these tickets;
* the 1,928 dropped voters return;
* **no one counted twice; nothing else changes.**

## Step 1: core `939e4a2c` (on a GO)
The one rebuild in `9d5d3ba` (KY, RI, OK): both api-v3 copies, then EC2 ddp-sync (with SYNC-186's `b569cf2`), then the drift check exits 0. **Nothing extra for Oklahoma.**

## Step 2: manifest rollout (on a GO)
* **Pull first, then `rollout-manifest.sh --host ec2 --ddp-sync-root /opt/ddp-sync`** (OPEN-532). Main is `7c7deb12` or later. It includes `ce2d4cc7` (RI, #469), which changed the validator, so a host older than that must pull first.
* **One rollout covers RI's step 2 (`98e5dcb`) and this one.** Report the commit and "every list agrees".

## Step 3: the scrapers image (Ramon)
* Build at **scrapers main `c29cfa4f` or later**, with core main **`939e4a2c`**, after ddp-open-states main `7c7deb12`.
* That one image carries Idaho (#234), North Carolina (#233), Rhode Island (#235, #236) and Oklahoma (#237, #238). It serves `7788700`/`9b4d8b9` step 2, `98e5dcb` step 3 and this step.
* Mac side checks the scrapers tree contains `c29cfa4f` and `DDP_CORE_COMMIT` is `939e4a2c`.

## Step 4: the Oklahoma 2025 + 2026 re-import (on a GO, after steps 1–3)
### Gates
1. Steps 1–3 done; new tasks run the step 3 revision or later. Report it.
2. Nothing OK running (`ddp:pipeline_lock:ok` empty).
3. Not on Sunday from 02:00 UTC (OK's weekly start).

### The run
```
POST /ddp-sync/v1/trigger/openstates-scrape/ok?full=true&sessions=2025,2026
```
(If the trigger takes one session per call, run `2025` first, then `2026`, never both at once.)
* The answer must be 202 with `"full": true` and both sessions echoed. A 409: wait.
* **Time:** the first run took 9 h 47 min (collection and load 4 h 49, archive 4 h 56); expect about the same. The limit is 6 h per phase. If a phase passes 6 h, stop and report; don't retry.
* **Report:** run id and revision, `"mode": "full"`, load status with bill / version / vote counts (expect 3,252 + 2,754 bills, 4,613 + 4,154 vote events), and the archive result.
* A load stopped by "already imported as ...": stop and report the full message.

### Pass/fail after (read-only, on RDS)
```sql
-- 1. unmatched person votes per name: expect only the 44 on SB 920 (2025-05-07); before: 3,451
SELECT pv.voter_name, count(*) FROM opencivicdata_personvote pv
JOIN opencivicdata_voteevent v ON v.id=pv.vote_event_id JOIN opencivicdata_legislativesession s ON s.id=v.legislative_session_id
WHERE s.jurisdiction_id='ocd-jurisdiction/country:us/state:ok/government' AND pv.voter_id IS NULL
GROUP BY 1 ORDER BY 2 DESC LIMIT 20;

-- 2. no "Hader" voter left: expect 0 (before: 1,928)
SELECT count(*) FROM opencivicdata_personvote pv JOIN opencivicdata_voteevent v ON v.id=pv.vote_event_id
JOIN opencivicdata_legislativesession s ON s.id=v.legislative_session_id
WHERE s.jurisdiction_id='ocd-jurisdiction/country:us/state:ok/government' AND pv.voter_name='Hader';

-- 3. "Mr. Speaker" votes, by person: expect Kyle Hilbert about 1,932, none unmatched
SELECT coalesce(p.name,'(none)'), count(*) FROM opencivicdata_personvote pv
LEFT JOIN opencivicdata_person p ON p.id=pv.voter_id
JOIN opencivicdata_voteevent v ON v.id=pv.vote_event_id JOIN opencivicdata_legislativesession s ON s.id=v.legislative_session_id
WHERE s.jurisdiction_id='ocd-jurisdiction/country:us/state:ok/government' AND pv.voter_name='Mr. Speaker' GROUP BY 1;

-- 4. roll calls where one person has two votes: expect 0
SELECT count(*) FROM (SELECT pv.vote_event_id, pv.voter_id FROM opencivicdata_personvote pv
  JOIN opencivicdata_voteevent v ON v.id=pv.vote_event_id JOIN opencivicdata_legislativesession s ON s.id=v.legislative_session_id
  WHERE s.jurisdiction_id='ocd-jurisdiction/country:us/state:ok/government' AND pv.voter_id IS NOT NULL
  GROUP BY 1,2 HAVING count(*) > 1) x;

-- 5. person votes in all: expect about 331,234 (no one is dropped any more, and no extra "Hader" rows)
SELECT count(*) FROM opencivicdata_personvote pv JOIN opencivicdata_voteevent v ON v.id=pv.vote_event_id
JOIN opencivicdata_legislativesession s ON s.id=v.legislative_session_id
WHERE s.jurisdiction_id='ocd-jurisdiction/country:us/state:ok/government';
```
* **Fail** = any number off. Stop and report.
* I check the same on the Mac replica. Then I post `reply-verified-ok-fixes-<date>.md` on OPEN-666.

## Step 5: `recompute-diff-order ok` (on a GO, after step 4 is verified)
* At core `939e4a2c`, **after the re-import**, so it acts on the re-imported versions.
* Prove the rule is present first (`openstates/ddp_states/ok.py` exists in that core).
* **Dry run first:** `os-text-extract recompute-diff-order ok --dry-run --list <file>`, after exporting OK's stored comparisons as the backup, as for NM.
* **Measured on the Mac replica before the re-import** (builder, read-only session):
    * `6005 bills checked | unchanged=7682 corrected=7261 nulled=2631`;
    * `is_bill_version: set=0 changed=3272 not_a_version=3272`;
    * `diff_baseline_id: set=3882 changed=3379 cleared=2631`.
* After the re-import the numbers shift, because the archive will have run with the new core. I'll measure the dry run on the replica again and post the expected range in an UPDATE before step 5.
* Report the exact lines and the list's md5. **The commit holds until its own GO note.**
* **Ramon's open call:** "Amended And Engrossed" (369 documents) stays a version as built. If he decides otherwise, a core change comes first.

## Scorecards
OK isn't live (routing and LegBot off). The 1,928 restored voters and the Speaker's votes reach no scorecard until go-live.

## Not authorized
* Any step before its GO note.
* A people refresh.
* Any other state's re-import or recompute.
* A second re-import.
* A recompute commit without its own GO.
* Any schedule, routing or LegBot change.

Tickets: OPEN-666 (OPEN-146); fixes OPEN-788, OPEN-789, OPEN-790.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
