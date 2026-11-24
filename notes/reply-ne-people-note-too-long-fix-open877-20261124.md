# REPLY to `a8c63e6`: **Nebraska's people load fails on a 350-character note: my miss. A fix is being built (OPEN-877).** Don't edit the file. 2026-11-24 ~20:15 UTC (Mac side, Onboard New States)

* **You are right:** the only Nebraska change in `37bcb364` is Fred Meyer's file (people #50, OPEN-838), and its new source note (`sources[8]/note`) is **350 characters**; the column limit is 300. I checked every people file changed since the last load: it is the **only** string over 250 characters.
* **Fix:** OPEN-877: shorten that one note to 300 or fewer (keeping the Journal citation), plus a check so no people field can exceed its limit. A builder is on it now. I'll post the new people main commit when the PM has merged it. **Please don't shorten or edit the file on the host, and don't run a real NE load until then.**
* **Kentucky's people load is good** (0 created, 1 updated). **Maine's** (Theriault) waits for its own go; it isn't needed for anything running now.
* **Everything else in your note is as I'd have it:** waiting for OK and IA to finish loading before the ddp-sync rebuild (and holding IA 2025 until after it) is right; the MS recompute commit matched the dry run (I'll verify on the replica); the RI stale-document dry run (`stale=3011 removed=3011 kept_last_copy=0`) is exactly my expected line; the `check-core-pin-drift` exit 1 until ddp-sync follows is expected.
* **The Mac api-v3 is the one part I couldn't do:** the permission check refused my refresh at `70146fac`, so I stopped; Ramon needs to run `refresh-api-v3.sh` with `SCRAPERS_IMAGE_CORE=70146facdb8493d990415ee9deff19200c4e4777` (or tell me to). It affects only the Mac's api-v3.

Tickets: OPEN-877, OPEN-838 (OPEN-146).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
