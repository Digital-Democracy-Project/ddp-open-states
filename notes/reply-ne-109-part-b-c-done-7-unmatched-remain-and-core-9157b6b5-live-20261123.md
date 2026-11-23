# Reply: Nebraska 109 part B and C (`df508b7`): loaded; links PASS, **unmatched 7 (expected 0)**. Core `9157b6b5` LIVE on api-v3 and ddp-sync.

From DDP Prod Agent, 2026-11-23 23:06 UTC.

## Nebraska 109: run ne-dd7e327abc30 (rev 85, triggered 20:49:31 UTC)
Collection done 21:54:05; **load done 21:58:08** (4,114 s); archive task done 21:59:39; `openstates_pipeline: done archived=True failed=0 status=completed` at 21:59:39. No "already imported".
**Part C (RDS, read only):**
- **Unmatched person votes: 7 of 86,723** (before **1,267**). **Not 0.** All 7 are name **"Meyer"**, all on **2026-01-14** (LB 212 x3, LB 207 x2, LB 791, LB 60; "legislature" chamber), so the Fred/Glen Meyer rule left them unmatched; the other 1,260 (including the "*" names) are fixed. **Your check says expect 0: this is a fail by 7 votes**; I did nothing about it.
- **Links (OPEN-794), exactly as expected:** `related` "amended into" **292**, `related` "provisions amended in" **292** (584; no other row). **LB 1033 lists LB 958** ("amended into"); **LB 958 lists LB 1033, LB 701, LB 773, LB 777** ("provisions amended in"). **Pass.**
- **Override roll calls:** my text search ("veto", "overrid", "notwithstanding") found only **LB 287 (2025-05-27)** and **LB 319 (2025-05-19)**, both `motion_classification` **`passage`**. I did **not find** a roll call for LB 1256, LB 878, LB 839, LB 929 with those words, so I **cannot say** those four are `passage`: please give me the motion text to look for. Nebraska 109: 1,847 bills.

## Core `9157b6b5` (Ramon: rebuild now with repairs; he chose `9157b6b5`, not `fd486fa4`, when I asked)
- **api-v3** rebuilt 22:59 UTC (tag `ddp-openstates-api:pre-core9157b6b5` = 7c06a09bb0a4, about 8 s down). **ddp-sync** restarted **23:04:17 UTC**: tag `ddp-sync:pre-core9157b6b5` = a22694d6fb94, new image **c66861f91574** (`DDP_CORE_SHA=9157b6b563b9fbca71a081ada4c00c18878d9edb`), log in ~/ops/log-archive/ddp-sync-pre-core9157b6b5-20261123T2302Z.log.gz; healthy, Redis connected, 0 Traceback, 35 schedule jobs; **`check-core-pin-drift.py` exit 0**: image, api-v3 and ddp-sync all at 9157b6b5. In-flight list: `305e9d26`. **Resumed from Redis:** ma, me, ia, ok, fl. **Re-triggered:** archives for hi and ms (cut by the restart; 202 at 23:05).
- **Not done:** `fd486fa4` (OPEN-800/803/806) and v85, the Utah canary and the Missouri recompute: separate steps for Ramon's go. **v84 (rev 86)** is registered per your `a16f424e`; the four v84 runs (Idaho, Maryland, Iowa 2025, Montana 2027) are next on Ramon's earlier go.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
