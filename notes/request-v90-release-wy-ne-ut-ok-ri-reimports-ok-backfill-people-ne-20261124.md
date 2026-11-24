# REQUEST (not a GO): **the v90 release.** Image v90 (scrapers `89e390d1`, core unchanged `70146fac`, no core rollout), the Nebraska people fast-forward, then ONE re-import each of Wyoming, Nebraska, Utah, Oklahoma and Rhode Island, and the optional Oklahoma roll-call-number backfill. 2026-11-24 ~21:15 UTC (Mac side, Onboard New States)

**Not a GO.** Each numbered step waits on Ramon's go in your session. It follows `a0e5d64`, `9e63a3d` and `e613948`; **the Wyoming hold in `e613948` lifts with this image.** Every merge below was checked on GitHub just now.

## What v90 contains (all merged to scrapers main, head `89e390d1e36308e740ff05a80bd4df6f4d93e4e0`)
| PR | State | What changes in the data after a re-import |
|---|---|---|
| #285 (OPEN-874) | **WY** | failed introductions and failed committee-of-the-whole votes count; whole-bill veto overrides count (the 14 SF 1 line items do not) |
| #284 (OPEN-876) | **NE** | General File / Select File advancement roll calls count as passage |
| #286 (OPEN-875) | **UT** | a Senate "passed 2nd reading" roll call counts when no later Senate passage roll call follows |
| #287 (OPEN-872) | **OK** | each roll call stores `house-rollcall-num` / `senate-rollcall-num` in its extras |
| #288 (OPEN-873) | **RI** | the Senate's budget roll calls load; calendar items read as passed |

* **Core is unchanged (`70146fac`):** no api-v3 or ddp-sync rebuild. After the image, `check-core-pin-drift.py --image-core 70146fac…` must still exit 0, and ddp-sync's `DDP_SCRAPERS_COMMIT` stays `b2aa844d…` (the load reads scrapers only inside the Fargate task's image).

## Step 1: image v90 (Ramon builds on the Mac)
* Build at scrapers main **`89e390d1…` or later**, core **`70146fac…`**. I check `DDP_CORE_COMMIT` = `70146fac` and the scrapers commit on the Mac side and post the revision for you.

## Step 2: Nebraska people, before Nebraska's re-import
* Fast-forward `/opt/ddp-open-states/people` to people main (**`26f4ad0d`**, people #53: Fred Meyer's note shortened to 225 characters; OPEN-877).
* `os-people` `--safe` then real for **ne** only. **Expect 0 created, 1 updated**, no "went missing" or retirement line. Anything else: stop and report.
* **Why:** the earlier Nebraska people load failed on a 350-character note (varchar 300). This is the fix.

## Step 3: re-imports on v90, each its own task, started together (parallel, per `9e63a3d`)
Each `POST /ddp-sync/v1/trigger/openstates-scrape/<st>?full=true&sessions=…` must answer 202 with `"full": true`. Report the run id, revision, counts and archive result. One run per state: **Oklahoma starts only after its current 2026 run (`ok-3f164c3f15c1`) ends.** Everything else started together, on or after v90's revision. A failure stops that state only; two states failing with the same error stop further starts.

| State | Request | Pass (I read it on the Mac replica after the load) |
|---|---|---|
| **WY** | `wy?full=true&sessions=2026` | counted bill-chambers **276 → 382**; 109 changed-vote rows (106 new + 3 concurrences replaced by a later failed override); the 14 SF 1 line items still `veto-override`; 0 unmatched |
| **NE** | `ne?full=true&sessions=109` (after Step 2) | counted bill-chambers **372 → 412**; the 470 stored advancement roll calls now typed; "Returned to Select File" and "Motion to return … failed" still **not** passage |
| **UT** | `ut?full=true&sessions=2026,2025S2` (the two sessions measured in #286) | **exactly 16** Senate bill-chambers start counting their 2nd-reading vote; none stops; 1,917 votes unchanged in number |
| **OK** | `ok?full=true&sessions=2025,2026` (after its current run) | 8,767 votes, **every one carries `house-rollcall-num` or `senate-rollcall-num`**; unmatched as in `0beadee` (2025: 44; 2026 about 0); 0 double votes; person votes about 331,234 |
| **RI** | `ri?full=true&sessions=2026` | Senate roll calls on HB 7127 **0 → 14** (12 amendments, 1 consideration 31-7, 1 passage 32-6); the other 1,433 events keep their key, bill, chamber and counts; 7 motion/label lines change |

* **Image revision:** every task must run v90's revision or later. A run that started earlier carries the old code: report it and don't count it.

## Step 4: Oklahoma roll-call-number backfill (optional, **before** Oklahoma's re-import; dry run first)
* Pull `/opt/ddp-open-states` to main **`3d1801a4…`** or later (ddp-open-states #487; it only adds Oklahoma to `backfill-vote-rollcall-num.py`).
* `--dry-run --list <file>` for `ok`: **expect 8,767** rows, list md5 `ce1039b50c43c9a00d3259731c690551` (measured on the PR's head; if your md5 differs, report both and stop).
* Commit only on Ramon's **second** go, `--apply-list <file> --expect 8767`, with `--undo` as the way back. All or nothing; a stored number is never changed.
* **Not needed for correctness:** Oklahoma's re-import writes the same numbers. It only makes them show before the re-import.

## Not authorized
* Any step before its go; a second run of any state; the Oklahoma re-import while its 2026 run is going.
* Any relabel or recompute commit (their dry runs come after each re-import is verified).
* Rhode Island's open header-shape question (S 2067 twice, Senate H 7165) is **Ramon's decision**, not yours; the re-import doesn't depend on it.
* Any manifest, schedule, routing or LegBot change.

## What I check on the Mac side
Each state's numbers above, per state as its load lands, then "verified" or a stop for that state. Then the relabel and recompute dry-run numbers for WY, NE, UT, OK and RI go in the next note.

Tickets: OPEN-146; OPEN-874 (WY), 876 (NE), 875 (UT), 872 (OK), 873 (RI), 877 (people).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
