# UPDATE: v65 is registered as `ddp-scrapers:68` (Ramon's go). It carries core `46cc5759` and scrapers `85df0af5`, later than note `e5d12b9` said. Checks now; the api-v3 rebuild is at `46cc5759`; no relabel is authorized. 2026-11-18 (Mac side)

Follows requests `59c62e0` and `e5d12b9`. **The registration is done.** Ramon built and pushed `ddp-scrapers:v65`, digest `sha256:bf3979ee…6706f6`, and it was registered at 03:51:14 UTC 2026-11-18 as task revision **68** (previously 67 = v64). **Do not register anything.**

## What v65 really carries
The image is built from each fork's main at build time, so it holds merges after `e5d12b9`'s expected commits:
| Repo | Commit in v65 | Since `e5d12b9`'s expected commit |
|---|---|---|
| openstates-core | **`46cc5759208b84343fef325fd8e263f7e58bb324`** (was expected `67f307ab`) | #124 `66cfb27c` Utah `classify_action` (OPEN-547); #125 `ddd24cf9` Michigan (OPEN-548); #126 `46cc5759` Virginia actions (OPEN-549) |
| openstates-scrapers | **`85df0af53653071c8218d4c10161c886b87a3e7a`** (was expected `5706b876`) | #128 Arizona: only Third and Final Reading roll calls are `passage`, decided from azleg's floor step (OPEN-625) |

* **No core database migration** since `67f307ab` (or since v64): `git diff --name-only 67f307ab 46cc5759` shows none.
* Every state above had its scorecard gate approved by Ramon on 2026-11-17 (ticket comments: OPEN-547 21272, OPEN-548 and OPEN-549 via the PM session, OPEN-625 "Approve, go").

## Which states' rules now apply to new imports
From the first task on revision 68, openstates-core's importer applies each state's own action-label rule (`openstates/ddp_states/<st>.py`) to every action it imports:
* **Nebraska** (OPEN-550), **Massachusetts** (OPEN-551), **Utah** (OPEN-547), **Michigan** (OPEN-548), **Virginia actions** (OPEN-549).
* **Virginia bill labels:** the scraper itself labels HR/SR `resolution` and HJ/SJ `joint resolution` (OPEN-545, already in `e5d12b9`).
* **Arizona:** the scraper labels only Third and Final Reading roll calls `passage` (OPEN-625). Arizona has **no** action rule yet: OPEN-552 (core #127) is held and not merged.

**What that means for stored data:** only bills a new scrape touches get the new labels, so each of these states' stored labels are mixed until its relabel runs. That is expected. **Read-only, in your next reports:** after each affected state's first run on revision 68 (va, ut and az on their weekly days; mi on Sunday), report its status and failed count, and any bill-stage or bill-event alert for that state that looks unusual. A label change on a re-imported bill can move its latest passage date.

## Authorized now (read only)
1. The next launched task reports revision 68 and image v65. Its `DDP_CORE_COMMIT` must be `46cc5759208b84343fef325fd8e263f7e58bb324`. A different value means a different image: stop and report.
2. The per-state first-run reports above.
3. Until the api-v3 rebuild below, expect `check-core-pin-drift.py` to report one disagreement (image `46cc5759` against api-v3 at its current core). That is expected: report it and leave it.

## The api-v3 rebuild (step B of `59c62e0`, changed core)
* **`DDP_CORE_SHA=46cc5759208b84343fef325fd8e263f7e58bb324`**, replacing `67f307ab` in `e5d12b9`. Everything else in `59c62e0` step B and `e5d12b9` §3–4 stands:
  * EC2 skips step A (it already has the `chambers` block);
  * the Mac runs `rollout-manifest.sh --host mac` before its own rebuild;
  * tag `pre-v65` for rollback;
  * gate: `/healthz` 200, `/ddp/enrollment` 200, and `check-core-pin-drift.py --image-core 46cc5759208b84343fef325fd8e263f7e58bb324 --container ddp-openstates-api-1` exits 0.
* **api-v3 #71 (OPEN-556) and #72 (OPEN-557) are still unmerged and held** (checked 2026-11-18). This rebuild includes neither. If api-v3 main contains either branch at build time, stop and report.
* The rebuild still waits on Ramon's explicit go, as before.

## Not authorized
* **Any relabel or stored-data change:** `os-text-extract relabel` for ne, ma, ut, mi or va, and Arizona's 24-vote `backfill-motion-classification.py --apply-list`. Each runs later in its own silent window, with its own request and Ramon's go.
* Registering anything, extra scrapes, any manifest, broker or ddp-sync change.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
