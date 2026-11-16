# Reply: Louisiana's manual scrape on revision 63, RESULT: completed, clean. Four-state summary. 2026-11-16 11:36 UTC (prod agent)

Completes `1f19165e` section 2 for la; follows `39b13208` (nc, ne) and `6d5db0e9` (al failed). **Nothing failed for la: 0 `Traceback`/`ERROR`/`CRITICAL` lines in the scraper log group for this run, `status=completed failed=0`.**

## la: run `la-ebf3078695cc`
- **Revision:** `ddp-scrapers:63` (read from ECS, task `7c9e359f5578442eaceb4cd9c571f47a`). One launch, no retry.
- **Times (UTC):** launched 07:35:03; scrape task summary 11:26:16, collection done 11:26:57; RDS load 11:26:57 to 11:33:52 (6 min 55 s); archive done 11:35:23; **pipeline done 11:35:23** (`duration_seconds=14420.5`, `archived=True`, `failed=0`, `sessions=1`, `status=completed`).
- **Scrape line:** `{"mode": "incremental", "status": "ok", "found": 5792, "duration_s": 13631}`; the task's own report **vote_event: 3172**. Sunday's run found 5,792 as well.
- **RDS: 3,172 vote events before and after; 2,616 bills before and after** (the same objects re-saved).
- **Archive** (`la-archive-9d4e9222d6fc`, ok, 21 s): checked 2,616, fetched 0, skipped 10,468, archived 0, `fetch_errors 0`, blocked 0, `extract_errors 0`, conflicts 0, `persist_errors 0`.
- **LegBot:** `archiver_triggered_legbot_no_sessions_touched` (no new documents): **no trigger sent**; SYNC-162's first live trigger is still unseen. **No `bill_search_refresh_run` or `knowledge_base_embedding_run` line for la** (nor for ne this morning; nc logged one, `refreshed=2343`).
- The usual `no usable filing figures for a successful run` warning.
- **Not checked (yours, on the Mac):** that 0 la bills are stored newest first.

## The four manual scrapes, in one table
| state | run id | start (UTC) | end | result | vote events before to after |
|---|---|---|---|---|---|
| nc | `nc-01a875a2f3a6` | 06:07:12 | 07:21:41 | completed | **781 to 1,501** |
| ne | `ne-dcaf452fc46f` | 06:07:17 | 07:16:12 | completed | 1,772 to 1,772 |
| al | `al-2086d764108a` | 07:34:55 | 07:36:28 | **FAILED** (`start` kwarg, `6d5db0e9`) | 2,550 to 2,550 |
| la | `la-ebf3078695cc` | 07:35:03 | 11:35:23 | completed | 3,172 to 3,172 |
All four on `ddp-scrapers:63`, one launch each.

## State of the open items
- **Alabama section B: blocked** until Alabama has a successful run (see `6d5db0e9`: the first incremental run fails on the `start` argument; I expect every Alabama run to fail while the watermark exists). I have not touched it and will not relaunch it without a word from you or the user.
- **Tonight's nightlies on revision 63 (wa 02:30, usa 03:00, pa 04:00, 11-17):** migration 0051 is in (`2f92468c`) so their archive steps can run. **Pennsylvania's will use `start_filter: true`** (`036052a4`) and, if its scraper takes `start`, should run incremental; the earlier stale S3 lock has expired (`921cfc1`). I will read all three in the nightlies note (section C: the OPEN-574 export line, any full-walk warning, mode, run time; and SYNC-162's first LegBot trigger).
- The broker (`bdef7ef1`), api-v3 `306b4f5` (`07a9d850`), the state list `e38af9c3` (`036052a4`) and migration 0051 (`2f92468c`) are live.
