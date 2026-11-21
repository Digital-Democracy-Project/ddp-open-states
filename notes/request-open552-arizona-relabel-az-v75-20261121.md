# REQUEST (not a GO for any write): Arizona's stored history, `relabel az` (OPEN-552, core #127 `948be01b`, in v75's core `7f531958`). Dry run first. 2026-11-21 (Mac side, State Specific Handling)

**Not a GO for any write.** Ramon approved Arizona's list and gave his go (OPEN-552 comment 22255, "Approve and go"). The real write still runs on a GO naming the dry run's count, as for Utah (`649afd2`).

## What and why
* `os-text-extract relabel az` applies Arizona's label rule (core `openstates/ddp_states/az.py`, #127) to stored actions.
  * The bare "FAILED" line loses `failure`. That line names no motion, and a failed third reading is often reconsidered and passed.
  * It writes only `classification`.
* **Measured on the Mac replica (2026-11-21, read-only):** **175 actions on 152 bills, 0 bills' labels.**
  * 107 go from `failure, reading-3` to `reading-3`, and 68 from `failure` to no label.
  * The bills' computed fields: 0 change.
* **Scorecards:** 0 votes start or stop counting, and 0 scorecard files change. Measured on a dev copy at broker `92fe8bdf`, after Arizona's switch to vote events (0107), which no longer reads action labels.
* **Bill stages:** the broker's Arizona reader (`_read_arizona`) still drops the same label when it reads, so the stages read the same (OPEN-552 measured 0 bills differ). After this, BROKER-490 can remove that reader.
* **v75's new Arizona imports already apply the rule** (ddp-sync's core after step 4), so the dry run may show slightly **fewer** than 175 if Arizona bills were re-imported since.

## Gates (all, before any write; stop and report if one fails)
1. **Step 4 of `1f1e692` is done:** ddp-sync is at core `7f531958`, and the drift check exits 0.
   * **Why:** with ddp-sync on the old core, Arizona's next import writes the old label back on every bill it re-imports.
2. **Arizona's quiet window:** no `az` scrape, collection or load running (ECS check, and `GET ddp:pipeline_lock:az` empty). Not during Arizona's scheduled run.
3. **The tool at core `7f531958`:** in a throwaway worktree on `PYTHONPATH`, with the host venv, as for the Utah relabel and the 0052 migration.

## Part 1: dry run (read-only; on your go for this part)
`os-text-extract relabel az --dry-run --list <lasting path>/relabel-az-dry-rds.csv`. Report:
* the summary line and the old → new counts;
* the "bills whose computed fields would change" line;
* the list's row count.

**Expect** `actions changed=175 … | bills changed=0` (or fewer, see above): 107 `failure, reading-3 -> reading-3` and 68 `failure -> (none)`; computed fields all 0.

**Stop rules:**
* **More than 175,** or any change that is not one of those two, or any bill label change: stop and report.
* **Fewer than 175:** report the count; the GO names it.

## Part 2: relabel az (on a GO naming the count)
1. `os-text-extract relabel az --commit --expect <count from the GO> --list <lasting path>/relabel-az-committed.csv`.
   * It is all-or-nothing; do not retry with a different `--expect`.
2. **Check:** a second dry run reports `actions changed=0 | bills changed=0`.
3. **Rollback, only if Ramon asks:** `os-text-extract relabel az --undo <lasting path>/relabel-az-committed.csv --commit --list <lasting path>/relabel-az-undone.csv`.

## After (read only)
* The write moves `updated_at` on up to 152 bills, so the broker re-syncs them on its next Arizona sync.
* **Bill events:** for Arizona in the hours after that sync, **0** stage-change events are expected, because the broker's reader gives the same stage. Report the count; any event is a stop for BROKER-490.
* **Scorecard checks after that sync:** `validate_scorecards --jurisdiction AZ --all`, `validate_scorecards --bills --all`, `reconcile_scorecards --jurisdiction AZ`.
  * Before, on the dev copy: 107 legislators, 4,827 votes, 0 discrepancies; reconcile 0 missing.

## Not authorized
Any other state; BROKER-490 (its own release, `/broker-deploy`).

Tickets: OPEN-552, OPEN-536. Plan: PLAN-state-specific-handling §6.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
