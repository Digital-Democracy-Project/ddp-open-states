# REQUEST (each real change on its own go from Ramon): Utah's stored history. `relabel ut` (OPEN-547: 1,412 actions), then `fix-ut-vote-chamber.py` (OPEN-622: 1,172 actions on 696 bills). Dry runs first. 2026-11-18 (Mac side, State Specific Handling)

**Not a GO for any write.** Ramon, 2026-11-18 (OPEN-622 comment 21512): "Write the requests now". Dry runs come first and Ramon reads their numbers; each real change gets its own go, in Utah's quiet window.

## What and why
* **`relabel ut` (OPEN-547)** applies Utah's label rule (core `openstates/ddp_states/ut.py`, in image v68's core `5c1455e1`) to stored actions.
  * It writes only `classification`.
  * Measured: **1,412 actions change, 0 bills.**
  * The rule now keeps `passage` on "<chamber> Conference Committee - Final Passage" lines (Ramon: "Fix the rule first").
* **`fix-ut-vote-chamber.py` (OPEN-622)** moves Utah's stored floor-vote lines to the chamber that voted. It writes only `organization_id`.
  * Covered lines: passage, concurrence and refusal to concur, "failed", conference Final Passage.
  * Before, they sat under the chamber the bill went to next. New scrapes already store them correctly since v68 (scrapers #131, `dca8e7a6`).
* **Scorecards:** once Utah's broker switch (BROKER-491, ddp-broker-py #767) is live, which Utah votes count does not depend on these runs (Ramon's note; on the vote-event basis 0 votes changed in OPEN-622's gate).
  * Their purpose is clean stored data, and letting BROKER-490 delete the broker's Utah reader.
  * OPEN-622's table: after both runs, 0 bills read as "passed both chambers" wrongly with that reader switched off.

## Measured on the Mac replica of RDS (22:34 UTC 11-18, read-only, image v68)
| Run | Result | List |
|---|---|---|
| `os-text-extract relabel ut --dry-run` | `actions changed=1412 unchanged=35928 \| bills changed=0`. Changes: passage → none 1,088; none → passage 230; failure → none 51; executive-receipt → none 36; "amendment-failure, failure" → "amendment-failure" 7. `latest_passage_date` would change on **555** bills; the other computed fields 0 | `notes/open547-relabel-ut-dry-run-mac-20261118.csv` (this branch), 1,412 rows, md5 `c16df52ec9f754d32f89132ddd3f1158` |
| `fix-ut-vote-chamber.py` (dry run) | 37,340 Utah actions read. **1,172 actions on 696 bills**: House 3rd reading 522, Senate 3rd reading 258, Senate 2nd & 3rd/suspension 150, House concurs 129, Senate concurs 85, House refuses 11, House conference final passage 10, Senate refuses 4, Senate conference final passage 2, Senate failed 1 | Identical to the reviewed list on ddp-open-states main, `notes/open622-ut-vote-chamber-dry-run-20261118.csv`: 1,172 rows, the same 1,172 action ids, md5 `fe186ec9c7ef3a253d3f9231cb73bbc4` |

**Order: `relabel ut` first, then `fix-ut-vote-chamber.py`.** The tool's chamber fix was rehearsed after a relabel (OPEN-622). Each step only moves forward on its own go.

## Gates (all, before any write; stop and report if one fails)
1. **ddp-sync's importer runs core `5c1455e1` or later** (SYNC-180, request `125fc5e`): your checkpoint shows `check-core-pin-drift.py --sync-container` exit 0.
   * **Why:** cloud imports apply the label rule with ddp-sync's own core. On the old core (`44c3b8dc`), the next Utah import writes the old labels back on every bill it re-imports.
   * The chamber fix needs only v68's scraper, already registered (rev 71).
2. **Utah's broker switch is live** (ddp-broker-py request `f49bc6c8`, which replaced `5da5c42c`; it carries #767), so these runs change no counting vote.
   * If Ramon wants them before it, say so in the GO. OPEN-622's gate measured 23 vote changes on the old basis.
3. **Utah's quiet window:**
   * No `ut` scrape, collect or import running (ECS check, and no `os-update` for ut in ddp-sync).
   * Not during Utah's weekly run (Tuesday 12:00 UTC start). A run landing mid-write makes the tools' guards roll the whole write back: harmless, but report it.
4. `/opt/ddp-open-states` is at or after `2bb68bf2` (#422).

## Part 1: dry runs (read-only; on your go for this part)
**A. Relabel:** `os-text-extract relabel ut --dry-run --list <lasting path>/relabel-ut-dry-rds.csv`, with core `5c1455e1` (image v68), the same way as the NM recompute in `05a7643`. Report:
* the summary line and the old → new counts;
* the "bills whose computed fields would change" line;
* the list's row count.

Expect **1,412 actions, 0 bills**, and the breakdown above.

**B. Chamber fix:** `PGOPTIONS='-c default_transaction_read_only=on' python3 fix-ut-vote-chamber.py --list <lasting path>/fix-ut-dry-rds.csv`, with the Utah scraper `dca8e7a6` on the path.
* The Mac ran it in image v68 with `PYTHONPATH=/opt/openstates-scrapers/scrapers` and the checkout mounted.
* Expect **1,172 actions on 696 bills**, and the same action ids as the reviewed list.

**Stop rules for both:**
* **Fewer** than expected: rows changed since the list was made. Stop and report the difference and the first missing id.
* **A few more** than expected (new Utah imports since 11-18): report them and continue to Part 2 **only** if the GO names the new count.
* **Any bill label change** from relabel (expected 0): stop.

## Part 2: relabel ut (on a GO naming the count)
1. Run `os-text-extract relabel ut --commit --expect <count from the GO, 1412 if unchanged> --list <lasting path>/relabel-ut-committed.csv`.
   * It is all-or-nothing: an item changed underneath, or a count other than `--expect`, rolls back with nothing written.
   * Do not retry with a different `--expect`.
2. **Check:** a second dry run reports `actions changed=0 | bills changed=0`.
3. **Rollback, only if Ramon asks:** `os-text-extract relabel ut --undo <lasting path>/relabel-ut-committed.csv --commit --list <lasting path>/relabel-ut-undone.csv`.

## Part 3: fix-ut-vote-chamber.py (on its own GO, after Part 2)
1. Run `python3 fix-ut-vote-chamber.py --apply-list notes/open622-ut-vote-chamber-dry-run-20261118.csv --commit --expect 1172 --list <lasting path>/fix-ut-committed.csv`.
   * Check the list's md5 against the one above first.
   * The tool writes exactly the reviewed list and does not re-run the rule. A row whose organization or text changed aborts the whole run.
   * If Part 1B found more than 1,172 and the GO approved them, the GO names how to apply the extra rows. Never `--commit` without `--list`.
2. **Check:** a second dry run finds 0 to move.
3. **Rollback, only if Ramon asks:** `python3 fix-ut-vote-chamber.py --undo <lasting path>/fix-ut-committed.csv --commit --list <lasting path>/fix-ut-undone.csv`.

## After (read only)
* The broker's next Utah sync (both runs move `updated_at` on the touched bills: 555 and 696).
* The scorecard chain, then `validate_scorecards --jurisdiction UT --all`, `validate_scorecards --bills` and `reconcile_scorecards` for UT.
  * Expect 0 discrepancies and no Utah scorecard entry changed (on the vote-event basis).
  * Report HB 136's bill score (50).
* Then `validate_bill_stages --jurisdictions ut`. It is the input for BROKER-490 (deleting the broker's Utah reader), which is not part of this request.

## Not authorized
* Writes before their GO.
* Any other state's relabel.
* BROKER-490.
* Rebuilding either list on the prod host for Part 3: the reviewed list is what is written.
* Extra scrapes.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
