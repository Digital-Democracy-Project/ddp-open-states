# STATUS (not a request, not a GO): **v88 contents**, a running list. It replaces the v87 list now that v87 is built. I update it as fixes merge; the release itself will be its own request note, on Ramon's go. Last updated 2026-11-24 ~14:00 UTC (Mac side, Onboard New States)

**Nothing for you to do from this file.**

## Baseline
* **v87** = `ddp-scrapers:89` / `db:16`: scrapers `b2d0d4db`, core `d5e548e8`.
* Its core rollout and North Dakota's `refresh-extraction` wait on Ramon's go (`cc1b14d`).
* Live core on EC2 is still `59dbdaa2` (v86's).

## Merged since v87, for v88
### Core (needs a core rollout at the core main v88 is built from)
| Merge | Ticket | What | After the rollout |
|---|---|---|---|
| #159 → `a124a218` | OPEN-841 | Oregon action labels ("Speaker/President signed." aren't passage; "concurred and repassed" is; "Failed." is failure) | `relabel or` (dry run first; 337 per State Specific Handling's `1803675`) |
| #165 → `e9b90e67` | OPEN-846 | Oregon: 433 amendment papers and minority reports aren't versions | `recompute-diff-order or` (dry run first: 433/432/201 per `1803675`) |
| #161 → `9f8fe018` | OPEN-833 | North Dakota floor defeats get `failure` (421 bills) | `relabel nd` (dry run first: 438 actions) |

### Scrapers (v88)
| Merge | Ticket | What | After v88 |
|---|---|---|---|
| #266 → `02ec6420` | OPEN-823 | Hawaii actions in date order | Hawaii's single re-import (Ramon: once, after its fixes) |
| #273 → `71655e3e` | OPEN-848 | Missouri: 28 Senate bills never scraped (incl. signed SB 1470); failed page loads now fail the run | Missouri 2026 full re-import |
| #274 → `af2f9857` | OPEN-852 | Kentucky second-chamber actions filed under the right chamber | Kentucky people refresh, then 2026RS re-import |
| #264 → `b2d0d4db` | OPEN-820 | Wyoming chambers: **already in v87** | One Wyoming re-import after core #150 / #160 |

### People (any time; one pull)
| Merge | Ticket | What | Then |
|---|---|---|---|
| #50 → `fd7a7b55` | OPEN-838 | Nebraska: Fred Meyer's start 2026-01-15 | NE load, then NE 109 re-import (optional per Ramon) |
| #51 → `5a0e0af1` | OPEN-843 | Kentucky: "Lewis C" | KY load before the KY re-import |

## Still in review (added here when merged)
* **Core:**
    * #149 (RI), #150 → #160 (WY), #151 → #166 (HI);
    * #157 → #167 (MO), #169 (ND, on #161, now merged);
    * #163 (ID), #153 and #158 (KY), #152 → #156, #168 and #170 (MT), #154 (MD), #155 (GA), #164 (NV);
    * OPEN-866–869 (being built).
* **Scrapers:**
    * #268 and #277 (HI), #270 (MS), #271 (MD), #267 (ME), #275 (MT);
    * #265, #269 and #272 (NV), #276 (WA pre-filing).
* **Other repos:**
    * api-v3 #78 (MT hidden drafts), people #52 (ME check);
    * ddp-open-states #478, #481, #483, #484;
    * ddp-sync #308;
    * broker #820 and #822–#825 (scorecard rules).

Tickets: OPEN-146.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
