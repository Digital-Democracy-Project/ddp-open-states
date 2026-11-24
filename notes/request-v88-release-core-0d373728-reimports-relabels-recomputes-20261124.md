# REQUEST (not a GO): **the v88 release.** One core rollout at **`0d373728`**, image **v88** (scrapers **`0aba6be6`**, core **`0d373728`**), a people load, then re-imports, relabels, recomputes, text re-reads and stale-archive removals. Every state gets its own pass/fail checks. 2026-11-24 ~15:30 UTC (Mac side, Onboard New States)

**Not a GO.** Each numbered step waits on Ramon's go in your session; I list the questions for him below. Recompute and relabel **commits** each wait on a second go after he has seen that state's dry-run numbers. The contents list is `status-v88-contents-running-list-20261124.md`.

## Decisions for Ramon first (the PM is putting them to him)
1. **Skip v87's rollout?** v88 contains everything v87 has. I recommend **one rollout at `0d373728` and no rollout at `d5e548e8`** (`cc1b14d`).
2. **Hawaii and Wyoming: one re-import each, on v88** (his earlier answers).
3. **Maine, Maryland, Mississippi: a second pass on v88?**
    * ME's v86 re-import (`me-98110acf6911`) fixes versions and votes, but two v88 fixes need data re-read: scrapers #267 (action order) and core #171 (engrossment as passage).
    * Core #171's labels are fixed by `relabel me` alone. Action order needs a second Maine re-import on v88.
    * MS: #270 (Governor as the "Office of the Governor") needs a re-import; MD: #271 (wrapped final-passage motions) needs the next Maryland run.
    * I recommend **a second pass for ME, MD and MS at the end, after the first ones are verified**, and no sooner.

## Step 1: one core rollout, `DDP_CORE_SHA=0d373728ff8fd18308a689542b0ded7ec7d11d8b` (on a go)
* **Prerequisites:**
    * the LA/NE go-live rollout (`df158e2`) has run, or run it first. It pulls `/opt/ddp-open-states` to main `d3d985d`, which carries #483 (the unmatched-voter script, bind-mounted, no rebuild), #481, #478 and the MD officers;
    * if you'd rather not do that rollout yet, pull `/opt/ddp-open-states` to `d3d985d34c8ed0c7726b7bf536dcd5e58eecf255` only for the script, and say so in your report.
* **EC2 api-v3:**
    * rollback tag;
    * build from api-v3 main (**`903013d`** at least: #78, OPEN-861, hides a draft record that a bill replaced, using the state's draft relation from core `mt.py`) with the core above;
    * `up -d --no-deps api`;
    * not 05:00–07:00 UTC.
* **EC2 ddp-sync:**
    * ff `/opt/ddp-sync` to main **`e7f4b35f524c96ed8b01352686be8168e887e980`**. Since `60791f5` that is only #308, the after-load alert on unmatched voter names, which needs the `#483` script above. It's switched on in `sync_schedule.yaml`;
    * build with **`DDP_CORE_SHA=0d373728…`** and **`DDP_SCRAPERS_SHA=0aba6be6631b4bb97ab2a83719661bcd449be707`**; the import check must pass;
    * tag a rollback and post the in-flight list;
    * wait for any run that is loading;
    * never 02:15–04:45 UTC.
* **Mac api-v3:** mine, after your note (`SCRAPERS_IMAGE_CORE=0d373728…`).
* **Then:** `check-core-pin-drift.py --image-core 0d373728…` exits 0 everywhere, and `DDP_SCRAPERS_COMMIT` in ddp-sync reads `0aba6be6…`.
* **Expect:** a one-time burst of "first check" alerts, one per state with unmatched voter names (about 16), the first night after #308 starts. That is intended. After that it alerts on change only.
* **After it:** MT's draft LC 858 is hidden from the API lists but still opens by id; check that `bill_types_only` totals drop by 1.

## Step 2: image v88 (Ramon)
* Build at scrapers main **`0aba6be6631b4bb97ab2a83719661bcd449be707`** or later, with core **`0d373728`**.
    * It carries scrapers #265–#278 (HI, MO, KY, MS, MD, ME, MT, NV, WA) and v87's #264. Not #279 (Missouri's journal chamber; waits on Ramon's call).
* Mac side checks `DDP_CORE_COMMIT` = `0d373728` and that the scrapers hold `0aba6be6`.
* **WA pre-filing (#276) is in it:** its first nightly after v88 scrapes both 2025-2026 and 2027-2028 and must not fail (`OPEN-853`). Report that run's counts.

## Step 3: people, one pull (any time after Step 1)
* Pull `/opt/ddp-open-states/people` to **`37bcb364bc93006c4bcc64e714d4c58b551c4afe`**. Since `05d7e4cc`, only three data files changed:
    * **KY:** Chris Lewis: "Lewis C" added (OPEN-843);
    * **NE:** Fred Meyer: his start date 2026-01-15 (OPEN-838);
    * **ME:** Nancy Theriault: "THERIAULT of Millinocket" added (OPEN-854).
* `os-people` `--safe` first, then real, **one state at a time** (ky, ne, me): each should show **0 created, 1 updated**, no "went missing" or retirement line. Anything else: stop and report.
* Kentucky's load must come **before** Kentucky's re-import.

## Step 4: re-imports on v88 (one heavy load at a time; each after its people load; Not Sunday from 02:00 UTC)
All `POST /ddp-sync/v1/trigger/openstates-scrape/<st>?full=true&sessions=…` must answer 202 with `"full": true`. Report the run id, revision, per-session counts and the archive result. I verify each on the Mac replica and post "verified" or a stop **before** the next one. Order, smallest and most blocked first:

| # | State | Sessions | Pass/fail (Stage 3 at core `0d373728`, plus) |
|---|---|---|---|
| 4a | **WY** | `2026` | bills 335; SF/SJ bills stored as Senate (90 were House); `validate_bill_stages wy`: `first_passage_not_by_origin_chamber` about 0, `passed_both_without_passed_one` 0; "Failed Introduction" actions carry `failure`; 0 backward action steps; 0 unmatched; 0 double votes |
| 4b | **KY** | `2026RS` | after Step 3; unmatched votes **0** of 61,568 (was 450: "Lewis C" 441, "Lewis" 9); 1,737 bills; no "passed over and retained" line tagged passage; second-chamber passage lines filed under the right chamber; "Passed both chambers" about 213 |
| 4c | **MO** | `2026` | bills about 3,161 (3,133 + 28); **SB 1470 present** (signed by the Governor); the 28 missing Senate bills present; SB 1534, SB 838, SB 841 and SR 668 no longer read "passed"; a failed page load fails the run (`#273`), so report any failure, don't retry |
| 4d | **HI** | `2026` | **once**: versions about 0.01% without a stage (1 / 10,703); sponsors about 0 unmatched (Aquino and Ward linked, via `OPEN-809`); Senate passage roll calls with no person votes about 0 (was 1,004 of 1,182); 14 committee votes flip pass → fail; action order newest-first no more; 0 "Reconsider:" prefix on the vote before |
| 4e | **NV** | `2025Special36,84` | sponsors 0 unmatched of 27; versions 237; versions named `^Amendment` 0; documents named `^Amendment` 26; no action text contains a line break; `2025Special36` 431 actions; `validate_bill_stages nv`: `passed_both_without_passed_one` 0, `no_mapped_action` 2 |
| 4f | **NM, OK 2025+2026, IA 2026+2025** | as already queued on v86 | **if v88 is live by then, they run on v88**, nothing else changes. Their pass/fail lines are in `a1c833f` and `07f2083` |

* **ME (`me-98110acf6911`, v86) finishes first.** Verify it as in `a92378e`. A second pass on v88 only per Decision 3 above.
* **Not part of 4:** Washington (its nightly), Hawaii twice, any second pass before Decision 3.

## Step 5: relabels, **dry run first**, commit on a second go
`os-text-extract relabel <st> --dry-run --list <file>`, at core `0d373728`, in the ddp-sync container. Report the exact summary lines and the list md5. Expected changes are the builders' measures on the replica; **I re-measure at `0d373728` and post any difference before you commit.**

| State | Expect | When |
|---|---|---|
| **OR** (OPEN-841) | 337 changed (`1803675`) | any time after Step 1 |
| **RI** (OPEN-822) | 2,222 lose `committee-failure` | **after RI's stale-document removal (Step 7)**; its re-import would also fix it |
| **ND** (OPEN-833, OPEN-858) | 438 gain `failure`, plus 82 gain `passage` (about 520) | any time after Step 1 |
| **ME** (OPEN-866) | about 5,177 (2,870 gain `passage`, 2,307 lose it) | after ME's v86 re-import is verified |
| **MT** (OPEN-826, 862) | about 62 gain `introduction`; "(LC) Draft Died in Process" 0 changes today | any time after Step 1 |
| **WY, HI, MO, KY** | **not needed:** their re-imports (Step 4) carry the labels | — |

## Step 6: recomputes, **dry run first**, commit on a second go (`recompute-diff-order <st> --dry-run --list <file>`)
Run after that state's re-import or relabel is verified, and after its stale-document removal where Step 7 lists one. **Never before a stale removal.**

| State | Expect (builder's measure) |
|---|---|
| **ID** (OPEN-834) | `not_a_version` 56, `corrected` 50, `nulled` 56 |
| **GA** (OPEN-842) | `corrected` 3, 0 nulled, no flag or baseline change |
| **NV** (OPEN-849) | `corrected` 32, `nulled` 26, flags changed 26, baselines 22/10/26 |
| **OR** (OPEN-846) | 433 / 432 / 201 (`1803675`) |
| **WY** (OPEN-835) | `not_a_version` 845 (840 amendment papers and 5 veto messages); each Enrolled's baseline = Introduced |
| **MT** (OPEN-827) | 60 comparisons change: 38 become empty, 22 shrink, none grow |
| **ND** | after Step 7's `refresh-extraction nd`; I post the range then |
| **MD, MS, HI** | I post ranges after measuring on the re-imported data |
| **MO** | `not_a_version` 700–800, `corrected` 420–510 (`c639029`; unchanged) |

## Step 7: text and archive (each on a go; dry run first)
* **ND (OPEN-836, before ND's public launch, Ramon):** `os-text-extract refresh-extraction nd`. Expect **1,431 changed, 1,259 unchanged, 0 errors**. Then the ND recompute dry run.
* **MD (OPEN-837):** after Maryland's archive, `refresh-extraction md`. Pass: chapter-law errors 743 → 0, and no cover-only rows left.
* **Stale archive rows (a rename leaves the old names behind): `remove-stale-documents <st>`, dry run, then `--commit --expect <stale> --list <file>`:**
    * **MS:** about 8,012 "Current version" rows;
    * **MD:** the rows under the old "First - <title>" names. **No deletion of the old Impact Note rows** (Ramon: leave them): if the dry run lists them as stale, report their count before committing;
    * **RI:** `stale=3011 removed=3011 kept_last_copy=0` (OPEN-665). After it, RI's relabel and its recompute.
* **Hold the recompute until the stale removal is committed** for those three states.

## Not authorized
* Any step before its go. Any recompute or relabel **commit** before the second go.
* Two heavy loads at once. A second run of any re-import before Decision 3.
* Hawaii twice. Wyoming twice. Missouri's #279.
* A re-import of NM, OK or IA beyond `a1c833f` / `07f2083`.
* Deleting any lock, S3 object or Redis key.
* Any manifest, schedule, routing or LegBot change beyond the LA/NE rollout in `df158e2`.
* Any certificate exception.

## If it goes wrong
* **Rollback:**
    * the scrapers image: register v86 (`ddp-scrapers:88`);
    * the core: re-tag the api-v3 and ddp-sync rollback images.
* A failed re-import leaves the state's earlier data in place until its load runs.

Tickets: OPEN-146; every fix ticket named above; OPEN-800, OPEN-803, SYNC-188, SYNC-189, OPEN-855.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
