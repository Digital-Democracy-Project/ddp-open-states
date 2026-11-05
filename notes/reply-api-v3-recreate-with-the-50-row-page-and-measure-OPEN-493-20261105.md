# Reply: api-v3 recreated with the 50-row page (PR #51) and measured, OPEN-493 / BROKER-431. Done, no check failed. Written 2026-11-05 01:05 UTC.

Run at the user's go in this session ("Yes, run it now (Recommended)", 00:57 UTC), after #51 was merged (`main` tip `b7adb9a3bc`, "Merge pull request #51"). I read `page50_vs_three20.py` first (GET only, key from the broker's own settings inside the web container, never printed). Nothing else was changed: no broker change, no `ensure`, no refresh, no setting.

## BEFORE and AFTER side by side (production, from the broker web container to api-v3 `10.0.0.11:8002`, 15 runs 1.5 s apart, `sort=latest_action_desc`)
| | BEFORE (00:57 UTC, image `7bc7f653f36a`) | AFTER (00:58 UTC, image `3b1a466605a1`) |
|---|---|---|
| 3 calls of `per_page=20` at once (what the broker does today), median / min / max | **235 ms** / 214 / 316 (all 200) | **263 ms** / 215 / 344 (all 200) |
| 1 call of `per_page=50` | **HTTP 400** (as expected before the change) | **median 110 ms** / min 102 / max 182 (200) |
| first-50 bill ids, fingerprint | three calls `517bcc9d57b4` | three calls **`517bcc9d57b4`** and one call **`517bcc9d57b4`**: **match** |
| `total_items` / `max_page` | n/a | **87,489** / **1,750** (50 rows a page) |
| `per_page=51` | n/a | **HTTP 400** (expected) |
| `per_page=50` with `include=sponsorships` | n/a | **HTTP 400** (expected) |
So **one call of 50 takes about 110 ms against about 263 ms for three of 20, 2.4 times faster**, and returns the same 50 bills in the same order. (The three-of-20 number varies a little between runs: 235 then 263; it is the same kind of call and the same index, so I read it as noise. Earlier today, `43640898`, I measured about 217 ms for three at once.) The Mac copy's figures in your request (62 ms against 105 ms) are the same direction.

## What I did (UTC)
1. Gates at 00:57: no ECS task, nothing in flight, no ddp-sync job in 10 minutes, load 0.7. Saved the running image id `7bc7f653f36a` (also tagged **`ddp-openstates-api:pre-open493`**) and the api log (`/home/bitnami/ops/log-archive/ddp-openstates-api-pre-open493-20261105T0057Z.log.gz`).
2. `/opt/ddp-open-states/api-v3`: fast-forward from `23d6e80903` to `origin/main` = **`b7adb9a3bcc65ebbce2cd842a33fd69c1e3f81db`** (3 files, +95 / -2, the new test `api/tests/test_bills_page_size.py`). **A slip, harmless:** my first merge command used a mistyped commit id and printed "not something we can merge"; I then merged `origin/main` itself, which is the #51 merge commit. `max_per_page_without_includes = 50` is in `api/bills.py` line 81.
3. **Built and recreated only `api`** (00:58:01): compose exit 0 in 3 s; **down about 5 seconds** (healthz polled every 0.5 s); healthz 200 at 00:58:12; healthy. New image **`3b1a466605a1`** (full `sha256:3b1a466605a184078721d34ef8717a0219aca08473e7b2bcae75212dfd32c807`), started 00:58:04. redis untouched (started 2026-10-11 19:49 UTC).
4. **Checks:** image id changed: yes. `python -c "import api.bills as b; print(b.BillPagination.max_per_page_without_includes)"` inside the new container prints **50**. `GET /healthz` **200**. No key **403**; the broker's key `GET /bills?jurisdiction=nc&per_page=1` **200**. `/ddp/enrollment` **200, 13 jurisdictions**. API log since the restart: **0 tracebacks, 0 errors**.
5. **The broker's list rows, for the record** (same script as before, 00:59 to 01:03 UTC, load 1.0, median ms): `bills list p1` **320**, `bills list US` **204**, `legislators list p1` 203, `legislators list US` 132. They have not changed yet, as you said, because the broker still asks for 20. (Earlier today: bills p1 297, US 150.)

## Also, a late line for the `is_bill_version` reply (`a5e35ac`)
The 10-minute replication reading I promised did not run on time (my wait loop compared the clock wrongly after midnight, and my attempt to stop it killed my own shell). I took it directly instead **at 00:56 UTC, 33 minutes after the column change: the slot `ddp_legbot_subscription` is active, state streaming, lag 0 bytes; the api log had 0 errors in the last 40 minutes; healthz 200.** This is still the RDS side only; the Mac's own apply worker is yours to check.

## Not done
No broker release (it must not ask for 50 until its own deploy), no `ensure`, no refresh. Rollback not needed; if wanted: re-tag `ddp-openstates-api:pre-open493` (`7bc7f653f36a`) as `local` and recreate `api` with `--no-deps`.
