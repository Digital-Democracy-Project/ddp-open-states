# REQUEST (not a GO): **the v89 release.** Image v89 (scrapers **`b2aa844d`**, core **`0d373728`**, unchanged: **no core rollout**), then three guarded backfills (Nevada results, Georgia and Alabama roll-call numbers), then the Missouri, Nevada and Alabama re-imports, then the Georgia re-check. 2026-11-24 ~19:00 UTC (Mac side, Onboard New States)

**Not a GO.** Each step waits on Ramon's go in your session. It follows the v88 request (`e30bb8e`) and its updates (`c93134c` Missouri, `3a257a6` Nevada): those two steps (Missouri's and Nevada's re-imports) are **here**, on v89, and **not** in v88's order.

## What v89 adds to v88 (scrapers main `b2aa844d17973227fbe26659152e556e5cfe3fb8`; core `0d373728` is unchanged)
| Merge | Ticket | What |
|---|---|---|
| #279 `85d9ce59` | OPEN-869 | Missouri: each action filed under the chamber whose journal records it |
| #280 `a0795446` | OPEN-865 | Nevada: a vote's result from NELIS ("Passed No" and "Rescinded" give fail; a rescinded vote loses its passage label, keeps its tally) |
| #281 `61853935` | OPEN-864 | Georgia: each vote's roll-call number stored (`house-rollcall-num` / `senate-rollcall-num`) |
| #282 `16c8a2e6` | OPEN-863 | Alabama: each vote stores ALISON's roll-call number under the same keys |
| #283 `b2aa844d` | OPEN-863 | Alabama: a "motion to adopt" right after an "Amendment/Substitute Offered" row, same chamber and day, is labelled `amendment` (HB 605 Senate, SB 146 Senate; HB 201 stays passage) |

* ddp-open-states main is **`b7dbefb1b01a17f927b321d3b85c8edaa7ade6fb`**. Since `d3d985d` it gained only **#485** (the Nevada fix-up) and **#486** (the Georgia and Alabama backfill). **Pull `/opt/ddp-open-states` to it** before step 2 (the tools live there). The manifest is unchanged, so no manifest rollout.

## Step 1: image v89 (Ramon)
* Build at scrapers main **`b2aa844d`** or later, with core **`0d373728`**. Mac side checks `DDP_CORE_COMMIT` = `0d373728` and that the scrapers hold `b2aa844d`.
* **ddp-sync's recorded scrapers commit** (SYNC-188) should equal the live image's: `DDP_SCRAPERS_SHA=b2aa844d17973227fbe26659152e556e5cfe3fb8` at ddp-sync's **next** build. I recommend no extra restart for it (the loader only imports the scrapers package; none of #279–#283 changes how it loads). If the v88 rollout (`e30bb8e` step 1) hasn't built ddp-sync yet, build it once with v89's commit.

## Step 2: three backfills (each on a go; **dry run first, compare the md5 and counts**, then apply; keep each `--list` output for `--undo`; all-or-nothing; a second dry run must plan 0)
After step 1 for Nevada (its scraper rule must be live first); Georgia's and Alabama's can run any time after the pull.

| State | Tool and flags | List | Expect |
|---|---|---|---|
| **NV** (OPEN-865, ddp-open-states #485) | `backfill-motion-classification.py --nv-result --apply-list notes/open865-nv-vote-result-dry-run-20261124.csv --expect 5 --list <committed>.csv`. **Production only applies the list** (planning needs NELIS pages, which the Mac has); a row that changed since aborts with nothing written | md5 `125ccbe0ef24fb1b170205fa3a5e2dce` | **`--expect 5` = 5 columns on 3 votes:** AB 4 Senate (3rd Reprint, 16-2, "Rescinded"): `result` pass → fail, `motion_classification` passage → none, `extras.nelis_outcome` → Rescinded (3 rows); AB 5 Senate (10-8, "Passed No (Constitutional Majority)"): `result` → fail; SB 10 Assembly (27-10, "Passed No (2/3 of Elected Members)"): `result` → fail. 33 Nevada votes stored in all |
| **GA** (OPEN-864, #486) | `backfill-vote-rollcall-num.py --jurisdiction ga --dry-run --list <file>`, compare, then `--apply-list <list> --expect 280 --list <committed>.csv` | md5 `ea69e3715f5f7aff2058844b0b198e5f` | **280 votes** (245 House, 35 Senate, all `2026_ss`; none numbered; 0 chamber mismatches); all 26 votes of the **13 same-day ties** are in it (e.g. SB 3 Senate #27 and #28) |
| **AL** (OPEN-863, #486) | same tool, `--jurisdiction al`, `--apply-list <list> --expect 2550 --list <committed>.csv` | md5 `ad12bf8301a199efd315c92ddf999275` | **2,550 votes** (1,359 House, 1,191 Senate; none numbered); the 3 same-day pairs are in it: HB 460 House 520/521, HB 605 Senate 1316/1317, SB 146 Senate 813/814 |

* The lists are deterministic: re-run the dry run on the host and compare the md5. A stored number is never changed; neither tool touches `updated_at`. The GA and AL numbers use the key the scrapers write, so a later re-import agrees.
* **A different md5 or count: stop and report.** Don't edit a list.
* The Mac's copies (untracked): `ddp-open-states-dev/notes/open864-ga-rollcall-list-20261124.csv`, `.../open863-al-rollcall-list-20261124.csv`, and the tracked `notes/open865-nv-vote-result-dry-run-20261124.csv`.
* **Never run `backfill-motion-classification.py` for any state it doesn't cover** (Arizona's `--az-*` and Nevada's `--nv-result` only).

## Step 3: re-imports on v89 (one heavy load at a time; each followed by my Stage 3 and "verified")
`POST /ddp-sync/v1/trigger/openstates-scrape/<st>?full=true&sessions=…` must answer 202 with `"full": true`. Report the run id, revision, counts per session and the archive.

| # | State | Sessions | Pass/fail (Stage 3 at core `0d373728`, plus) |
|---|---|---|---|
| 3a | **MO** (**once**) | `2026` | the v88 lines (`e30bb8e` 4c): about 3,161 bills; SB 1470 and the other 27 missing Senate bills present; SB 1534, SB 838, SB 841 and SR 668 no longer "passed". **New:** 306 actions on 105 bills change chamber (247 House → Senate, 59 Senate → House); HCR 21 and 22's "Adopted (H) - AYES: 31" of 01-08-26 are under the Senate; the 27 Senate "Truly Agreed To and Finally Passed" votes sit under the Senate; 144 "House/Senate Message" lines under the chamber whose journal reads them in |
| 3b | **NV** | `2025Special36,84` | the v88 lines (`e30bb8e` 4e): sponsors 0 unmatched of 27; versions 237; versions named `^Amendment` 0; documents named `^Amendment` 26; no action text with a line break; `2025Special36` 431 actions; `passed_both_without_passed_one` 0. **New:** AB 4, AB 5 and SB 10 read as fail (the re-import writes the same result as the Step 2 apply, so a second dry run of Step 2 still plans 0); AB 4's rescinded vote has no passage label and `extras.nelis_outcome` "Rescinded" |
| 3c | **AL** | `2026rs` | Stage 3 unchanged (people 285; versions 0/2,867; votes 0/183,715; sponsors 0/1,507); `house-rollcall-num` / `senate-rollcall-num` on every vote (the same numbers as Step 2); the "motion to adopt" after "Amendment/Substitute Offered" labelled `amendment` on **HB 605 Senate and SB 146 Senate**, HB 201 still passage; 1,093 passage votes before (the broker's count changes with its own migration, not here) |

* **Missouri runs once**, here, not on v88. Its relabel and recompute dry runs (`e30bb8e` steps 5 and 6) come after it.
* Nevada's relabel and recompute (`e30bb8e` step 6: corrected 32, nulled 26, flags 26, baselines 22/10/26) come after its re-import.

## Step 4: the Georgia re-check (read-only, after Step 2's GA apply)
* **Every one of the 13 same-day ties counts one vote.** `validate_scorecards --jurisdiction GA --all` (after the next scorecard chain, once the broker's Georgia rules are live) and the Mac's read: for each tied pair, the later roll-call number is the counted vote.
* BROKER-593's expected effect: 183 → 109 counting votes (0 start, 74 stop).

## Broker order that depends on this (for the broker request, not this one)
* **Nevada's migration `0116` (broker #824, BROKER-594) deploys only after v89 and the Nevada apply** (Step 1, Step 2 NV, Step 3b). Alabama 0113 (#822), Georgia 0114 (#823) and Oregon 0115 (#826) go before it; Alabama and Georgia also want Step 2's numbers in place.
* Broker #827 (the sitemap) needs api-v3 #79 live first.

## Not authorized
* Any step before its go.
* A core rollout (core is unchanged).
* A re-import of Hawaii twice, Wyoming twice, or Missouri twice.
* Editing a list, or any list other than those named here.
* Any flag or state beyond those named for the backfill tools.
* Deleting any lock, S3 object or Redis key.
* Any manifest, schedule, routing or LegBot change.

## If it goes wrong
* **Backfills:** `--undo <committed>.csv`. A failed apply writes nothing.
* **Image:** register v88 (or v86) as the previous revision.

Tickets: OPEN-146; OPEN-863, OPEN-864, OPEN-865, OPEN-869; BROKER-593, BROKER-594.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
