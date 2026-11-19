# UPDATE to `5836c52` (Part A, image v69): v69 carries core `c983ae68`, not `5c1455e1`. 2026-11-19 (Mac side, State Specific Handling)

**Not a GO.** It corrects one line of request `5836c52` (OPEN-638). Ramon built v69 from main, and it is registered.

## What v69 is
| Repo | v69 | Since v68 (rev 71: scrapers `dca8e7a6`, core `5c1455e1`) |
|---|---|---|
| openstates-scrapers | `65815f3df68a1e1d635e0cc8072b9d2319909847` | #134 only (OPEN-638): federal related bills keep congress.gov's type; only "Identical bill" is a companion |
| openstates-core | `c983ae68599e94494a94edc23d576b483922302e` (#132, OPEN-637) | **one rule:** New Mexico's "Amendments in Context" is added to the not-a-version names (`version_ordering.py` `_PROCEDURAL_DOCUMENT_NOTES`), with its tests. No migration, no model change |

* **Image:** ECR `ddp-scrapers:v69`, digest `sha256:4c73d6a35fa941b7562a2fc3673fc90a3875fa7ea30038a5a107ee1b138e8ce6`, **task-definition revision 72**.
  * Built from main at about 04:30 UTC on 11-19; all of the image's own checks passed.
  * **Registered** (PM session). One task was running at registration (`8f594676…`): it stays on v68 (rev 71). Tasks launched after it use v69.
* **Part B is on hold:** Ramon is weighing a re-scrape of only the needed bills (the scraper's `bill_no` option) instead of the whole 118th and 119th Congresses. Do not start Part B until a note says which.
* **Correction:** `5836c52` said "core unchanged". That is no longer true: core is now `c983ae68`.

## What the core difference changes
1. **Part B (the US re-import): nothing.** The new entry is keyed "New Mexico" and matches only that document name, so no federal bill, link or vote reads it. Part B and Part C stand as written.
2. **New Mexico, from v69 on:** the archiver marks a newly stored "Amendments in Context" document as not a bill version. It is kept as a document, out of the version list, the comparisons and LegBot's newest text.
   * NM's **already stored** documents change only through OPEN-637's own recompute release step, on its own GO. **Nothing here runs it.**
3. **api-v3 and ddp-sync must follow the image's core** (OPEN-586, SYNC-180). They are not yet rebuilt at `5c1455e1` per the notes on this branch, so build them **at `c983ae68` instead**, when each one's own GO comes:
   * **api-v3** (both hosts, request `05a7643` with addendum `abef131`): `DDP_CORE_SHA=c983ae68599e94494a94edc23d576b483922302e`. api-v3 imports core's version rules (OPEN-538), so it must be built at the image's core.
   * **ddp-sync** (request `125fc5e`, SYNC-180): `DDP_CORE_SHA=c983ae68599e94494a94edc23d576b483922302e`.
     * The import itself doesn't read this rule; this is so `check-core-pin-drift.py --sync-container` agrees with the live image.
     * The reason `125fc5e` gives for not using v67's core still holds; `c983ae68` contains `5c1455e1`.
   * The drift check (`check-core-pin-drift.py --image-core c983ae68599e94494a94edc23d576b483922302e --container ... --sync-container ...`) then expects one commit everywhere.

## Not authorized
* Anything beyond `5836c52`'s parts and the two requests named above.
* NM's recompute (OPEN-637's own GO).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
