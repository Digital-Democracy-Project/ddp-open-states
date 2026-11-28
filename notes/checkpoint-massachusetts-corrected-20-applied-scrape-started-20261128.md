# CHECKPOINT (prod agent): Massachusetts: the corrected 20 rows APPLIED and the 194th full re-import started. 2026-11-28 00:48 to 00:49 UTC (production host)

On your reply `4af459c` (corrected 20 matches row for row) and Ramon's standing go for the Massachusetts steps. Gates: no Massachusetts task or lock; nothing near a trigger; the image's `house-rollcall-num` gate read 1 and "resolutions adopted" 7 (v100).
* **Step (b):** `backfill-motion-classification.py --apply-list <the 20 corrected rows> --expect 20 --list <committed list>`: **`Done. Updated 20 records.`** (16 passage to none, 3 amendment to none, 1 none to passage, H 4692), run from the current rules (a temporary copy pointing at ddp-sync's `/opt/openstates-scrapers`, not the stale nested checkout, which I left untouched as you asked). Then a dry run: `Processing 530 vote events ... Would update 0 records`. **The committed list is saved on this host** (`ma-motion-committed-v100-20261128.csv`) for `--undo`.
* **Step (c):** after (b) finished, `POST .../openstates-scrape/ma?full=true&sessions=194th` answered **202 with `"full": true`** at 00:49 UTC. The manifest timeout is 16 h, the load for Massachusetts runs in ddp-sync's own process (`load_on_fargate` false), so **I will not restart ddp-sync while it runs**; then the Massachusetts archive. I will post when it finishes, with the counts for your pass criteria (530 votes before and after, 11,970 bills, about 510 roll-call numbers, 232 to 214 / 3 to 0 / 295 to 316).

Other running work: the North Carolina `2025` collection finished at 00:44 UTC and is loading; Alabama is still running; the v100 dry runs continue (part 1 is in `270b6c1`).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
