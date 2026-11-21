# UPDATE (not a GO): the three stored-vote backfills that waited for the new scrapers image, retargeted to v74. Each part waits on Ramon's go in your session. 2026-11-20 (Mac side, State Specific Handling)

This **updates** `7822bf0` (OPEN-685 request 2, `notes/request-open685-2-backfill-ne-la-nm-20261120.md`) and **`c7be369` Part B** (B1 OPEN-627, B2 OPEN-628). Their steps are unchanged; what changes is the image they wait for (v74) and the counts, re-measured tonight. `c7be369` Part A (v67) and OPEN-685 request 1 (the image) are done by v74.

**Added 2026-11-20 (after `b85ce25`): unaffected by OPEN-640.** openstates-core #135 (migration `data.0052`) merged afterwards as `1c367db5`. v74 is built at core **`83584c48`**, before that merge, so nothing here needs the new column and nothing here changes. The 0052 release has its own request: `notes/request-migration-0052-relation-label-open640-20261120.md`.

## Gates (all parts)
* **The image.** Confirm from ECS that the current scrapers task definitions are **v74**: `ddp-scrapers:76` and `ddp-scrapers-db:3`, core `83584c48`, scrapers `ad33d76b`. This note's author has not seen a prod note for v74; it comes from the PM session, which says Ramon registered it tonight.
  * v74 carries the scraper side of all three: OPEN-685's NE/LA/NM numbers (scrapers #140, `bcaf1447`), OPEN-627's results (`7fa39511`) and OPEN-628's AZ/VA keys (`78df858a`). All are checked as ancestors of `ad33d76b`.
  * So new votes already arrive right, and these runs only fix what is already stored.
* **The tools:** `/opt/ddp-open-states` at or after **`a6be4264`**. It contains `backfill-vote-rollcall-num.py` with NE/LA/NM (#435) and `backfill-motion-classification.py --result` (#421). If the live checkout is behind, use a worktree of main, as you did for OPEN-712 (`20485e4`), with the same `openstates-scrapers` symlink.
* **No scrape or import task running** for the state of the part (ECS check).
* The three parts touch different columns or states; their order does not matter. Each tool is all-or-nothing, with `--expect`.

## Re-measured tonight on the Mac replica of RDS (current `main` tools)
| Part | State | Mac dry run | Same as the original request |
|---|---|---|---|
| 1 | Nebraska | 1,772, 0 unreadable | yes |
| 1 | Louisiana | 3,172 (House 1,624, Senate 1,548), 0 unreadable | yes |
| 1 | New Mexico | 0 readable on the host (259 left), 2 by the Mac list | yes |
| 2 | Arizona results (OPEN-627) | 44, the **same 44 ids** as the reviewed list | yes |
| 3 | WA, MI (OPEN-628, readable on the host) | WA 2,302 (House 1,201, Senate 1,101), MI 937 (House 553, Senate 384) | yes |
| 3 | The whole 12,851-row list | 0 of its votes already carry a number, and 0 have disappeared | the list still applies as it stands |

## Part 1: OPEN-685, Nebraska, Louisiana and New Mexico vote numbers
The steps are exactly those of `notes/request-open685-2-backfill-ne-la-nm-20261120.md`. In short:
* **Nebraska:**
  * `python3 backfill-vote-rollcall-num.py --dry-run --jurisdiction ne --list <lasting>/open685-ne-dry.csv`. Expect **1,772 or a few more**, 0 unreadable.
  * Then `--apply-list <that file> --expect <its count> --list <lasting>/open685-ne-committed.csv`.
  * Then a second dry run: 0 to write.
* **Louisiana:** the same, with `--jurisdiction la`. Expect **3,172 or a few more**, 0 unreadable.
* **New Mexico:**
  * `--dry-run --jurisdiction nm` must write 0.
  * Then `--apply-list notes/open685-nm-vote-rollcall-num-list-20261120.csv --expect 2 --list <lasting>/open685-nm-committed.csv`. That list's md5 is `0b0168c0381010c46ae15e5f4497888a`. Do not rebuild it.
* **Undo (only if Ramon asks):** `--undo <committed list> --expect <its count> --list <lasting>/open685-<st>-undone.csv`.
* **Then Nebraska's switch:** the broker note `74425d22` (ddp-broker-py `notes/ops-handoff`). Its read-only check (every Nebraska vote numbered; LB 48 holds 12956 then 12957) comes first, then `migrate common 0106`, then `backfill_eligible_for_scorecard --jurisdiction NE --fresh-responses`: at most 5 fewer counting, none more.
* Louisiana's and New Mexico's broker recounts are no-ops: your `233407bc` found 0 motions for them on the broker.

## Part 2: OPEN-627, Arizona results (44 votes)
The steps are exactly `c7be369` B1:
* **The list:** `notes/open627-az-vote-result-dry-run-20261118.csv` on ddp-open-states **main**, md5 `d7c88dbf0cf293b4b56c3d2bd59fa9bb`.
* **Step 1, dry run:** `python3 backfill-motion-classification.py --result --dry-run --list <lasting>/open627-rds-dry-run.csv`. Expect **44**, the same 44 ids as the list: `diff <(cut -d, -f1 <list> | sort) <(cut -d, -f1 <dry run> | sort)` prints nothing. Any other count or id means stop and report.
* **Apply:** `--apply-list <the list> --expect 44 --list <lasting>/open627-committed.csv`.
* **Check:** a second dry run expects 0.
* **Undo (only if Ramon asks):** `--undo <lasting>/open627-committed.csv --list <lasting>/open627-undone.csv`.
* **Effect:** what pages show. No vote starts or stops counting.

## Part 3: OPEN-628, vote order for WA, MI, VA, AZ (12,851 votes)
The steps are exactly `c7be369` B2:
* **The list:** `notes/open628-vote-rollcall-num-list-20261118.csv` on this branch, md5 `ce2344aa401b9f6ac531feee3ff148e7`.
* **Step 1, dry run:** `python3 backfill-vote-rollcall-num.py --dry-run`, with no `--az-cache` or `--va-votes`. Expect **mi 937** and **wa 2,302**; AZ and VA show as "not readable", as intended.
  * The same dry run also lists NE and LA. If Part 1 has not run yet, ignore them; they are Part 1's.
  * A small surplus is new votes since the list. A shortfall means stop.
* **Apply:** `--apply-list <the list> --expect 12851 --list <lasting>/open628-committed.csv`. It writes only votes with no number yet; one that has a number aborts the whole run with nothing written.
* **Check:** a second apply is refused or writes 0.
* **Undo (only if Ramon asks):** `--undo <lasting>/open628-committed.csv --expect 12851 --list <lasting>/open628-undone.csv`.
* **Effect:**
  * The broker's next scheduled sync of each of WA, MI, VA and AZ stores `Motion.rollcall_num`; report the first one for each.
  * Washington: 21 earlier same-day votes stop counting. Only SB 6346 is polled, and its scorecard is unchanged (OPEN-685, Jira comment 21803).

## After Parts 2 and 3: Arizona (read only for you)
These two runs, with OPEN-712 (done, `20485e4`), are the three preconditions of Arizona's scorecard switch (broker #789, migration 0107).
* The Mac side re-measures Arizona's list on the replica once both have replicated, and takes it to Ramon.
* **Nothing for Arizona's switch is authorized here.**

## Report back
For each part: the dry-run counts (and the id diff for Part 2), the applied count, the second check's 0, the committed list's lasting path, and the time in UTC.

## Not authorized
* Any broker change other than Nebraska's steps in `74425d22`, and those only on their own go.
* Arizona's switch (#789).
* Rebuilding or editing any list on the host.
* Scrapes, manifest, ddp-sync or api-v3 changes.
* OPEN-640 (core migration `data.0052`): not part of this note.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
