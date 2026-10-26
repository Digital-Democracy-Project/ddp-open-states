# REPLY: how NC did in the first scheduled jobs after the flip (read-only; prod agent, EC2-broker host, 2026-10-26 19:28 to 19:40 UTC)

Nothing was changed, restarted, triggered or deployed. No secret was printed (variables read by exact name; the one token I touched I only tested for "set"). The broker containers were recreated at the flip (2026-10-23 02:14:56 UTC), so their logs cover exactly the window you asked about; ddp-sync's log starts at its 10-22 21:45 restart. Raw outputs are on this host in `/home/bitnami/ops/nc-first-jobs-20261026/`.

## 1. The 03:00 UTC jobs, 10-23 to 10-26
| day | people pull | USA scrape (lower + upper) |
|---|---|---|
| 10-23 | 03:00:00, `done head_after=cb1619a7afeec16e65f08431f77a7481ec6f270c`, executed successfully | `completed duration_seconds=1088.1 failed=0 total=2` (ended 03:18:08) |
| 10-24 | `done head_after=c6c64f9d1898bdc8caef49ceb4c3ef30a39931b1` | **5,863.7 s**, `failed=0 total=2` (ended 04:37:43) |
| 10-25 | same head `c6c64f9d...` | **5,438.2 s**, `failed=0 total=2` (ended 04:30:38) |
| 10-26 | same head | 976.3 s, `failed=0 total=2` (ended 03:16:16) |
* **The daily "people pull" is only a `git pull` of `/opt/ddp-open-states/people`** (it ran in under a second each day); it is **not** the database import. The import is the **weekly people refresh**: **10-25 10:00:00 to 10:02:26 (146.8 s) `done`**; the host's `logs/scraper.log` shows `os-people to-database nc` at **10:02:03** among the ten states (us, fl, wa, va, mi, ut, az, ma, nc, al) and `People refresh done.` **So NC is in the weekly refresh list.** I did not read the 10-18 run's full state list, so I do not claim NC was absent then.
* **NC's people count in api-v3 is still 173** (`/people?jurisdiction=North Carolina`, read 19:3x UTC today; controls Utah 106 (107 on 10-22), Virginia 142).
* **The two long USA runs (10-24, 10-25) are the LegBot relay timeout again:** `archiver_triggered_legbot_wireguard_trigger_failed error=` (empty) at 10-24 04:20:19 **and 10-25 04:14:08**, each exactly 3,600 s after the relay began (`_MAC_TRIGGER_TIMEOUT_SECONDS = 3600.0`, `openstates_archive.py:503/594`; details in my 10-25 report). No other error in those jobs.

## 2. The 04:00 UTC scorecard chain (celery log is New York time; I converted to UTC)
Ran every night and **succeeded** (no `raised`/failure): 10-23 04:00:00, fetch phases succeeded 05:08:00, **succeeded in 9,989.2 s** (06:46:29); 10-24 **10,077.7 s** (06:47:57); 10-25 **12,002.1 s** (07:20:02); 10-26 **10,472.99 s** (06:54:33). **NC in the chain's logs:** the only lines naming NC are debug lines of the form `Jurisdictions with tallies for bill <US bill>: {... 'North Carolina' ...}` (tally data for US bills by state, 21,855 such lines in 5 days, the same format as for other states). **No error or warning names NC, a NC legislator or a NC bill.** I cannot tell from these logs whether the chain does anything with NC bills beyond those tally lines.

## 3. Broker errors since the flip (10-23 02:14:56 UTC onward)
* **Searched for** (celery, celery-beat and web logs): `\bNC\b`, `North Carolina`, `state:nc`, `ocd-jurisdiction/country:us/state:nc`. **At ERROR / WARNING / Traceback / Exception / CRITICAL level: 0 lines in celery, 0 in beat, 0 in web.** The 48 web lines naming NC are all normal DEBUG/INFO: `Routing NC to DDP OpenStates replica`, `GET /bills?jurisdiction=NC&session=...`, `GET /jurisdictions/NC?include=legislative_sessions`, `/ddp/search/hydrate`, `/ddp/search/coverage`. **I did not search by NC bill ids** (they are bare `ocd-bill/<uuid>` with no NC marker, so there is no pattern to match without a list).
* **All errors, for context:** web: 774 `DisallowedHost` tracebacks (internet scanners using the server's IP or EC2 hostname) plus **1 `TimeoutError`** (10-23 02:16:33 UTC, `openstates search unavailable: /ddp/search ... read timeout=4.0`: my own cold-start `q=school` smoke test about 80 s after the flip, not NC); celery: the usual noise (cache-miss messages, `Jurisdiction with iso2 DC/PR does not exist`, Voatz event messages), nothing new; beat: 0.
* **nginx 5xx per day: 10-23: 0, 10-24: 0, 10-25: 0, 10-26: 1** (10-26 00:43:23 UTC, a scanner `GET /geoserver/web/` answered 502).

## 4. NC smoke checks (GET only, 19:3x UTC)
* `/api/openstates-jurisdictions/` returns `MI, UT, US, VA, AZ, WA, FL, NC, AL, MA`: **NC listed**.
* `/api/openstates-bills/?jurisdiction=NC&session=2025`: 200, **2,338** (unchanged).
* `/api/search/?q=school&jurisdiction=NC`: 200, **168** (165 on 10-23), `partial` false, 0.81 s.
* **`/api/search/?q=Eddie+Settle`:** 200, 20 results (19 bills plus **1 representative**), `partial` false; **the representative `Eddie Settle` (id `b4b6f0a7-baca-4062-947a-989cb9f98356`) is at rank 3** (ranks 1, 2, 4 and 5 are bills: "Celebrating the life of Eddie L. Radden", "Further Continuing Appropriations...", "A bill to provide for the equitable sett...", "Commending Eddie Thomas"). **`/api/search/?q=Edie+Settel`:** 200, total 1, `partial` false: **only result, rank 1, the same representative.**

## 5. The nightly search jobs
Both ran **every night** (03:30 UTC; four runs 10-23 to 10-26), all `succeeded`: `rebuild_all_search_documents` in 0.15 to 0.26 s (`bills_total` **46,460 / 46,480 / 46,498 / 46,539**, `bills_updated` 0, `representatives_total` **1,503** every night, `representatives_updated` 0); `run_search_coverage_report` in 35 to 55 s. Its NC lines, every night: **`search coverage: == 2. OpenStates universe (MI, UT, US, VA, AZ, WA, FL, NC) ==`** and **`search coverage: NC: bills=2343 projected=2343 with_text=2343`** (10-23, 10-24, 10-25 and 10-26 03:30 UTC, in the log's 10-22 to 10-25 23:30 NY stamps). **These lines carry no NC people or representative counts**; `representatives_total` was 1,503 on every night since the flip (I do not know what it was before).

## 6. Parity (`check_replica_parity --jurisdiction NC --sessions 2025,2025E1`, exit 1)
Sessions match ✓. **Session 2025:** Bills public **2,338** / replica 2,338 ✓ (0.00%); **Vote-events public 770** / replica 774 (0.52%) ✓. **Session 2025E1:** Bills 5 / 5 ✓; **Vote-events public 6 / replica 7 (14.29%) ✗** (tolerance 2.0%). **Roster public 173 / replica 173 ✓.** Only the waived 2025E1 line fails. **The public side keeps moving, in both directions:** 2025 votes 773 (10-22), 771 (10-23), **770 now** (down 3 in four days, replica constant at 774); 2025E1 votes 3 (10-22), 5 (10-23), **6 now** (replica 7). I did not look into why 2025 is drifting down; at 0.52% it is within tolerance.

## 7. Which broker build
Broker `HEAD` **`489c6578`** (`489c657891701708ab2d2210ed9e073085e9ff46`), clean; **it does not contain BROKER-300**: no commit mentions it and no bill-event endpoint code exists in the running build (BROKER-300 is `71c83ba9` on `origin/main`; the broker is **86 commits behind** main). **SYNC-128 hook:** ddp-sync is at `74d72fe`; `config/sync_schedule.yaml` has `broker_bill_event_signal` **`enabled: false`, `jurisdictions: []`**. The container has `DDP_BROKER_API_TOKEN` set (value not shown; I did not check whether it is the placeholder the yaml comment mentions). Nothing was deployed.

## Could not read / not checked
NC bill ids in the logs (no pattern); whether the scorecard chain uses NC data; the Mac's own logs; what `representatives_total` was before the flip; why the public 2025 vote count is drifting down. BROKER-302 and OPEN-231 stay In Progress for Ramon.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
