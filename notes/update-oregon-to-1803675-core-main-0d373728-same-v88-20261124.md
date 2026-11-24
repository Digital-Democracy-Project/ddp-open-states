# UPDATE (not a GO) to `1803675`: core main is now **`0d373728`**, and Oregon's numbers are unchanged there. **Oregon rides in the same v88 image and the same core rollout as Onboard New States' list (`0ec8829`); there is no separate Oregon rollout.** 2026-11-24 (Mac side, State Specific Handling)

**Not a GO.** Everything in `1803675` stands. This note only changes its target commit and answers the one open question.

## What changes in `1803675`
* **Core target:** wherever `1803675` says `e9b90e67`, read **`0d373728ff8fd18308a689542b0ded7ec7d11d8b`** (core #156 merged on top). Oregon's fixes (#159 `a124a218`, #165 `e9b90e67`) are ancestors of it.
* **Same image, same rollout as `0ec8829`:**
    * Core, the scrapers image and api-v3 ship together, with one core per image (`check-core-pin-drift.py`). So **v88 is one image at one core, and one rollout** puts it on api-v3 (both hosts) and EC2 ddp-sync. It carries every core merge below, Oregon's two included.
    * **A requirement for whichever commit v88 is built from:** its `DDP_CORE_COMMIT` must contain `e9b90e67`. Check it first. `0d373728` does, and so does anything later on core main.
    * **If v88 is built before more core merges land,** that is fine. Oregon needs nothing else.
* **Order, unchanged:** v87 and its rollout (`cc1b14d`) stay as written. Ramon may skip straight to v88.

## Oregon's numbers, re-measured at `0d373728` (Mac replica, read-only)
* `os-text-extract relabel or --dry-run`: `actions changed=337 unchanged=3575 | bills changed=0`. That is 306 passage → none, 29 none → passage, 1 none → failure, 1 reading-3 → "reading-3, failure". `latest_passage_date=154`, the other computed fields 0.
* `os-text-extract recompute-diff-order or` dry run: `304 bills checked | unchanged=452 corrected=201 nulled=432`, `is_bill_version changed=433 not_a_version=433`, `diff_baseline_id changed=201 cleared=432`.
* **Identical to `1803675`'s expected lines.** The per-action labels (1,737 distinct Oregon rows) and the 159 version notes match the earlier results byte for byte.
* **The shared-code changes since `e9b90e67` don't touch Oregon:**
    * the voter-name matching (#153, importers) only runs on import and affects votes;
    * Nevada's "Reprint N" stage rule (`utils/version_ordering.py`): none of Oregon's 159 notes match it, and Oregon's version ordering is identical at both commits.
* So the Oregon steps (gates, relabel, recompute, the Mac count check, `validate_bill_stages --jurisdictions or`) are unchanged, and run on their own go after the v88 rollout.

## Whole-replica change at `0d373728` vs `59dbdaa2` (the live core)
* **Actions (885,960 stored):** 11,326 change. Maine 5,177; Hawaii 2,395; Rhode Island 2,222; North Dakota 520; Wyoming 427; **Oregon 337**; Kentucky 133; Montana 62; Missouri 53.
* **Version flags (46,208 note rows):** 1,363 documents change. Wyoming 845; **Oregon 433**; Idaho 56; Nevada 26; North Dakota 3.
* No other state changes in either measure. Each of those states has its own relabel or recompute step, on its own request and go. **Not authorized by this note:** any of them.

Tickets: OPEN-841, OPEN-846 (OPEN-536). Follows: `1803675`, `0ec8829`, `cc1b14d`.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
