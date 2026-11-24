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
| OPEN-874 (State Specific Handling; building) | Wyoming | earlier-reading roll calls (139 bill-chambers) and whole-bill veto overrides only | a new image and **one** Wyoming re-import (held); blocks BROKER-589 |
| OPEN-875 (State Specific Handling; building) | Utah | second reading | an image and a Utah re-import |
| OPEN-872 (mine; building) | Oklahoma | store each vote's roll-call number | an image, the backfill if needed, an Oklahoma re-import; blocks BROKER-591 |
| OPEN-873 (mine; building) | Rhode Island | the missing Senate roll calls (HB 7127) and six title-only roll calls | an image and a Rhode Island re-import; blocks BROKER-590 |
