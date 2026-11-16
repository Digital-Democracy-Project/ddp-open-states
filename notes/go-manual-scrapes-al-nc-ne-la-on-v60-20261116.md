# GO: one manual scrape each for **nc, ne, al and la** on v60 (`ddp-scrapers:63`) today, after step 8, instead of waiting for Sunday 11-22. Alabama's version-date passes (section B of `a774838`) then run after Alabama's manual run. 2026-11-16 (Mac side)

**Ramon, 2026-11-16 (pop-up): "let's not wait a whole week"**, choosing **Alabama, North Carolina, Nebraska and Louisiana** for a manual scrape now.

**Why each:**
* **al:** OPEN-569's version dates become stored data, so section B of `a774838` can run (recompute, then stale copies). Also confirms OPEN-563/566 and BROKER-473's stage check.
* **nc:** confirms the OPEN-543 flip holds on a real scrape. Brings in about 719 more roll calls (OPEN-573), motion rules (OPEN-572) and voter names (OPEN-234).
* **ne / la:** confirm the oldest-first order holds after a real scrape on the fixed scraper (closes OPEN-535 / OPEN-534).

## What I need from you

### 0. Gates, checked before **each** launch (stop and report if one fails)
* **Step 8 is done and checked** (`52fcaf5`). Start no scrape before it.
* Outside the nightlies (wa 02:30, usa 03:00, pa 04:00 UTC) and the 05:00-07:00 scorecard chain.
* For the state: 0 running `ddp-scrapers` tasks; its S3 locks (`_lock`, `_import_lock`) read released; no ddp-sync line for it in the last 10 minutes.
* At most **two** state pipelines at once. The archive relay struggles when several archive together.

### 1. Launch, in this order, each **exactly once** (no retry: a failure is a report, not a relaunch)
1. **nc** and **ne** together (about 1 h each last Sunday).
2. **al** when one of them has finished (about 2.5 h).
3. **la** when another slot is free (about 4 h; the longest).

The method is the one used for Nebraska on 11-08: `POST /ddp-sync/v1/trigger/openstates-scrape/<st>` from inside the ddp-sync container, with its own key (not printed). One call each. Expect `{"status":"started","target":"<st>"}`.

### 2. Report each run (one note, or one per pair)
* Run id;
* **task definition revision, read from ECS (must be 63)**;
* start and end (UTC);
* scrape line (`mode`, `found`, vote events);
* archive line (checked / archived / errors);
* LegBot line.

Before-counts, read-only, taken before each trigger: the state's vote events in RDS.

### 3. Alabama: section B of `a774838`, now after **this** run
Run B **after Alabama's manual run has finished its import and archive**, not after Sunday's: B.1 check, B.2 `recompute-diff-order al`, B.3 `remove-stale-documents al` (export first), B.4 final dry run.
* The gates are unchanged.
* Each step commits only if its dry run passes, per Ramon's standing "Save if the trial matches".
* The `b261ead` hold on `recompute-diff-order al` ends only through these gates.

### What I check on the Mac side (you need not)
* nc, ne and la: 0 bills stored newest first after the load.
* nc: vote events against 781 before, and motion classifications present.
* al: 0 undated versions, then the B results on the replica.

## Not authorized
* Any other state (ma and az wait for Sunday as usual).
* A second launch of any state.
* Any commit whose gate fails.
* Migration `0051` (OPEN-539).
* **Alabama's search rebuild (OPEN-577):** it holds for its own go after B.
* Any ddp-sync, broker or manifest change.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
