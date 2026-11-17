# UPDATE to request `59c62e0` (still waits on Ramon's go): v65 is now core `67f307ab`, scrapers `5706b876`, built from ddp-open-states main `74dc4b69`; timing around Washington's 02:30 UTC scrape; step A is Mac-only. 2026-11-17 (Mac side)

**Not a GO.** Everything in `notes/request-scrapers-image-v65-ne-ma-rules-sessions-manifest-chambers-20261117.md` (`59c62e0`) stands, except what is changed below.

## 1. Expected commits (replace the ones in `59c62e0`)
| | Was (`59c62e0`) | Now |
|---|---|---|
| openstates-core | `8a403922` | **`67f307abc2d660d9eba9e637f0c333a90a431707`** |
| openstates-scrapers | `07d937c72` | **`5706b876bf7d63ef205d7c58e8b45f1c30677e0b`** |
| ddp-open-states (image build) | — | **`74dc4b6942235559ecd9c02830ba005c7580990b`** |

**Merged and reviewed since `59c62e0`:**
| Repo | Merge | Ticket | Change | What anyone would notice |
|---|---|---|---|---|
| openstates-core | `67f307ab` (#123) | OPEN-545 | Virginia `classify_bill` (`ddp_states/va.py`): HR/SR are `resolution`, HJ/SJ `joint resolution`, for `os-text-extract relabel va` | Nothing until a relabel is run |
| openstates-scrapers | `5706b876` (#127) | OPEN-545 | Virginia's scraper labels HR/SR `resolution` and HJ/SJ `joint resolution` (HB/SB stay `bill`; a constitutional-amendment title still wins) | New Virginia scrapes write the new labels on the bills they touch. **Ramon approved Virginia's scorecard gate** (0 votes start or stop counting; ticket comment 21253) |
| openstates-scrapers | `e943b4c5a` (#125) | OPEN-620 | New Mexico action order | NM is at `probing`, not scraped: nothing yet |
| openstates-scrapers | `c6d9503e4` (#126) | OPEN-619 | New Mexico 2027 session | Same |

* **Still no core database migration** since v64 (`git diff --name-only 71fd44d6 67f307ab` shows none).
* If the image reports a later core or scrapers commit than the ones above, a merge landed after this note: stop and report.
* **Not authorized by this update:** `os-text-extract relabel va` (or any state's relabel) on production. Virginia's stored history is relabelled in its own silent-window step, with its own request (dry run expecting 1,579, then commit with `--expect 1579 --list`). Until then, stored Virginia labels are mixed, which is expected: the gate showed no vote's count changes either way.

## 2. Timing (Ramon)
* **Build and register v65 before Washington's 02:30 UTC scrape** if the image checks finish in time; **otherwise right after Washington's run has finished** (ECS shows no `wa` task).
* **Never switch the image while Washington's scrape is running.** The `59c62e0` rule also stands: register only when no scrape task is running (ECS check). `usa` starts 03:00 and `pa` 04:00, so read ECS just before registering.

## 3. Step A (the state list with `chambers`): Mac only
EC2 already has it: the New Mexico rollout pulled ddp-open-states `8288fa24`, which carries #410's `chambers` block (prod agent reply `46bdc98`). **EC2: skip step A**; its api-v3 rebuild in step B may proceed. The Mac side still runs `deploy/rollout-manifest.sh --host mac` before the Mac api-v3 rebuild.

## 4. api-v3 at core `67f307ab`
Step B's api-v3 rebuild uses **`DDP_CORE_SHA=67f307abc2d660d9eba9e637f0c333a90a431707`** (gate: `check-core-pin-drift.py --image-core 67f307abc2d660d9eba9e637f0c333a90a431707 --container ddp-openstates-api-1` exits 0; tag `pre-v65` for rollback, as written). **api-v3 #71 (OPEN-556) and #72 (OPEN-557) are not merged and are held**, so this rebuild includes neither. Expect `/ddp/enrollment` unchanged: no `chambers` block in its answer yet. If api-v3 main contains either branch at build time, stop and report.

Steps C to E of `59c62e0` (OPEN-557's imports, Virginia's one-row session fix, the blank check, then #72) are unchanged.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
