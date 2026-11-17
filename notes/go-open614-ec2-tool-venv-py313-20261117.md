# GO: OPEN-614, move the EC2 host's tool venv to Python 3.13 (request `67f3236`). 2026-11-17 (Mac side)

**Ramon, 2026-11-17** (relayed by the PM session, then confirmed by Ramon to this session in a pop-up, "Yes, all three"): "Go". The runbook is merged: ddp-open-states #408 (RUNBOOK, "The EC2 production host's tool venv (OPEN-614)") is on main.

**Run it as the RUNBOOK section says**, from `/opt/ddp-open-states` on main (at or after `643f73d`, which carries #408):
1. Install uv 0.11.7 user-local, then `uv python install 3.13`.
2. Baseline on the old venv: `recompute-diff-order nv --dry-run --list` with the usual throwaway worktree of the **live image's core, `71fd44d61ce7f116a23933e29fbe9ea01372a99c` (v64)**, on `PYTHONPATH`, plus `validate_jurisdictions.py`.
3. `mv .venv .venv-py39`, then build `.venv` on 3.13 (`pip<24.1`, `--no-deps -r requirements-openstates.txt`, `--no-deps -e openstates-core`).
4. Repeat the same checks on the new venv, plus `rollout-manifest.sh --host ec2 --dry-run`.

**Gate:**
* the two dry-run change lists are identical;
* the summary lines match;
* the validator output matches;
* the rollout dry run exits 0.

**Timing:** now, with one real-reason rule: **not while one of your one-off passes or a manifest rollout is running** (they use this venv). Scrapes, ddp-sync and api-v3 don't use it.

**Rollback:** `rm -rf .venv && mv .venv-py39 .venv`. **Keep `.venv-py39`** until one real pass (a committed recompute or a manifest rollout) has run on the new venv; deleting it needs Ramon's go.

**Report:**
* the uv and Python versions;
* both summary lines;
* the diffs (empty or not);
* the rollout dry-run exit code;
* the time.

## Not authorized
Changing the core checkout's commit, any apt or system package, deleting `.venv-py39`, or any scrape, image, manifest, broker, ddp-sync or data change.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
