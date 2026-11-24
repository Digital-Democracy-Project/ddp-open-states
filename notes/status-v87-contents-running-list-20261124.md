# STATUS (not a request, not a GO): **v87 contents**, a running list. I update this file as fixes merge. The release itself will be its own request note, on Ramon's go. Last updated 2026-11-24 ~05:00 UTC (Mac side, Onboard New States)

**Nothing for you to do from this file.** It exists so the next release note is short and you can see what is coming.

## Baseline
* v86 = `ddp-scrapers:88` / `db:15`: scrapers `cc028db6`, core `59dbdaa2`.
* The core rollout at `59dbdaa2` is planned for ~07:15 UTC (`deb1bc6`).
* The PM merges no core change until that rollout is reported done.

## Merged, waiting for v87 (scrapers) or a people load
| Kind | Merge | Ticket | What | Production steps it will need |
|---|---|---|---|---|
| scrapers | #264 → `b2d0d4db` | OPEN-820 | Wyoming: Senate Files and Senate Joint Resolutions get the Senate as origin chamber (90 of 335 bills in 2026 stored as House) | v87, then a WY 2026 full re-import |
| people | #50 → `fd7a7b55` | OPEN-838 | Nebraska: Fred Meyer's start set to 2026-01-15, so Glen Meyer's 7 votes of 01-14 match one person | people pull, NE load, then an NE 109 re-import (or relink) |
| people | #51 → `5a0e0af1` | OPEN-843 | Kentucky: "Lewis C" (441 House votes in 2026RS) added to Chris Lewis's other names | people pull, KY load, then a KY 2026RS re-import (or relink) |

## Held by the PM (core; after the `59dbdaa2` rollout is done, then a core rollout plus v87)
| PR | Ticket | What |
|---|---|---|
| core #149 | OPEN-822 | Rhode Island: "held for further study" is no longer labelled committee failure (2,222 actions; 602 of those bills later passed a chamber) |
| core #150 | OPEN-821 | Wyoming: "Failed Introduction" labelled as a failure; "Bill Number Assigned" no longer first reading |
| core #151 | OPEN-824 | Hawaii: 2,314 committee-report adoptions no longer labelled passage |

* Action labels are computed at import, so each needs that state's re-import, or the stored-action relabel the state-rules work uses, after the core rollout. That will be in the release note.

## In review (next round)
* scrapers #265–#268: added to this list when merged.

Tickets: OPEN-146.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
