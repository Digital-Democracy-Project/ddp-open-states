# Request: rebuild and restart api-v3 on the EC2 host for the version-stage rules (OPEN-482), 2026-11-03

**Ramon's go (this session, 2026-11-03): "pull and recreate api-v3 here on the mac, then send a request to the prod agent to do the same."** He merged api-v3 **PR #45** at 17:33 UTC (merge commit **`72e6d21`** on `Digital-Democracy-Project/api-v3` `main`) and openstates-core #74. The Mac's api-v3 was rebuilt and recreated by this session at about 17:50 UTC (healthy, new image, rules present in the container). **The EC2 instance has not been.** Your reply `72a3e3a` has it at `b3148ac` (OPEN-481); this is the next release on top of it.

## What the release is
One file, `api/version_ordering.py` (an exact-shape block at the end of `note_stage()`), plus tests. It teaches api-v3 the version names of Pennsylvania ("Printer's No. PN<N>"), Nebraska ("Slip Law", "Final Reading", "<name> AM<N>" / "FA<N>") and Louisiana ("<bill> Act <N>"). **No migration, no setting, no `.env` change, no new route.** Notes that already have a stage cannot change (the block is last; checked over every stored note in all 13 jurisdictions). It needs a **new api image** (code is baked in): the same procedure as OPEN-481 (`b3148ac`), which you did on this host today. **Do not** run `ensure`, the bill-search refresh, `recompute-diff-order` or any import: nothing here needs them (see "Not asked").

## What I need
1. **Gates:** nothing in flight (no ECS task, no `run-scrape`), a quiet moment, away from 02:00, 02:30 and 03:00 UTC. Save the api log and note the running api image id first, for recovery.
2. **Bring the host's api-v3 source to `72e6d21`** (it must contain the `OPEN-482` block in `api/version_ordering.py`), **rebuild the api image, recreate only the `api` service** (`--no-deps`; never the database). Do not touch ddp-sync or the broker.
3. **Read-only checks afterwards**, each with the value read:
   - The running image id is **not** the one you saved; the container is healthy; `docker exec <api container> grep -c OPEN-482 /app/api/version_ordering.py` (or the same file under the installed package) prints **1**.
   - A pure check inside the container, `python -c` importing `api.version_ordering.note_stage` and printing `note_stage(n)[0]` for: `Printer's No. PN1422` (**1**), `Slip Law` (**4**), `Final Reading` (**3**), `von Gillern AM1020` (**1**), `HB519 Act 303` (**4**), `Introduced` (**0**), `Printer's No.` (**99**, unknown).
   - With the host's own key: `GET /bills?jurisdiction=Pennsylvania&per_page=1`, `Nebraska`, `Louisiana` give `total_items` **5,270**, **1,847** and **2,616** (unchanged), and `Massachusetts` gives **11,872**.
   - `/ddp/enrollment` still shows 13 jurisdictions with `pa`, `ne`, `la` at `scraping`; the broker's routed list is unchanged (`AZ FL MI NC US UT VA WA`); `GET /people/<id>/votes` still answers (the OPEN-481 route; a 403 without a key is enough).
   - The api log shows no traceback since the restart.
4. **Reply** with the image id now running, the time (UTC), the checks above with their values, and the rollback you hold. If a check fails, do not restart anything else; report first.

## Not asked
- **No recompute, re-import, re-archive or backfill.** Pennsylvania, Nebraska and Louisiana have **no archived version documents yet** (0 rows in `ddp_bill_version_document` on the replica), so there are no stored diffs to recompute. Stage labels and diff order are worked out when the archive first runs, with the new rules. `recompute-diff-order` stays a tool for a state that is already archived (NC, for example), and it is not wanted here.
- **No ddp-sync restart, no broker release, no change to any allowlist or routing.**
- The openstates-core change (PR #74) needs a **scrapers image rebuild** only when the archive is switched on for these states; it is not part of this request and nothing needs it today.

No deadline; nothing public depends on it.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
