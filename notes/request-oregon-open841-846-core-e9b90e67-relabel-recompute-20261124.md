# REQUEST (not a GO): Oregon's action labels (OPEN-841) and amendment papers (OPEN-846). Core main is now `e9b90e67`, ahead of v87's `d5e548e8`. It goes out with the **next image (v88)** and the core rollout at v88's core. Then `relabel or`, `recompute-diff-order or` and `validate_bill_stages --jurisdictions or`. 2026-11-24 (Mac side, State Specific Handling)

**Not a GO.** Each step waits on Ramon's go in your session. Each write needs its own go, naming the dry run's count.

## What changed in core since v87 (`d5e548e8`)
Core main = **`e9b90e671cd9654516ebcb1e0274b900a8750c42`**. Exactly two merges since `d5e548e8`, both Oregon only, **no migration**:

| PR | Merge | Ticket | What it does |
|---|---|---|---|
| #159 | `a124a218` | OPEN-841 | Oregon's `classify_action` (`ddp_states/or.py`). "Speaker signed." and "President signed." lose `passage`. A bare "Passed.", a special-order adoption, and "House/Senate concurred in ... amendments and repassed bill." gain `passage` (Ramon). A floor line ending "Failed." gains `failure` (Ramon). |
| #165 | `e9b90e67` | OPEN-846 | 433 Oregon committee amendment papers and minority reports ("House Amendments to Introduced", "HED Amendment -A2") are **not bill versions** (`ddp_states/or.py`). |

* The Mac compared every state's actions (885,960) and every (state, note) pair (45,924) on the replica. **Only Oregon changes.**
* Oregon's code at `e9b90e67` is byte-identical to the tree those measurements ran on (`63dab69a`). The only other difference is #162 (North Dakota), which is already in v87.

## 1. Is a new scrapers image needed? **Yes: v88.**
* The rule (PRIMITIVES `check-core-pin-drift.py`, OPEN-586): core, the scrapers image and api-v3 ship **together**. api-v3 is built at the live image's core.
* v87's image carries `d5e548e8`. Rolling api-v3 and ddp-sync to `e9b90e67` under v87 would:
  * fail the drift check;
  * split Oregon: imports and archives in the image would write the old labels and versions, while the hosts' tools wrote the new ones.
* So **Ramon builds v88 from core main** (`e9b90e67` or later). It carries whatever else is merged by then: Onboard New States' running list decides its contents, for example WY core #150/#160 and the HI/MS/MO/KY/MT/MD/ME/WA scraper fixes.

## 2. How this relates to `cc1b14d` (v87, core rollout at `d5e548e8`)
**It follows `cc1b14d`; it does not replace it.**
* v87 and its core rollout at `d5e548e8` stay as written. That rollout isn't done yet: your `69c817a` lists it as waiting for Ramon's go.
* North Dakota's `refresh-extraction nd` follows that rollout, as before.
* This request adds **one later rollout, at v88's core**, the same steps as `cc1b14d` step 1 with v88's commits:
  * **EC2 api-v3:**
    * rollback tag;
    * `DDP_CORE_SHA=<v88 DDP_CORE_COMMIT>`;
    * `up -d --no-deps api`;
    * not 05:00–07:00 UTC.
  * **EC2 ddp-sync:**
    * rebuild with `DDP_CORE_SHA=<v88 core>` and `DDP_SCRAPERS_SHA=<v88 scrapers>`. The import check must pass;
    * rollback tag;
    * post the in-flight list, and wait for any loading run;
    * `up -d --no-deps`.
  * **Mac api-v3:** `refresh-api-v3.sh` with `SCRAPERS_IMAGE_CORE=<v88 core>`, Mac side, after your note.
  * **Check:** `check-core-pin-drift.py --image-core <v88 core>` exits 0 everywhere.
* **If Ramon prefers one rollout:** v88 is built before the `d5e548e8` rollout has run, so he may skip straight to v88's core.
  * North Dakota's refresh then simply follows v88's rollout.
  * That is his call, in your session. Either way, **v88's `DDP_CORE_COMMIT` must contain `e9b90e67`**: check it before anything below.

## 3. Oregon, after the v88 rollout (each part on a go)
**Gates (stop and report if one fails):**
1. The v88 rollout is done:
   * the drift check exits 0;
   * ddp-sync reports v88's core. Otherwise Oregon's next import writes the old labels back.
2. **Oregon's quiet window (the OPEN-546 rule):**
   * no `or` scrape, collection, load or archive running (the ECS check, and `GET ddp:pipeline_lock:or` empty);
   * no bill-event check queued;
   * `recheck_requested` false.
3. **The tool at v88's core:** in the ddp-sync container after the rollout (as for the Kentucky recompute in `fc52632`), or in a throwaway worktree on `PYTHONPATH` with the host venv (as for `relabel az`).

### 3a. `relabel or` (OPEN-841)
**Dry run (read-only):** `os-text-extract relabel or --dry-run --list <lasting path>/relabel-or-dry-rds.csv`.

**Expect** (the Mac replica, read-only, core at #159's final head; Oregon's newest replica row is 2026-11-17):
```
or: [DRY RUN] actions changed=337 unchanged=3575 | bills changed=0 unchanged=0
  action: passage -> (none): 306
  action: (none) -> passage: 29
  action: (none) -> failure: 1
  action: reading-3 -> reading-3, failure: 1
  bills whose computed fields would change: first_action_date=0 latest_action_date=0 latest_action_description=0 latest_passage_date=154
```
* The 306 are the presiding officers' signatures: 153 Speaker, 153 President.
* The 29 are:
  * 23 repassage lines (Ramon: "Count as passage");
  * 5 bare "Passed.";
  * 1 special-order adoption.
* The 2 failures are HB 4098's 28–30 third reading and its bare "Failed." Ramon decided this on 2026-11-24. The bare line has no roll call of its own: it records the failure becoming final.

**Stop rules:**
* any change kind not listed above, or any bill-label change: stop;
* far more than 337: stop;
* a little different (RDS re-scraped Oregon since the Mac copy): report it, and the GO names the count.

**Commit (on a GO naming the count):**
* `os-text-extract relabel or --commit --expect <count> --list <lasting path>/relabel-or-committed.csv`. It is all-or-nothing; don't retry with a different `--expect`.
* **Check:** a second dry run reports `actions changed=0 | bills changed=0`.
* **Rollback, only if Ramon asks:** `os-text-extract relabel or --undo <lasting path>/relabel-or-committed.csv --commit --list <lasting path>/relabel-or-undone.csv`.

### 3b. `recompute-diff-order or` (OPEN-846)
**Dry run (read-only):** `os-text-extract recompute-diff-order or`. Post the three lines.

**Expect** (Mac replica, same tree):
```
or: [DRY RUN] 304 bills checked | unchanged=452 corrected=201 nulled=432
or: [DRY RUN] is_bill_version: set=0 changed=433 not_a_version=433
or: [DRY RUN] diff_baseline_id: set=0 changed=201 cleared=432
```
* The 433 documents are amendment papers and minority reports, now not versions.
* The 432 are their comparisons, removed. One paper ("HREV Amendment -A17") has no comparison stored.
* The 201 are real texts re-pointed at the text before them: every A-Engrossed (155) and 46 Enrolled are compared against a paper today.

**The Mac count check:** I compare your three lines with the Mac's and reply on this branch before the commit's go.
* A difference only from Oregon bills re-scraped since 2026-11-17 is fine.
* Anything else is a stop.

**Commit (on a GO):** `os-text-extract recompute-diff-order or --commit --list <lasting path>/recompute-or-committed.csv`, the same way as the Kentucky commit in `fc52632`. There is no `--expect` here: it goes only with `--baseline-only`. Then a second dry run should show `corrected=0 nulled=0`.

### 3c. `validate_bill_stages --jurisdictions or` (OPEN-841 acceptance line 4; read-only, broker host)
* Run it after the broker's next Oregon sync: the relabel moves `updated_at` on up to 154 bills, and the broker re-reads them.
* **Before** (dev broker, a production copy, broker `1ea84b14`): `first_passage_not_by_origin_chamber=3`, `passed_both_without_passed_one=3`.
* **Expect after:**
  * both counts **0**;
  * "Passed both chambers" about **153** bills;
  * HB 4098 ends "Failed" instead of "In committee".
* Post the full output. Any count above 0 is reported, not fixed.

## Not authorized
* Any other state's relabel or recompute.
* Any re-import.
* The Wyoming steps: they wait for core #150/#160 and their own request.
* Anything on the broker beyond the read-only command.

Tickets: OPEN-841, OPEN-846 (OPEN-536). Plan: PLAN-state-specific-handling. Follows: `cc1b14d`.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
