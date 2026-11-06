# Status (no reply needed): where the production host stands after the three recomputes (OPEN-494, OPEN-495/496/497). 2026-11-06, about 21:50 UTC

Reply to nothing; this lists what I have posted, what is running, and what I still owe, so nothing has to be pieced together from the other notes. Nothing here changes anything.

## Done and posted
- **Pennsylvania nightly (OPEN-494, OPEN-478):** ddp-sync `11cd64e` and ddp-open-states `a2b4180f` on this host; ddp-sync restarted 20:02:27 UTC, healthy; `openstates_primary_scrape_pa` next run 11-07 04:00 UTC; `pa` out of the Sunday list. Notes: ddp-sync `74ff882`, `66f71c0`, `015e50c`. The ddp-open-states tip (`46065175`, with OPEN-495's `clean_pa_text`) is **not** pulled; it waits for your separate note.
- **Recompute, all three committed and verified by you:** NE `8f68d9d2` (21:36:49 UTC), LA `af8a0c4c` (21:40:09), PA `7264d596` (21:44:40). Whole table 224,167 documents, flags set 73,120. Dry runs `bde791c8`. No further recompute run.
- **Certificate (BROKER-430, BROKER-326):** catch-up tests `d7b7e018`; the renewal cron entry installed at 21:4x UTC (`12d59757`).
- **Deploy `d5586c61`** is live with Voatz off (broker `56533868`).

## Running now
- ddp-sync container up and healthy since 20:02:27 UTC. No ECS task running at the last check (21:49 UTC).
- A background watcher wakes at **04:03 UTC** to capture Pennsylvania's launch.

## Still owed from me
1. **Pennsylvania, tonight 04:00 UTC:** the launch reply (task id, and which image revision it runs: v45 / revision 47 expected, read from the launch since I cannot read task definitions), a report at about 3 h, and the end report (exit code, bills / vote events / person votes against 5,270 / 5,858 / 425,560, any 429, 403 or block, RDS CPU and connections, overlap with other jobs). If it fails or stalls I stop and report; I do not retry. At the end I also read how many Pennsylvania vote events carry a `motion_classification` other than empty or `amendment`/`reading-3` (the before picture is 953 `{passage}`).
2. **First scheduled certificate renewal run, 11-07 after 09:17 UTC:** time, "Nothing to install", exit 0, hashes identical.

## Not authorized, not started
`recompute-diff-order all`, `ma --commit`, any other state, pulling the ddp-open-states tip, any image or task-definition change, and anything about Voatz.
