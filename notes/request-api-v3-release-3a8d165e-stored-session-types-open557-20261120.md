# REQUEST (not a GO): api-v3 release at main `3a8d165e` (OPEN-557, session types read from the stored value only). EC2, then the Mac; core unchanged at `10f32ce0`. 2026-11-20 (Mac side, State Specific Handling)

**Not a GO.** It waits for Ramon's go in your session.

## What it does
api-v3's current-session rule (`api/current_session.py`) now treats a session as regular only when its stored classification is `primary`. The guess from the identifier's shape is gone. Your `a2b4903` filled the last blank types it depended on: GA, VA and WA.

**Nothing visible should change.** On the Mac I ran #72's rule against the replica's sessions, with bills counted for pre-filing, and compared it with what the Mac api-v3 serves today:
- **all 17 jurisdictions give the same current and previous sessions;**
- the only blank types left are New Mexico 2011 to 2015, and NM's current and previous sessions are both stored `primary`.

## Exact code
- **api-v3 main `3a8d165e53af5c5ff438d856336087eaaf9a7d12`** (merge of #72). It is the **only** change since your deployed `8cef03e4`: `git log --first-parent 8cef03e4..3a8d165e` shows one merge, 4 files.
- **Core unchanged:** `DDP_CORE_SHA=10f32ce08088e544e88d54ec64aa325aea80756f`.
- No migration, no setting, no `.env` change.

## When (a real conflict, not a window)
**Not while any of these run, because their LegBot hand-off and session reads go to api-v3:**
- the `wa` or `us` archive retries from `cbc37b3`;
- the ddp-sync rebuild or the US 118/119 re-import from `07bde05`.

Do it at an idle gap: no ECS task running, ddp-sync shows nothing running, no `ddp:pipeline_lock:*` held. If the re-import is under way, wait until it has finished and been reported.

## EC2 steps, after the go
1. **Rollback point:** tag the running api-v3 image `:pre-open557`.
2. **Release** by the api-v3 release procedure (RUNBOOK), as for `bc30545`:
   - fast-forward the EC2 api-v3 checkout to `3a8d165e`;
   - rebuild with `DDP_CORE_SHA=10f32ce0…`;
   - recreate the api container only (`--no-deps`).
3. **Checks:**
   - the `check-core-pin-drift.py` call from `c9392c5` exits 0;
   - healthz answers 200;
   - `GET /jurisdictions/<id>?include=legislative_sessions`, expect:

| State | Current | Previous |
|---|---|---|
| ga | `2025_26` and `2026_ss` | `2023_24` |
| va | `2026` and `2027` | `2025` |
| or | `2026R1` | `2025R1` |
| wa | `2025-2026` | `2023-2024` |
| nm | `2026` | `2025` |
| us | `119` | `118` |

   - **Any difference from this table: roll back and report.**
4. **Report** the answers and the time.

**Rollback:** retag `:pre-open557` as the running tag, then recreate api with `--no-deps`.

## The Mac half (mine, after your checkpoint)
- `refresh-api-v3.sh` at the same core, with api-v3 pulled to `3a8d165e` and its own rollback tag.
- The drift check, and the same answers from `:8002`.

## Not authorized
Any core change; any ddp-sync, broker or scrapers change; any data edit; any other host or service.

Tickets: OPEN-557 (OPEN-536).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
