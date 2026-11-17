# REQUEST (waits on Ramon's go and on ddp-open-states #408 merging): move the EC2 host's tool venv to Python 3.13 (OPEN-614 step 3). 2026-11-17 (Mac side)

**Not a GO yet.** Thanks for the inventory (`1a2ff64`). The steps are the new RUNBOOK subsection "The EC2 production host's tool venv (OPEN-614)" in ddp-open-states #408. Once it's merged and Ramon says go, run it from `/opt/ddp-open-states` on main.

## In short
* **Install:** uv 0.11.7, user-local, then `uv python install 3.13`. No apt, and the system Python isn't touched.
* **Baseline on the old venv:** `recompute-diff-order nv --dry-run --list` (with the usual throwaway worktree of the **live image's core** on `PYTHONPATH`) and `validate_jurisdictions.py`.
* **Switch:**
  * `mv .venv .venv-py39`;
  * build `.venv` on 3.13 (`pip<24.1`, `--no-deps -r requirements-openstates.txt`, `--no-deps -e openstates-core`);
  * repeat the same checks, plus `rollout-manifest.sh --host ec2 --dry-run`.
* **Gate:**
  * the two dry-run change lists are identical;
  * the summary lines (corrected, nulled, errors) match;
  * the validator output matches;
  * the rollout dry run exits 0.
* **Rollback:** `rm -rf .venv && mv .venv-py39 .venv`.
* **Keep `.venv-py39`** until one real pass (a committed recompute or a manifest rollout) has run on the new venv.

## Rules
* Not while a one-off pass or a manifest rollout runs. Scrapes on Fargate aren't affected (no container mounts this venv).
* If `pip install -e openstates-core` refuses the checkout's Python range, stop and roll back. The checkout `5c79b47d` declares `^3.9`, so it should accept 3.13.
* Report: the uv and Python versions, the two summary lines, the diffs (empty or not), the rollout dry-run exit code, and the time.

## Not authorized
Changing the core checkout's commit, any apt or system package, any scrape, image, manifest, broker, ddp-sync or data change, or deleting `.venv-py39`.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
