# REQUEST (not a GO): api-v3 release at main `8cef03e4` (OPEN-660, pre-filed sessions count as current), EC2 and the Mac, core unchanged at `10f32ce0`. 2026-11-20 (Mac side, Onboard New States)

**Ramon, 2026-11-20, "Show them sooner":** "we like to put Voatz polls on bills in pre-filing so that voters have more time to weigh in before the session starts."

## What it does
api-v3's one current-session rule (`api/current_session.py`) now counts a session **in pre-filing** as current: its start date is still ahead and it already has bills. It is current beside whatever is current today.
* Previous sessions and the fallback regular session don't change.
* A session with no bills doesn't change.

ddp-sync's bill sync, the broker's search, Explore and the broker's session rows all read this flag, so pre-filed bills reach the site and can be polled. **Nothing else is released for that.**

## Exact code
* **api-v3 main `8cef03e4a1bb43573295ade1e17b5b1832680d3f`** (merge of #74). It is the **only** change since the deployed checkout `9fba5a6`: `git log --first-parent 9fba5a6..8cef03e4` shows one merge, 4 files.
* **Core unchanged:** `DDP_CORE_SHA=10f32ce08088e544e88d54ec64aa325aea80756f`, v71's core and what EC2 runs now (your checkpoint `c9392c5`).
* No migration, no setting, no `.env` change.

## Order with OPEN-659's scrapers image (`8f665b0` / `6c007d7`)
**Independent: it does not need to ride with that image.**
* This release alone makes Florida 2027 and Virginia 2027 current. Their pre-filed bills are already stored.
* Nevada 84 joins once that image's first Nevada run has stored its bills. Either order is fine.
* If the new image ships first with a newer core, build api-v3 at that image's core instead, as the usual release order says (image, then api-v3 at its core).

## What I need from you (EC2), after the go
1. **Gate:**
   * nothing in flight: no ECS task running, ddp-sync shows nothing running;
   * your open archive-launch alert (`0cf87ce` / `9996932`) does not block this. It's a different service, but say if you'd rather wait.
2. **Rollback point:** tag the running api-v3 image `:pre-open660`.
3. **Release by the api-v3 release procedure** (RUNBOOK, api-v3 release):
   * fast-forward the EC2 api-v3 checkout to `8cef03e4`;
   * rebuild with `DDP_CORE_SHA=10f32ce0…`;
   * recreate the api container only (`--no-deps`).
4. **Checks:**
   * The `check-core-pin-drift.py` call from `c9392c5` exits 0.
   * healthz 200.
   * `GET /jurisdictions/fl?include=legislative_sessions` and `/jurisdictions/va?include=legislative_sessions`: **`2027` has `is_current: true`, and `2026` keeps `is_current: true`**. Nothing else changes: FL previous `2025`, VA previous `2025`.
   * `/jurisdictions/ut?include=legislative_sessions`: `2027` stays `is_current: false` (no bills yet).
   * `/jurisdictions/us?include=legislative_sessions`: `119` current, `118` previous, as before.
5. **Report** those answers and the time.

**Rollback:** retag `:pre-open660`, then recreate api with `--no-deps`.

## The Mac half (mine, after your checkpoint)
* `refresh-api-v3.sh` at the same core (`SCRAPERS_IMAGE_CORE=10f32ce0…`, api-v3 pulled to `8cef03e4`), with its own rollback tag.
* The drift check, and the same four answers from `:8002`.

## Checked after both (Mac side)
* ddp-sync's next bill sync for FL and VA includes their 2027 bills.
* The broker's onboarding check lists 2027 among FL/VA current sessions.
* A 2027 bill can be picked for a poll. **These are OPEN-660's remaining acceptance lines.**

## Not authorized
Any core change; a ddp-sync, broker or scrapers change; any data edit; any other host or service.

Tickets: OPEN-660 (OPEN-659, OPEN-146).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
