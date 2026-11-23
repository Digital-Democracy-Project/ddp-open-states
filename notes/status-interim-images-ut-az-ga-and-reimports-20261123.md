# Interim status (2026-11-23 05:35 UTC): next images, Utah and Arizona re-imports, US backfill, Kentucky recompute

None of these needs anything from you; each waits on an image or the core rebuild.

- **Images:** I have not seen v81 or any image after v80 registered. What I can read from ECS: scrape tasks run **ddp-scrapers:81** (v79) and the Rhode Island archive that started 04:50 UTC runs **ddp-scrapers-db:9** (your v80 db revision). I cannot read image tags or task definitions; tell me the tag and I will report the revisions when a new one is live. Nothing for **OPEN-775 Utah** (`21d55d4`, `d7ce0d8`), **OPEN-649 Arizona** (`fd0419f`, `753a793`), **OPEN-605 Georgia** (`2a19865`) or **OPEN-777** (`86a8109`) runs until their image is built.
- **Utah 2026 re-import (`d7ce0d8`), Arizona 57th-2nd-regular re-import (`753a793`):** not started; each also needs Ramon's go in my session after its image is live.
- **US vote-person backfill commit (15, OPEN-611):** waits for the core rebuild (your gate 3); I will report how many bills it marked updated if the image holds OPEN-777.
- **Kentucky `recompute-diff-order ky` (`22d7100` step 4):** dry run waits for the rebuild; not while a Kentucky scrape or archive runs (KY's weekly run is Sun 11-29 02:00 UTC).
- **Core rebuild:** waits for Oklahoma's archive (running since 01:01 UTC; 4.5 h so far). If it passes 6 h I will tell Ramon before deciding. Plan and your reply `5ae8ab35` are in `3cef331`.
- **Owed end reports:** Florida 2024/2025/2026, Michigan, Rhode Island rerun, Oklahoma, PA's embedding, smoke test and QA sweep.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
