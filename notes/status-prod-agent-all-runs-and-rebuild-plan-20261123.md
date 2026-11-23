# STATUS from the prod agent, 2026-11-23 04:45 UTC: what is running, what is done, and the core rebuild plan (answers all open requests; read this first)

Every action below was on Ramon's go in my session unless it says otherwise.

## Done since your last read of my notes
- **PA go-live (`945ce66`): DONE as part of one rollout.** EC2 checkout is `f0cfd9c7a` (#458 PA live, #461 ID scraping, #467 WY scraping, #464 docs). pa: live, search_refresh, embedding, api_smoke_test, qa_sweep true. **Ramon waived your "pa must be idle first" gate:** pa's 04:00 UTC nightly (revision 81) was still running at 04:26 UTC. The nightly's embedding step may now run with the new flags; I will report PA's first embedding, smoke test and QA sweep. Details in ddp-sync `41e6ca9`.
- **First scrapes started on rev 81 (v79):** Idaho `id-2a1021ebee6f`, Wyoming `wy-d64df4852faf` (04:26 UTC); **Rhode Island rerun** `ri-397bc21f0bff` (04:15); **Michigan full run** `mi-b8b23c2b5df9` (04:24, open-states `afa4cc05`). All in parallel with Florida's re-run of 2024/2025/2026 (00:49), Oklahoma's archive, and the PA nightly.
- **Earlier today:** ND rerun and KY first scrape completed (`dcbd313`); RI first run failed on a repeated bill (`9b21ebe`); Washington re-import done (`123b4f3e`); Florida re-import 6 of 9 sessions (`f47317d7`); OPEN-611 dry runs (`2d4e5a8f`); broker 36e0bb51 live (broker `3ae4822f`).

## Requests I had missed until 04:35 UTC (my fault: I had moved my read marker to my own commit)
- `994956e` Wyoming: **started** (above). `945ce66` PA go-live: **done**. `df508b7` NE and LA before go-live: **not started**; gate G1 (api-v3 and ddp-sync at core `42b48982`) is not met yet, see below.

## Core rebuild: Ramon said "rebuild once the Oklahoma archive finishes" (11-23)
- **Plan, in your `a9fbb18`/`22d7100` order:** (2) api-v3 on EC2 rebuilt with `DDP_CORE_SHA=42b48982c3378c84f6c549ac9ac37be12bdbf2ae`; (3) EC2 ddp-sync fast-forwarded from `becbceb` to `b569cf2` (SYNC-185 + SYNC-186; first-parent gap is exactly #303 and #304, G1 of `9825134` met; part 1 list = 13 states, `92b3d562`), tagged `ddp-sync:pre-b569cf2`, rebuilt at the same core; then `check-core-pin-drift.py --image-core 42b48982...` must exit 0.
- **Restart effects, from my 11-20 read of ddp-sync's code** (collection and load of every in-flight Fargate job resume from redis with a fresh wait; the archive, search/embedding/LegBot hand-offs, archive retry loops and later sessions of a multi-session pipeline do NOT): I expect the rebuild to cost **the archive step of any run that has not reached it** (mi, ri, id, wy, and pa's tail) and, **Florida's 2025 and 2026 sessions** if the restart lands during 2024. I will list each and tell Ramon before I re-trigger anything. Ramon knows this cost.
- **Please confirm in a note** that none of the running scrapes (mi, ri, id, wy, ok, fl, pa) needs core `42b48982` in the loader to load correctly. Your notes say so for id, wy, ri; I have no explicit statement for mi, ok, fl, pa.
- **After the rebuild** I will post a checkpoint and then wait for your GO notes for: NE/LA part A (people), KY `recompute-diff-order ky` dry run (your `22d7100`, its own go), NC Tillett relink, and the Arizona re-import (needs the image after v79). Nothing of those is started.

## Still owed from me
End reports for id, wy, mi, ri, fl, ok; broker `36e0bb51` Stage 5 after the 05:00 UTC chain; PA embedding/smoke/QA. Open and held: AGENTS-225 pilot (MLX), Virginia LegBot (Ramon stopped it for MLX tests).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
