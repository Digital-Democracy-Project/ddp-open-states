# REQUEST (not a GO): **Idaho: the struck-text refresh and the recompute, dry runs first (OPEN-895).** Everything they need is now in place. 2026-11-27 ~00:30 UTC (Mac side, Onboard New States)

**Not a GO.** Ramon gives each go in your session naming this note. This replaces "Parts 3 and 4" of `request-v97-scrapers-image-idaho-…` (b8210af); nothing else in that request changes.

## What is now true (your notes)
* Core `647bb399` (openstates-core #176, Idaho's strike-line reader) is in image v97/v98 and live on api-v3 on both hosts and on EC2's ddp-sync (`bd5c9c0`, `31e935a`, `7cd9feb`). Idaho's manifest is live since 11-25.
* Measured on the Mac replica's local archive copy: **438 of 924 Idaho 2026 documents (427 versions) lose struck text; none gains a character; 0 errors.** Only Idaho's reader changed across all 131 states.

## What I need from you (each step stops at a dry run; the commit holds until a go note)
1. **Gate:** no Idaho task in flight and no ddp-sync job in the last 10 minutes; record "now" as the restore point; confirm the code that will run is core `647bb399` (show me the commit).
2. **`os-text-extract refresh-extraction id` as a dry run.** Expect **438 changed, 486 unchanged, 0 errors**. Report the exact lines; **do not commit**. **If this role cannot run it (it needs the archive and core on a host you can reach), say exactly what it needs and I will ask Ramon**; do not improvise a scrape or a re-import.
3. **On a go note: the refresh commit.** Report the counts; I verify on the Mac replica that H 561 reads "(b)" where it read "(c) (b)", the struck "(h) Official flags of Idaho colleges, universities, and public schools" is gone, H 570's struck ", or" is gone, and no unrelated Idaho text changed.
4. **`recompute-diff-order id --dry-run`** (after the refresh commit; the comparisons change). Report the exact lines; **do not commit**; the commit holds until a go note. I read the same dry run on the Mac side.
5. After the recompute commit, tell me; I re-run Stage 3 and the Idaho dev LegBot sample through `/onboard-state` (H 570 and H 561 included).

## Not authorized
A scrape or re-import; any other state's refresh or recompute; a manifest change; Idaho `replica_routing` or `legbot_replica` (they stay false until its sample passes); a ddp-sync restart; any commit before a go note.

Tickets: OPEN-895; OPEN-664 (Idaho); OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
