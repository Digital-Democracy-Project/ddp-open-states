# GO: North Carolina people load on production, removing three stop-gap joined-up names (OPEN-613, people #28). After NC's current run finishes. 2026-11-18 (Mac side)

**Ramon, 2026-11-18 (/ask-me):** "Go after NC's run".

**Why:**
* Before the vote-name reader was fixed (OPEN-234), the people fork carried joined-up other names so NC votes stayed linked: "CarsonSmith", "CharlesSmith", "vonHaefen".
* people #28 (merged `4b644faf`) removes them.
* On the Mac replica (13:40 UTC 11-18), NC votes use only the spaced names ("Carson Smith", "Charles Smith", "von Haefen"), 814 rows each, all linked. So nothing depends on the joined spellings.

## What I need from you
1. **Gate:** NC's run `nc-b9ac274ee86a` (started 12:00 UTC on revision 68) has finished, including its archive. Nothing for `nc` is running.
2. Pull `/opt/ddp-open-states/people` to main; it must include `4b644faf` (people #28). If main is behind that, stop and report.
3. `os-people` from the container's `/opt/venv-openstates/bin/os-people`, `--safe` first, as for Georgia on 11-17 (`a713124`), then the load for **nc** only.
4. **Gate (CORRECTED 13:55 UTC):** 0 created. **Four** people updated:
   * Carson Smith, Charles Smith and Julie von Haefen (people #28 removes their joined-up names);
   * **Beth Gardner Helfrich** (people #22, OPEN-233, merged 11-15 as `f2e95091`, adds her plain "Helfrich" other name; it has never been loaded into NC).

   No "went missing" or retirement line. Anything else: stop and report.
5. Report the load's output and the time. No scrape for this.

## Separate finding, not part of this go (corrected)
On the replica, 814 NC 2025 votes are unlinked:
* **809 are "Helfrich",** since January 2025. NC has one Helfrich (Beth Gardner Helfrich), but other states' people named Helfrich now exist.
* **5 are "Tillett",** from yesterday.

* **Helfrich is OPEN-611's sixth case.** This load adds her other name, so new imports link her. The 807 stored votes are then filled by `relink-blank-voters.py --state nc`, which is **not** authorized here: it stays under the scorecard gate, with its own dry-run list and go.
* **Tillett is the same pattern.** Senator since 2026-09-03; his other names lack the bare "Tillett". It needs a people change first; it is added to OPEN-611 and not part of this load.

## Not authorized
Any scrape, image, manifest, ddp-sync, broker or data change other than this people load; any other state.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
