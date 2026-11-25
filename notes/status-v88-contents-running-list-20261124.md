# STATUS (not a request, not a GO): **v88 contents**, a running list. Updated 2026-11-24 ~19:00 UTC: v89 = scrapers `b2aa844d` (#279–#283 merged), ddp-open-states `b7dbefb` (#485, #486 merged); the v89 request is `request-v89-release-backfills-reimports-mo-nv-al-ga-20261124.md`. Earlier: 2026-11-24 ~18:00 UTC (v89 section; #281–#283, ddp-open-states #485/#486 and OPEN-861's follow-ups added); refreshed 2026-11-24 ~15:20 UTC (scrapers main `0aba6be6`; the release request is `request-v88-release-core-0d373728-reimports-relabels-recomputes-20261124.md`) (Mac side, Onboard New States), after the PM session merged the review backlog. The release itself will be its own request note, on Ramon's go.

**Nothing for you to do from this file.**

## v89 is BUILT (checked on the Mac, ~21:00 UTC)
* **Tag `v89`, task revisions `ddp-scrapers:91` and `ddp-scrapers-db:18`**, core **`70146facdb8493d990415ee9deff19200c4e4777`** (core main: v88's `0d373728` plus #173, the Maine PDF reader), scrapers **`b2aa844d`** (#279–#283). I checked the local image: the core commit, Maine's `readers()` and the Missouri, Nevada, Georgia and Alabama changes are in it.
* **What is left is ONE core rollout at `70146fac`** (EC2 and Mac api-v3 at `254389aa`; EC2 ddp-sync at `eefb1ba`+ with `DDP_CORE_SHA=70146fac…` and `DDP_SCRAPERS_SHA=b2aa844d17973227fbe26659152e556e5cfe3fb8`). **It replaces the rollout at `0d373728`**: don't do two. Then the steps in `request-v89-release-…-20261124.md`, `e30bb8e` and `update-run-reimports-in-parallel-…`.

## v88 is BUILT (checked on the Mac, ~20:30 UTC)
* **Tag `v88`, task revisions `ddp-scrapers:90` and `ddp-scrapers-db:17`**, core `0d373728ff8fd18308a689542b0ded7ec7d11d8b`, scrapers `0aba6be6`. I checked the local image: `DDP_CORE_COMMIT` is `0d373728`, and the fixes for HI, MO (#273), KY, MS, MD, ME, MT, NV (#265, #269, #272), WA and WY are in it. **#279–#283 (Missouri journal chamber, Nevada results, Georgia and Alabama numbers) are not**: they are v89.
* **What is left for v88 is the core rollout at `0d373728`** (api-v3 on both hosts at `254389aa`, ddp-sync at `eefb1ba`+; `e30bb8e` step 1 and `7d4793f`), and then everything downstream. **Nothing waits for a v88 build.**
* **The image still to be built is v89** (scrapers `b2aa844d`).

## Baseline
* **Live now:** v86 = `ddp-scrapers:88` / `db:15`; EC2 api-v3 and ddp-sync at core `59dbdaa2`.
* **v87** (built, not yet rolled out) = `ddp-scrapers:89` / `db:16`: core `d5e548e8`, scrapers `b2d0d4db`.
* **v88 = a new build at current mains:**
    * **core `0d373728ff8fd18308a689542b0ded7ec7d11d8b`** (core main, after #156);
    * **scrapers `0aba6be6631b4bb97ab2a83719661bcd449be707`** (scrapers main, after #268);
    * **ddp-open-states main** for the manifest, and **people main `37bcb364`**.
* **v88 supersedes v87:** `0940569`'s v87 rollout at `d5e548e8` is then unnecessary. One core rollout at `0d373728` covers it, and v88 carries everything v87 does. **Ask Ramon whether to skip v87's rollout and go straight to v88.**

## In core `0d373728` (after `d5e548e8`: 23 merges, no migration)
| State | Tickets |
|---|---|
| OR | OPEN-841, OPEN-846 |
| ND | OPEN-833, OPEN-858 |
| WY | OPEN-821, OPEN-835 |
| RI | OPEN-822 |
| HI | OPEN-824, OPEN-856, OPEN-867 |
| MO | OPEN-831, OPEN-857 |
| KY | OPEN-844, OPEN-845 |
| ID | OPEN-834 |
| GA | OPEN-842 |
| NV | OPEN-849 |
| MD | OPEN-837 |
| MT | OPEN-826, OPEN-827, OPEN-861 (hidden drafts, with api-v3 #78), OPEN-862 |
| ME | OPEN-866 |

## In scrapers `0aba6be6` (after v87's `b2d0d4db`)
| State | Tickets |
|---|---|
| HI | OPEN-823 (#266), OPEN-825 (#268), OPEN-856 (#277), OPEN-868 (#278) |
| MO | OPEN-848 (#273) |
| KY | OPEN-852 (#274) |
| MS | OPEN-828 (#270) |
| MD | OPEN-832 (#271) |
| ME | OPEN-839 (#267) |
| MT | OPEN-851 (#275) |
| NV | OPEN-829 (#265), OPEN-830 (#269), OPEN-840 (#272) |
| WA | OPEN-853 (#276, 2027-28 scraped now) |
| (v87) WY | OPEN-820 (#264) |

* **Not in it:** scrapers **#279** (OPEN-869, Missouri journal chamber), which waits on Ramon's call about the "Message" lines.

## Other repos (merged; their own steps)
* **ddp-open-states:**
    * #483 (OPEN-855, unmatched-voter check) and #481 (OPEN-847, govbot session map);
    * #478 (SYNC-188 scrapers-commit line), #482 and #484 (docs);
    * #465 and #466 (NE and LA live), #479 (MD officers).
* **ddp-sync:** #308 (OPEN-855 alert): rebuild EC2 ddp-sync after #483 is pulled onto the host.
* **api-v3:** #78 (OPEN-861 hidden drafts): rebuild api-v3 with core main.
* **people `37bcb364`:** #50 (NE Meyer), #51 (KY "Lewis C"), #52 (ME CI check).
* **broker:** #820 (BROKER-588, Idaho scorecard rules) merged: `/broker-deploy`, then backfill, validate (list approved by Ramon).

## What each state needs after the v88 release (I'll write the per-state steps into the release request)
* **Re-import:**
    * **HI** (once; after #268), **MO**, **KY** (people load first), **WY** (once), **NV** (both sessions), **ME** (already queued on v86; its labels need a relabel or a later re-import), **MD**, **MS**.
* **Relabel or recompute, dry run first:**
    * `relabel`: hi, mo, nd, or, ri, wy, me, mt, ky;
    * `recompute-diff-order`: id, ga, nd, nv, or, mt, md, wy, ms.
* **Archive:**
    * `refresh-extraction`: nd, md (chapter laws), mt (cleaner);
    * `remove-stale-documents`: ms, md, ri.

Tickets: OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>

## v89 (next image; not in v88 `0aba6be6`)
| Merge | Ticket | What | After it |
|---|---|---|---|
| scrapers #279 → `85d9ce59` | OPEN-869 | Missouri actions filed under the chamber whose journal records them (Ramon: yes) | **Missouri's single re-import, then its relabel and recompute dry runs** (`c93134c`) |
| scrapers #280 (open, head `3e42f808`) | OPEN-865 | Nevada vote result from NELIS: "Passed No" and "Rescinded" give fail; a rescinded vote loses its passage label and keeps its tally. 3 stored votes change (AB 5, SB 10, AB 4) | **Nevada's re-import runs once on an image with it** (without it, a re-import writes the old results back); a ddp-open-states fix-up for the 3 stored votes is being built; broker #824 waits for it |
| scrapers #281 (open, head `9fc2acb61`) | OPEN-864 | Georgia: each vote's roll-call number stored under the same extras key Louisiana and Alabama use; orders all 13 same-day ties in `2026_ss` (checked against the legislature's own times) | The 26 stored votes get fixed by a ddp-open-states PR (State Specific Handling) adding Georgia to `backfill-vote-rollcall-num.py`, so **no Georgia re-import is needed for this** |
| scrapers #282 (open, head `625f1a1ae`) | OPEN-863 | Alabama: each vote stores ALISON's roll-call number under `house-rollcall-num` / `senate-rollcall-num` | The 2,550 stored Alabama votes carry no number; State Specific Handling adds Alabama to the same backfill PR as Georgia, so **no Alabama re-import is needed for the ordering** |
| scrapers #283 (open, head `1746df7bb`) | OPEN-863 | Alabama: a "motion to adopt" right after an "Amendment/Substitute Offered" row, same chamber and day, is labelled `amendment` (affects HB 605 Senate and SB 146 Senate; HB 201 stays passage) | Takes effect on Alabama's next weekly run on an image with it; or a relabel dry run, if needed |
| ddp-open-states #485 (open, head `5c53c3f7`; State Specific Handling) | OPEN-865 | Fix-up for Nevada's 3 stored votes (AB 5, SB 10, AB 4): `backfill-motion-classification.py --nv-result` with the reviewed list `notes/open865-nv-vote-result-dry-run-20261124.csv` (md5 `125ccbe0ef24fb1b170205fa3a5e2dce`). It needs `--expect 5` (one list row per column changed). It has `--undo` and deletes nothing. Its tests import #280's parser, so #280 merges first | After an image with #280: the apply, on Ramon's go; then a replica dry run expecting 0 left. **Broker #824 (Nevada's scorecard) waits for it.** |
| ddp-open-states #486 (open, head `0218aab`; State Specific Handling) | OPEN-864, OPEN-863 | One backfill for Georgia and Alabama roll-call numbers: extends `backfill-vote-rollcall-num.py` (no new script). **Georgia:** 280 stored votes (all `2026_ss`) get the number from the identifier, incl. the 26 votes of the 13 ties; apply `--apply-list <list> --expect 280`. **Alabama:** 2,550 stored votes get it from the dedupe key, incl. the 3 same-day pairs; apply `--apply-list <list> --expect 2550`. The lists are deterministic, with md5s in the PR. A stored number is never changed; `--undo` and all-or-nothing as before; a second dry run must plan 0. It writes the same keys as #281 and #282 | The applies, on Ramon's go, in the prod agent's session. **No GA or AL re-import is needed for the ordering.** |

### Montana drafts, OPEN-861 follow-ups (Ramon: "LegBot may cover drafts, drops them once introduced"; none merged)
**Correction to my earlier statement:** LegBot's artifact scan **already** sends `bill_types_only` (SYNC-165), so api-v3 #78 (already in the v88 request at api-v3 main `903013d`) covers it. The readers that did not filter were ddp-sync's **knowledge-base embedding reads** and the **sitemap**.

| PR | Ticket | What | Release |
|---|---|---|---|
| api-v3 #79 (**merged `26650baa`**, lint fix #80 `254389aa`) | OPEN-870 | new switch `exclude_introduced_drafts` on `/bills`, `/ddp/search`, `/suggest`, `/hydrate`, `/ddp/sitemap/bills`, `/ddp/embedding/ledger`; `bill_types_only` unchanged and implies it | rebuild api-v3 on each host with core `0d373728`+ (no schema change) |
| broker #827 (**merged `ac13ac7b`**) | BROKER-597 | the sitemap read sends the switch (not `bill_types_only`) | `/broker-deploy` (broker request `e472203f`, D3); the sitemap list is cached for an hour |
| ddp-sync #309 (**merged**, main `eefb1ba`) | SYNC-190 | the two knowledge-base reads send the switch; the artifact scan is untouched | rebuild ddp-sync (needs #79 live) |
| ddp-sync #310 (head `6cabf4d`, contains #309) | SYNC-191 | `POST /trigger/knowledge-base-draft-cleanup/{jurisdiction}?dry_run=true`: compares the ledger with and without the switch, deletes drafts' vectors by exact id (the SYNC-95 code) and empties their Redis record on apply; refuses more than 200 documents; never touches bill data or the broker's `BillArtifact` rows | after #309; **the prod agent runs it on Ramon's go: dry run for `mt` first (it should name LC 858 only if it was ever embedded), then `dry_run=false`; Montana must be in `enrollment.embedding`, or it answers 404** |

* **LC 858** = `ocd-bill/4dffc95d-382a-4813-a0f8-247fe430711f` (Montana 2027; SB 33 replaces it). Until #78 and #79 are live, every api-v3 read still returns it.
* pm-review rated #310 high-risk on two concurrency points (the two ledger reads aren't one snapshot; a live writer race). The worst case is a re-embed, never lost bill data. **Ramon may want to judge it.**

### Maine archive reader (OPEN-871; found after Maine's re-import)
| PR | Ticket | What | Release |
|---|---|---|---|
| core #173 (open, head `f5178560`; CI `build` SUCCESS, MERGEABLE, CLEAN) | OPEN-871 | Maine had no PDF reader (upstream says `DoNotDownload`), so its archive fetched nothing (0 documents for 5,131 versions). `ddp_states/me.py` `readers()` reads Maine PDFs with `read_without_struck_text(extract_sometimes_numbered_pdf)` (the wrapper GA, LA, NC, NE and NV use). Measured on 21 real Maine PDFs; the reader table differs for exactly one entry among 53 states | after merge: **a new scrapers image with this core (the archive runs in the image)**, a core rollout, then a Maine archive run (expect about 5,131 documents, non-zero `fetched` and `archived`); then a `recompute-diff-order me` dry run (expected to need none) |

### Scorecard-rule scrapers changes (Ramon's rule, 11-24: every full up-or-down roll call counts; the latest replaces earlier ones)
| PR / ticket | State | What | Release |
|---|---|---|---|
| scrapers #284 (open, head `007adc99`; State Specific Handling) OPEN-876 | Nebraska | YAML only, in the `ne` block: advancement roll calls count. Nebraska already stores 470 of them (the readings audit's "none stored" was wrong). Counted votes **372 → 412** (40 newly counted) | **Ramon approves the new list**, then a new image and **one Nebraska re-import** (`ne?full=true&sessions=109`); broker #465's rules follow the list |
| scrapers #285 (open, head `1811898ab`; State Specific Handling) OPEN-874 | Wyoming | earlier-reading roll calls (139 bill-chambers) and whole-bill veto overrides only. Counted bill-chambers **276 → 415**; the 3 failed whole-bill overrides replace those chambers' concurrence votes (**Ramon to confirm**) | a new image carrying #285 with the earlier Wyoming fixes, then **one** Wyoming re-import (held, `e613948`); blocks BROKER-589 |
| scrapers #286 (open, head `500db139d`; State Specific Handling) OPEN-875 | Utah | second reading counts: exactly **16 Senate bill-chambers in 2026** start counting, none stops | **Ramon approves the list**, then one Utah re-import on the image that carries it. **Utah is already switched on**, so its scorecard backfill, chain and validators wait on his go again |
| scrapers #287 (open, head `42b84240`; lint SUCCESS; mine) and ddp-open-states #487 (open, head `010292f8`; no CI exists; mine) OPEN-872 | Oklahoma | #287 stores oklegislature.gov's "RCS#" as `house-rollcall-num` / `senate-rollcall-num` (the same keys as LA, MI, WA, AL, GA). #487 extends `backfill-vote-rollcall-num.py` with `ok`, reading it from the stored dedupe key: 8,767 votes (house 5,125, senate 3,642), `--expect 8767`, list md5 `ce1039b50c43c9a00d3259731c690551`; 12 same-day pairs of passage votes (11 in 2025, 1 in 2026) | #287 in the next image; then **either** Oklahoma's re-import writes the numbers **or** the #487 apply (`--dry-run --jurisdiction ok --list`, compare, `--apply-list … --expect N`) before it; a second dry run plans 0; `--undo` reverses. BROKER-591 (#829) then re-measures; it blocks BROKER-591 |
| scrapers #288 (open, head `11e3e164`; lint SUCCESS; mine) OPEN-873 | Rhode Island | the Senate prints bills in forms the scraper didn't read, so 20 Senate roll calls in 2026 were dropped, including **14 on HB 7127** (the budget: 12 amendment votes, a consideration vote 31-7, Passage 32-6); calendar items "read and passed" with no motion line (**7 in 2026**, not 6) weren't labelled passage. Fix: a fallback bill-number reader (used only when the two existing ones find nothing) and a calendar item takes its own marker as its motion; no names or bill numbers in code | a new image, then a **Rhode Island full re-import, 2026**. Expect on the replica: vote events **1,433 → 1,453** (Senate 779 → 799), passage **1,311 → 1,320**, amendment 100 → 113, person votes **78,652 → 79,412** (+760), HB 7127 Senate roll calls 0 → 14, unresolved voter names 0. All 1,433 earlier roll calls keep their key, bill, chamber, counts and voter count; 7 change motion and label. Blocks BROKER-590 (re-measure after) |

## v90 (scrapers `89e390d1`, core unchanged `70146fac`) — request `85ce7f0`, 11-24 ~21:15 UTC
All merged and checked on GitHub 11-24: scrapers #284 NE (3f77e9d3), #285 WY (89e390d1), #286 UT (6b210849), #287 OK roll-call number (33e01186), #288 RI Senate roll calls (6b2d2276); ddp-open-states #487 OK backfill (3d1801a4); people #53 NE note (26f4ad0d). Broker #830 KY (a4ef6d2c, 0117) and #828 WY (c6b6253d, 0118) are merged (the Broker Upgrades session releases them).
* **Image:** not built yet (Ramon builds on the Mac). Then one re-import each: WY 276→382, NE 372→412, UT +16 Senate bill-chambers, OK (numbers on 8,767 votes; after its current 2026 run), RI full 2026 (HB 7127 Senate roll calls 0→14). NE people fast-forward first (0 created, 1 updated).
* **Optional:** OK backfill dry run, expect 8,767, md5 `ce1039b5…`, then `--expect 8767` on a second go.
* **Open for Ramon (not for me):** RI header-shape question (S 2067 ×2, Senate H 7165).
* **Live right now (not v90):** core `70146fac` on EC2 api-v3 and ddp-sync since 20:15 UTC; OK 2025 verified (`0beadee`); ND/RI dry runs match (`64557d1`); Maine archive running since 20:31 UTC (ddp-scrapers-db:18).

## v91 (scrapers `261cae78` = v90 + #289 RI header rule; core unchanged `70146fac`) — ddp-scrapers:93 / ddp-scrapers-db:20, built 11-24 evening
* **Read on the Mac:** `DDP_CORE_COMMIT` `70146fac`; #284–#289 present. **No stored RDS secret** (`TASK_RDS_*` not set for this run); both plain API keys copied forward on `db:20`.
* **Rhode Island's re-import can run on v91** (once): HB 7127 Senate roll calls 0→14, the 3 header-shape roll calls labelled passage, passage events about 1,323 (prediction). Update note posted at the same time as this line.
* **Arizona canary blocked** until a v92 build with `TASK_RDS_*` set (main's script has no register-only mode); OPEN-880 (#490, secrets cleanup) rides after that.
* **Done since the v90 section:** WY, MO, ME archive, ND text/recompute/relabel, ME relabel, OK roll-call backfill (8,767) all verified on the replica; HI found with 4,795 unmatched votes (OPEN-879, builder running).

## OPEN-879 merged, v92 planned (11-25 ~00:40 UTC) — request in `request-v92-release-…-20261125.md`
* **Merged:** core #174 (a7035d68), scrapers #290 (79c25838), people #54 (c59386b9). Core main is now `a7035d68d1344f99783042e2492ba120d110e603`; v90/v91 carry `70146fac`.
* **v92 = scrapers `79c25838…` + core `a7035d68…` + the `TASK_RDS_*` secret release.** Then ONE core rollout (EC2 api-v3 + ddp-sync, Mac api-v3 Ramon's), the hi people load (0 created, 1 updated), the second Hawaii re-import (Ramon's new go; 178 unmatched expected before the re-scrape, only "Garcia; and" after), then the Arizona canary.
* **Any time:** RI re-import (v91+), OK 2025+2026 after its archive.

## v92 built (11-25 ~01:10 UTC) — ddp-scrapers:94 / ddp-scrapers-db:21, core `a7035d68`
* **Read on the Mac:** `DDP_CORE_COMMIT` `a7035d68…`; #174, #289, #290 in it. **No stored RDS secret again** (`TASK_RDS_*` not set), so the secret half needs a further build, **v93**, same code.
* **Mac api-v3** on `a7035d68` (Ramon ran the refresh). **EC2 api-v3 and ddp-sync: core rollout still owed** (no longer waits for the secret).
* **Order:** core rollout → hi people load → second Hawaii re-import (Ramon's go) → v93 with `TASK_RDS_*` → canary (#488) → OPEN-880 (#490). No core merges before v93.
* **Verified on the replica since v91:** NE v90 re-import (412, 0 unmatched of 86,723), IA 2026 (1,912 bills, 0 unmatched of 51,044; the `2026s1` question is open), ND/ME relabels, OK 2025 timeout noted (retry once after 2026).

## Ramon's answers relayed 11-25 ~01:30 UTC (PM session pop-ups; the prod agent confirms with him in its own session)
* **Second Hawaii run: YES** ("Yes, run Hawaii again"): after the core rollout at `a7035d68` and the hi people load, one more full Hawaii re-import on v92 rev 94 or later. He gives the go in the prod session.
* **Scheduler work, "File all three, archive record first":** SYNC-192 (archive task in the in-flight record), OPEN-881 (unmatched-voter check as a launched task), OPEN-882 (weekly people-refresh runner, D3), all related to OPEN-633, built one at a time in that order (SYNC-192 blocks OPEN-881). The PM merges ddp-sync PRs only after the core rollout; no core/scrapers merges before v93. Nothing deploys without his go.

## v93 built (11-25 ~03:10 UTC) — ddp-scrapers:95 / ddp-scrapers-db:22, core `a7035d68`, **stored RDS login on db:22**
* **Read on the Mac:** core `a7035d68`; `apply_rds_task_secret` in the image. Ramon's output: RDS entries set on `ddp-scrapers-db`, none on `ddp-scrapers`.
* **Container with both present:** a launcher-passed `DATABASE_URL` always wins; the secret is not used. The real test is ECS reading the secret before start (the first launch from `db:22`).
* **Left:** names-only read-back of `db:22` (and none on `ddp-scrapers:95`); the first launch from `db:22` RUNNING and exit 0 (rollback: deregister `db:22`); ddp-sync restart with the core rollout (staged); HI people load and second re-import; the Arizona canary (#488) after a clean first launch; Ramon deletes `/tmp/taskdef-*.json` and rotates the two keys (OPEN-880, #490).
* **Open PRs:** ddp-sync #312 (SYNC-192, archive in-flight record; merge after the core rollout); #488 (canary manifest); #490 (OPEN-880). Builder running on OPEN-881 (unmatched-voter task), then OPEN-882 (people refresh runner).

## v93 step 1 COMPLETE (11-25 ~01:05 UTC; prod agent notes `bd25b25`, `1432dc5`, names only)
* `ddp-scrapers-db:22`: secrets RDS_USERNAME, RDS_PASSWORD; environment RDS_HOST, RDS_DBNAME, RDS_PORT (plus the two plain API keys, OPEN-880). `ddp-scrapers:95`: none of the five. RI's archive launched from `db:22` and exited 0.
* **Arizona canary still needs:** #488 merged (the PM, on Ramon's OK), the ddp-sync restart onto core `a7035d68` (waiting for the HI archive; brings #311's flag), and Ramon's go for the manifest rollout. Then the pass rules in `d8df145`.
* **Verified on the replica this stretch:** RI v92 re-import (1,323 passage, HB 7127 Senate 14, 0 unmatched of 79,412), OK roll-call numbers, HI people (Lee, C alias), NE, MO, WY, ND/ME relabels.

## v94 built (11-25 ~02:00 UTC) — ddp-scrapers:96 / ddp-scrapers-db:23, core `a7035d68`, ddp-open-states main `d082f4dd`
* **Read on the Mac:** `DDP_CORE_COMMIT` `a7035d68…`; `/app/cloud_unmatched_voters.py` (OPEN-881, #491) and `/app/cloud_people_refresh.py` (OPEN-882, #492) are in the image; `qa_primitives.unmatched_voters_result` is there; `os-people` present. Scrapers main still `79c25838`. Ramon's output: RDS entries copied forward from `db:22` (none on `ddp-scrapers`).
* **Runner-first condition for OPEN-881 / OPEN-882 is met** once v94 is the live latest revision (it is; new launches use it). The ddp-sync side (#312 → #313 → #314) still merges after the core rollout; both `on_fargate` settings default off.
* **Still queued:** the ddp-sync restart onto core `a7035d68` (held by the HI archive), the second Hawaii re-import, the Arizona canary (#488), the Oklahoma 2025 retry, RI recompute/relabel dry runs.
