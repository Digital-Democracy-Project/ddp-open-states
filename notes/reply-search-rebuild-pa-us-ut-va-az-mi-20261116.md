# Reply: search rebuild done for pa, us, ut, va, az, mi on EC2, checks pass (OPEN-533), 2026-11-16 01:24 UTC (prod agent)

Answers `c4110ce8`. User's words in session (pop-up, after I summarized the new notes and said I would not act on the relayed go alone): **"Yes, run it now"**. Ramon's gate: finish before 02:15 UTC. Done 01:24:30.

- **Gates:** api-v3 `8214db7` (image `7de2aed5fcff`, healthy); 0 ddp-sync pipeline lines in 10 min; 0 running scraper tasks. The command has a `--dry-run`; I did not rely on it for sizing (without `--full` applied it only counts rows already stale: pa 5,286, the rest 0).
- **Rebuilds, one at a time** (`docker exec ddp-openstates-api-1 python -m api.search_projection refresh --full --jurisdiction <x>`; a script stopped on any non-zero exit or any health probe other than 200, and would not start a state after 02:10; neither triggered). Summary lines, UTC:
  - **pa** 01:19:03-01:19:26: `mode=full | refreshed=5286 | with_text=5286 | orphans_removed=0 | seconds=21.8`
  - **us** 01:19:26-01:23:09: `refreshed=39277 | with_text=38381 | orphans_removed=0 | seconds=221.5`
  - **ut** 01:23:09-01:23:28: `refreshed=1021 | with_text=1021 | orphans_removed=0 | seconds=18.1`
  - **va** 01:23:28-01:23:54: `refreshed=4413 | with_text=4413 | orphans_removed=0 | seconds=25.5`
  - **az** 01:23:54-01:24:08: `refreshed=2190 | with_text=2190 | orphans_removed=0 | seconds=12.4`
  - **mi** 01:24:08-01:24:30: `refreshed=4234 | with_text=4234 | orphans_removed=0 | seconds=21.0`
  Every exit 0; the api's `/healthz` read 200 after each; api container about 5% CPU, 470 MiB during the first run.
- **Checks (`/ddp/search`, read through the broker's settings; the response has `exact` and `text` lists, no `results` key; my first baseline read the wrong key and I corrected it before using it):**
  - **BEFORE:** `precondition` + pa: 0 rows; `education` + pa: 0 rows (Pennsylvania was not in search); us 20, ut 20.
  - **AFTER:** `precondition` + pa: **12 bills, HB 2625 NOT among them** (first: HB 1655, SB 31, SB 756, HB 2815, HB 2224, HB 2030). `education` + pa: **20 results** (first SB 315, HB 1505, HB 2167). `education` + us: **20**; + ut: **20**. All status 200.
  - The api log since 01:19: 0 Traceback/ERROR/5xx; ddp-sync log: 0 `jurisdiction_manifest_unusable` / `..._disagrees`.
- **Not done:** any other state, any manifest or `search_refresh` change, ddp-sync, broker, scrape, archive, recompute.
- **Not checked:** I did not read the earlier `/bills?q=` call again (it returned 0 results in my 11-15 note; `/ddp/search` is the route that matters, as you said).
