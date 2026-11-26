# Request (NOT a GO): a third Hawaii re-import (2026) for the failed-final-vote label (OPEN-900, scrapers #297), after the image that carries it. Also names BROKER-605. 2026-11-26 (Mac side, State Specific Handling)

**Not a GO.** Every step waits on Ramon's go in your session, and on #297 being merged and an image built from it (Ramon builds the image). A third Hawaii run was "not authorized" in `request-v92-...-people-hi-second-reimport`; this is the request for it, with its reason.

## Why
Ramon (via the PM session, 2026-11-26, on OPEN-900): "Fix the label first, then approve once" for Hawaii's scorecard list (BROKER-603, ddp-broker-py #840). The Hawaii scraper types a failed "Third Reading" or "Final Reading" roll call as nothing, so the broker's "latest passage vote replaces earlier ones" rule keeps an earlier passed vote or counts nothing.

* **Scrapers #297** (head `edb1362a5`, one pattern line in the `hi` block of `motion_classification.yaml`): `^(reconsider: )?failed to pass (third|final) reading\b` is `passage`. No change to `hi/bills.py`.
* **Measured on the Mac replica (read-only):** Hawaii holds 12,828 stored vote events (session 2026 only, 6,728 bills). **Exactly 6 roll calls change label** (none to passage), nothing else: HB 1516, HB 1550 and SB 3263 (Senate, "Failed to pass Final Reading"); HB 1919 (House) and HB 2413 and SB 319 (Senate), "Failed to pass Third Reading".
* **Effect on what counts (the broker's own eligibility code, offline, with the Hawaii rule from #840):** counted bill-chambers **2,168 -> 2,171**: 3 start (HB 1919, HB 2413, SB 319), 3 swap (HB 1516, HB 1550, SB 3263: the failed final vote replaces the earlier passed third reading), 0 stop.
* A YAML label reaches stored votes only by a re-import (relabel does not read this file).

## Order (each step on Ramon's go)
1. **#297 merged** (the PM merges) and a **scrapers image built from a main that contains it**. The latest image I know is v96 (rev 98, scrapers `248c2571c`), which does **not** carry #297. It can ride the next image Ramon builds (v97 if #297 is merged before it).
2. **Gate:** new tasks run that image's revision or later; read `DDP_SCRAPERS_COMMIT` in the image and check it contains #297's merge commit. If it does not, stop and report.
3. **The run:** `POST /ddp-sync/v1/trigger/openstates-scrape/hi?full=true&sessions=2026` must answer 202 with `"full": true`. `ddp:pipeline_lock:hi` empty first. Then the Hawaii archive (a resumed run does not start one by itself). Hawaii holds only session 2026 on the replica.
4. **Pass (I read it on the replica):**
   * the 6 roll calls above are `passage` (everything else unchanged: **exactly 6 labels change**);
   * vote events **12,828**, bills **6,728**, unchanged;
   * unmatched person votes unchanged from the second re-import's result (only "Garcia; and" remained);
   * the counted bill-chambers read **2,171** with #840's rule offline.
   Anything else: stop and report.
5. **Then** the Hawaii scorecard approval is Ramon's (BROKER-603), once.

## Also blocks Hawaii's scorecard backfill (not this request, not mine)
**BROKER-605** (a broker fix): a motion text over 200 characters: **1,020 of Hawaii's 12,828 vote events**. Hawaii's scorecard backfill and switch-on wait for the label (this note) **and** BROKER-605 (a broker release through `/broker-deploy`). Nothing in this note changes the broker.

## Not authorized
A Hawaii scorecard backfill or switch-on; any broker change; any other state's re-import; a second Hawaii run before the image has #297; deleting a lock, S3 object or Redis key.

Tickets: OPEN-900, BROKER-603, BROKER-605 (OPEN-536). Rollback: none needed for data (a re-import restores labels from the source; the previous labels are the source's own).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
