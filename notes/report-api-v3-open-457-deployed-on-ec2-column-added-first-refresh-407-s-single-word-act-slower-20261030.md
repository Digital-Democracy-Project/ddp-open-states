# Report: api-v3 `4e90dc0` (OPEN-457) deployed on the EC2 host. Sequence worked, gate passed, refresh took 6.8 min; two things differ from your expectations: `act` is 32% slower, and the top 20 of `act`, `state` and `health` changed

Prod agent, Fri 2026-10-30 18:50 UTC. The operator said "Option A, go now". Output in `/home/bitnami/ops/api-v3-open457-20261030T1835Z/` (`run.txt`, `single-words.txt`, scripts). Window: Friday evening, nothing launching until Saturday 02:30; at the swap api-v3, VoteBot, ddp-sync and the broker were idle.

## Steps, as you wrote them
* **0 before:** api-v3 HEAD `f9dde91`, clean; container started 2026-10-28 02:04:53; Redis `ddp-openstates-redis-1` started **2026-10-11T19:49:12.477Z**; `api` image **`6e3a0d7e0e10`**, tagged **`pre-open457`** (still that ID).
* **1:** fast-forward only: api-v3 to **`4e90dc0e2bea13fb7bee1eb80f5df5f2fc4442b5`** (PR #39 merge `b9d2f61` is in it). **I did NOT fast-forward `/opt/ddp-open-states`**: it is 14 commits behind `main`, and they are **not docs only** (they change `run-scrape.sh`, `run-archive.sh`, `check-replica-health.sh`, `lib/slack-alert.sh`, `start-os-api.sh`, `backup-openstates-db.sh`, the scrapers `Dockerfile` and `verify-jurisdiction`); it stays at `3b78732760`, and `deploy/` is unchanged by them.
* **2:** `build api` without recreating: 3 s, new image `1ce13c3e873b`; the running container (old code) kept serving.
* **3:** `run --rm --no-deps api python -m api.search_projection ensure`: `=== BILL SEARCH ENSURE: ddp_bill_search present ===`, exit 0, 3 s. Before it: no advisory lock held, no active query on the table.
* **4 gate: PASS.** `current_database`: **`openstates`**; column `alt_titles` present; index `ddp_bill_search_alt_titles_idx` present and valid (no URL printed); 77,472 rows, 0 with alt titles.
* **5:** `up -d --build --no-deps api` at 18:36:05: **3 s**, healthy; container created 18:36:07, started 18:36:08, image `1ce13c3e873b`; **Redis start time unchanged** (2026-10-11T19:49:12.477Z).
* **6 smoke:** your two URLs as written answered **400** (`at least one 'jurisdiction' is required`: they omit the required parameter; not a 500). With the nine jurisdictions: **`/ddp/search?q=One+Big+Beautiful+Bill` 200 and `/ddp/search/suggest?q=One+Big` 200**; `/healthz`, `/ddp/enrollment` and `/bills` 200.
* **7:** `refresh --full`: 18:36:48 to 18:43:35, **`BILL SEARCH REFRESH: all | mode=full | refreshed=77649 | with_text=75944 | orphans_removed=0 | seconds=406.5`, exit 0**: **6.8 minutes, not 26** (you allowed about 26).

## Step 8
* **Coverage** (`/ddp/search/coverage`, nine jurisdictions): **`projected == bills` for all nine**: US 39,097, FL 7,685, MA 11,840, VA 4,396, MI 4,159, WA 3,411, NC 2,343, AZ 2,190, UT 1,021. `opencivicdata_bill` has 77,649 rows, equal to `refreshed`.
* **Alt titles:** `SELECT count(*) FILTER (WHERE alt_titles <> ''), count(*)` = **29,820 of 77,649 (38.4%), exactly the Mac's figure.**
* **`q=One Big Beautiful Bill`: HR 1 (US 119) is first** (then S 2556, S 2749); 89 to 106 ms. **`q=FEHB Protection Act`: HR 1 is 4th** (S 4035, HR 7868, HR 2193, HR 1), as on the Mac.
* **Multi-word timings (nine jurisdictions, median of 5):** `One Big Beautiful Bill` 89 ms; `state park campsite reservations` 198 ms (FL HB 109 first); `school safety grant program` 267 ms; `FEHB Protection Act` 410 ms; `education funding` 690 ms; the known slow shape `S 1` **880 ms** (your runbook says about 1.25 s). `suggest`: `Med` 340 ms, `S 1` 351 ms, `One Big` 93 ms. (The runbook's section 6 numbers are for a local database and a 65-query judged set I do not have, so I cannot compare them one for one.)

## Single words against my 10-28 table: NOT unchanged
| word | pre-#36 (10-28) | reverted (10-28) | now | first-20 ids same as pre-#36 |
|---|---|---|---|---|
| act | 1,023 ms | 1,005 | **1,329** | **16/20** |
| state | 995 | 1,004 | 1,027 | **11/20** |
| school | 333 | 304 | 324 | 20/20 |
| health | 511 | 492 | 505 | **14/20** |
| public | 612 | 608 | 603 | 20/20 |
| hemp | 76 | 86 | 80 | 20/20 |
You expected single words to run the same SQL as before and be unchanged. **`act` is 32% slower than the reverted run** (1,005 to 1,329 ms; the five runs range 1,290 to 1,458) and **the top 20 changed for three of the six words** (`act` 16 of 20 the same, `state` 11, `health` 14); `school`, `public` and `hemp` are identical. I did not look into why (a ranking that now sees the other titles would fit the ids, and I did not check the SQL).

## Rollback state
Not used. The `pre-open457` tag is the rollback (re-tag and recreate); the column, index and the filled `alt_titles` stay and are harmless to old code. No data was lost or deleted; `orphans_removed=0`. No error or traceback in the new container's log.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
