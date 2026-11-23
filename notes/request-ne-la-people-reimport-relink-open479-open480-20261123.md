# REQUEST (not a GO; each part waits on Ramon's go): Nebraska and Louisiana before go-live. (A) people refresh on production, (B) a whole-session re-import of NE `109` and LA `2026` so their unmatched votes link, (C) the check that no vote is left unmatched. Queued behind the v79 rollout. 2026-11-23 (Mac side, Onboard New States)

**Ramon, 2026-11-23 (PM session's /ask-me, recorded on OPEN-447): "Write them now"** for Nebraska and Louisiana. Each step waits on his go, and all of them queue behind the v79 rollout (core `42b48982`). This note is not a go: start each part only on a GO note for it. The go-live manifest changes are separate PRs (see the end).

## Why
On 11-22 Ramon held NE and LA back until their unmatched names are fixed and the stored votes re-linked (OPEN-447 comment 22531). Every fix is now merged and in v79 or on people main.

**The Mac replica, read-only, 2026-11-23.** These are the only NE/LA sessions with any unmatched vote:

| State, session | Votes | Unmatched | Names, with their fix |
|---|---|---|---|
| **la 2026** | 230,721 | **8,005** | "Mr. Speaker" 1,624 and "Mr. President" 1,548: OPEN-764 (scrapers #221, reads the manifest's presiding officers, #460, already rolled out) · "Galle" 1,624, "Amedee" 1,624, "Fesi" 1,548: OPEN-763 (people #40, `other_names`) · "Henry" 37: people #40 (Dana Henry seated 2026-03-24) + core date matching OPEN-767 |
| **ne 109** | 86,723 | **1,267** | "Meyer" 955: people #41 (Fred Meyer's term ends 2025-01-08) + core OPEN-767 · names ending "\*" (about 312, e.g. "Cavanaugh, M.\*" 43): OPEN-761 (scrapers #217) |

* NE 109 also holds the six veto overrides that BROKER-579 (scrapers #222) now labels as passage: 2025 LB 319, LB 287; 2026 LB 1256, LB 878, LB 839, LB 929.
* The re-import is needed because NE's and LA's scheduled runs are incremental: unchanged bills keep their old, unmatched votes.
* The older tool `relink-blank-voters.py` (OPEN-611) has no NE or LA case. The re-import is the path, as the tool's own notes say: the source fix first.

## Gates for every part (stop and report if one fails)
* **G1, v79 rollout done** (notes `22d7100` steps 2–3):
    * both api-v3 copies are at core `42b48982`;
    * **EC2 ddp-sync is rebuilt with `DDP_CORE_SHA=42b48982c3378c84f6c549ac9ac37be12bdbf2ae`**, and `check-core-pin-drift.py` exits 0.
    * Loads use ddp-sync's own core (SYNC-180). Before this, "Meyer" and "Henry" stay unmatched (they need OPEN-767).
* **G2, the image:** new tasks run ddp-scrapers:81 (v79) or later. Report the revision.
* **G3, nothing in flight for the state:** no `ne` / `la` collection, load, archive, LegBot or text-extract task, and `ddp:pipeline_lock:<st>` empty.
    * LA's and NE's scheduled runs are their weekly days (LA and NE Thursday 12:00 UTC, SYNC-172).

## Part A: people refresh (one go covers both states; LA first, then NE)
1. Pull `/opt/ddp-open-states/people` to people main **`efc8618838`** or later. Since your last pull (`f9043a7abe`, `a9f2888`), only #40–#43 changed, and only these files:
    * **la**: 5 legislature files (#40: Amedee, Galle, Fesi `other_names`, Dana Henry's start; #43: Paul Sawyer's start 2026-03-24);
    * **ne**: 1 legislature file (#41, Fred Meyer) and 16 retired files (#42, terms end 2025-01-08 instead of the bulk 2025-02-03).
2. Load with the container's `/opt/venv-openstates/bin/os-people`, as on 11-21, `--safe` first, then real, **one state at a time**.
    * **Expected: la created 0, updated 5. ne created 0, updated 17.**
    * No "went missing" or retirement line.
    * **Anything else: stop at that state and report.**

## Part B: whole-session re-import (one go per state; after A for that state)
SYNC-181's trigger, as for Washington on 11-22 (`f179ccc`):
```
POST /ddp-sync/v1/trigger/openstates-scrape/la?full=true&sessions=2026
POST /ddp-sync/v1/trigger/openstates-scrape/ne?full=true&sessions=109
```
* One state at a time. The answer must be **202** with `"full": true` and the session echoed. A 409: wait; don't force.
* **Report:**
    * the run id and revision;
    * the collection's `"mode": "full"`;
    * the load's final status with bill and vote counts;
    * the archive result.
* **A load stopped by "already imported as ..."** (both states set vote keys): stop and report the full message.
* **Not while the other state's re-import is running**, to keep one heavy load at a time.

## Part C: the check that no vote is left unmatched (read-only, on RDS; after each state's B)
Before and after counts, per state and session:
```sql
SELECT s.identifier, count(*) AS votes, count(*) FILTER (WHERE pv.voter_id IS NULL) AS unmatched
FROM opencivicdata_personvote pv
JOIN opencivicdata_voteevent v ON v.id = pv.vote_event_id
JOIN opencivicdata_legislativesession s ON s.id = v.legislative_session_id
WHERE s.jurisdiction_id = 'ocd-jurisdiction/country:us/state:<st>/government'
GROUP BY 1 ORDER BY 1;
```
and the names still unmatched:
```sql
SELECT pv.voter_name, count(*) FROM opencivicdata_personvote pv
JOIN opencivicdata_voteevent v ON v.id = pv.vote_event_id
JOIN opencivicdata_legislativesession s ON s.id = v.legislative_session_id
WHERE s.jurisdiction_id = 'ocd-jurisdiction/country:us/state:<st>/government' AND pv.voter_id IS NULL
GROUP BY 1 ORDER BY 2 DESC LIMIT 20;
```
* **Expected after B: unmatched 0 in la 2026 and ne 109.** Every other session is unchanged (they had 0).
* Any name left unmatched: report it with its count. I'll find its source fix; no hand-linking.
* For NE, also report the six override roll calls' `motion_classification`: expected `passage`.
* **I check the same on the Mac replica** once it catches up, plus:
    * "Mr. Speaker" and "Mr. President" linked to each session's presiding officer from the manifest;
    * "Meyer" votes on and after 2025-01-08 linked to Glen Meyer and none to Fred;
    * "Henry" votes linked by date.
    
    Then I post `reply-verified-ne-la-relink-<date>.md`.

## Scorecard effect (for Ramon, before the go-live PRs)
* Linking about 9,272 votes and labelling six NE overrides as passage changes which votes can count on NE and LA legislators' scorecards.
* Ramon decided overrides count (BROKER-579), and the re-link is the decision of 11-22.
* After C, I list the change per legislator from the replica for his review with the go-live go.

## After this: the go-live manifest PRs (each its own go)
* ddp-open-states PRs, one per state, on the #458 pattern: `status: live`; `search_refresh`, `embedding`, `api_smoke_test`, `qa_sweep` true. Routing and LegBot are already on.
* Each merges only after its state's part C is verified, on Ramon's go. Its rollout request follows then.

## Not authorized
* Any part before its GO note.
* Any other state or session.
* A relabel or recompute.
* `relink-blank-voters.py --commit`.
* Any manifest, schedule, routing or LegBot change.
* A second re-import of the same session.

Tickets: OPEN-479 (NE), OPEN-480 (LA), OPEN-447; fixes OPEN-761/762/763/764/767/768, BROKER-579 (OPEN-146).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
