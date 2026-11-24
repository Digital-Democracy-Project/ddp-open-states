# STATUS (not a request, not a GO): **v88 contents**, a running list. Refreshed 2026-11-24 ~15:00 UTC (Mac side, Onboard New States), after the PM session merged the review backlog. The release itself will be its own request note, on Ramon's go.

**Nothing for you to do from this file.**

## Baseline
* **Live now:** v86 = `ddp-scrapers:88` / `db:15`; EC2 api-v3 and ddp-sync at core `59dbdaa2`.
* **v87** (built, not yet rolled out) = `ddp-scrapers:89` / `db:16`: core `d5e548e8`, scrapers `b2d0d4db`.
* **v88 = a new build at current mains:**
    * **core `0d373728ff8fd18308a689542b0ded7ec7d11d8b`** (core main, after #156);
    * **scrapers `10e919d459a8c21276942d7c847c836c219d6999`** (scrapers main, after #278);
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

## In scrapers `10e919d4` (after v87's `b2d0d4db`)
| State | Tickets |
|---|---|
| HI | OPEN-823 (#266), OPEN-856 (#277), OPEN-868 (#278) |
| MO | OPEN-848 (#273) |
| KY | OPEN-852 (#274) |
| MS | OPEN-828 (#270) |
| MD | OPEN-832 (#271) |
| ME | OPEN-839 (#267) |
| MT | OPEN-851 (#275) |
| NV | OPEN-829 (#265), OPEN-830 (#269), OPEN-840 (#272) |
| WA | OPEN-853 (#276, 2027-28 scraped now) |
| (v87) WY | OPEN-820 (#264) |

* **Not in it:** scrapers **#268** (OPEN-825, Hawaii tallies), being re-based onto #277 now. **#279** (OPEN-869, Missouri journal chamber), which waits on Ramon's call about the "Message" lines.

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
