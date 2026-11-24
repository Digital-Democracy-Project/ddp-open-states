# UPDATE (not a GO) to `0940569` and `4389222`: **v85 is built**: `ddp-scrapers:87` (scrapers) and `ddp-scrapers-db:14`, core `eb197d74`, scrapers `928138b2`. v86's core is **`59dbdaa2`**. 2026-11-24 ~03:20 UTC (Mac side, Onboard New States)

**Not a GO.** Each step still waits on Ramon's go.

## v85 (Ramon's build, per the PM session)
* **Tag `v85`**: task definitions **`ddp-scrapers:87`** and **`ddp-scrapers-db:14`**.
* **Checked on the Mac, from the local `ddp-scrapers:v85` image (id `d985a78b2f01`):**
    * `/opt/openstates-core/DDP_CORE_COMMIT` = **`eb197d7407253550912fc8ba9f9b0aa0c9da127f`**;
    * the scrapers carry Maryland's OPEN-814 (`ANALYSES` in `scrapers/md/bills.py`) and Maine's OPEN-811;
    * `/app/jurisdictions.yaml` has Maryland's `house_speaker_by_session` (`2026`, `2026s1`: Joseline Peña-Melnyk).
* So `0940569` **step 1 (core `eb197d74` everywhere) is what v85 needs**: `check-core-pin-drift.py --image-core eb197d74…` must exit 0 before v85 runs anything.
* Then `0940569` steps 2–6 as written, on **rev 87 or later**.

## v86: core `59dbdaa2` (replaces "core main at build time" in `4389222`)
* OPEN-817 (core #148) is merged as **`59dbdaa2f3628821baa4cd45f1fabeb2cf936c7a`**.
    * Since `eb197d74` it is the only change: `openstates/importers/bills.py` plus tests. **No migration.**
    * It matches votes dated after a session's end to a member seated that day. On the Mac replica it fills 606 blanks (MD 2, AZ 277, FL 184, VA 138, NC 5) and changes 0 existing matches. They fill only when those votes are imported again.
* **v86 = scrapers main with OPEN-819 (Washington 2027-28; PR still being built) + core `59dbdaa2`.**
* **Before any run on v86:** a core rollout to `59dbdaa2`, like step 1 (EC2 api-v3, EC2 ddp-sync, Mac api-v3, then the drift check against `59dbdaa2`), on its own go.
    * If v86 is built before step 1 has run, **skip `eb197d74` and do one rollout at `59dbdaa2` together with v86**; v85 then runs nothing.
* **ddp-sync's SYNC-188 rebuild** takes v86's scrapers commit in `DDP_SCRAPERS_SHA` if it happens after v86. Otherwise use v85's `928138b2…`.

## Not authorized
Unchanged.

Tickets: OPEN-146; OPEN-817, OPEN-819, SYNC-188.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
