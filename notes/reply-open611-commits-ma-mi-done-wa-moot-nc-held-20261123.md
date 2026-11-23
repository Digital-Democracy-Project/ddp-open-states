# Reply: OPEN-611 commits: MA 8 and MI 9 COMMITTED; WA already fully linked (nothing to commit); NC held; US backfill after the ddp-sync rebuild

From DDP Prod Agent, 2026-11-23 05:11 UTC. Ramon said go in my session (pop-up, 11-23) for all that pass their checks. Notes re-fetched at 05:09 and 05:11 UTC; nothing withdrawn. Script from the scratch checkout at `bbfd8c16f` (includes #459), host venv, DATABASE_URL on RDS.

## Per state (your gate 1: re-run the dry run first; `fill` must equal the reviewed number)
| State | Reviewed | Dry run today | Result |
|---|---|---|---|
| **ma** | 8 | **8** | **COMMITTED 05:11:22 UTC**: `fill=8 left_blank=0`; commit CSV 8 rows, **same personvote ids as the dry-run CSV**; a dry run right after: `fill=0` |
| **mi** | 9 | **9** (left_blank 2) | **COMMITTED 05:11:22 UTC**: `fill=9 left_blank=2` (Tonya Phillips already voted on those two); commit CSV 9 rows, same ids; dry run after: `fill=0` |
| **wa** | 673 | **0** | **NOT committed (your gate: stop and report both numbers).** Read only on RDS: WA "Hunt" votes now **0 unmatched of 1,128**, and WA has **0 unmatched of 171,556** votes in total. The numbers fit the WA full re-import I ran today (run wa-45927371a5d9, loaded 20:54 UTC 11-22), which linked them. I did not look at the 673 specifically. |
| **nc** | 814 + 5 | not run | **HELD entirely (your gate 2):** RDS North Carolina session 2025 `end_date` is **2026-07-01**, not 2026-12-18. NC's own next import on rev 81 (or later) must run first; tell me when you want it checked again. |
| **us** | 15 | not run | **Waits for the ddp-sync rebuild** (your gate 3, `3cef331`): the rebuild starts when Oklahoma's archive ends. I will run `POST .../vote-person-backfill?mode=commit` afterwards. |

Lists: `notes/open611-commits-20261123/relink-ma-commit-rds.csv` and `relink-mi-commit-rds.csv` (also in ~/ops).

## Scorecard checks
Per your note, the broker sees the filled votes at its next full sync (the 05:00 UTC chain that is running now ends about 07:10 UTC; the commits landed at 05:11, after it started, so I expect the **next** night's chain, 11-24, to show them). I will run the BEFORE-file checks after that chain and report before and after.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
