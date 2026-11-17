# Reply to 67f323608: EC2 tool venv moved to Python 3.13 (OPEN-614 step 3), every gate met, old venv kept

Written 18:16 UTC (date -u at write time). From the production EC2 host. User's words in session: "I appove these requests. GO". The host checkout stays at 487c06f6d (I did not pull to main, so it does not carry the RUNBOOK text; #408 is merged on main 643f73dd8 and I followed it from there). No pass or manifest rollout was running (checked first); evidence in /home/bitnami/ops/step-open614-20261117/.

- **uv and Python:** uv 0.11.7 installed user-local under /home/bitnami/.local/bin (I downloaded the pinned installer to a file and read its first lines before running it; UV_NO_MODIFY_PATH=1 so no shell profile was edited). `uv python install 3.13` gave **Python 3.13.13** at ~/.local/share/uv/python/cpython-3.13-linux-x86_64-gnu/bin/python3.13. No apt, system Python untouched.
- **Baseline on the old 3.9.2 venv (18:14:26):** `recompute-diff-order nv --dry-run --list` with the live image's core worktree (b5728c43, v63) on PYTHONPATH: "27 bills checked | unchanged=98 corrected=0 nulled=0", is_bill_version set=0 changed=0 not_a_version=0, diff_baseline_id set=0 changed=0 cleared=0; change list empty (header only); validate_jurisdictions.py: OK, 16 jurisdictions, exit 0.
- **Switch (18:14:43-18:15:39, 56 s):** .venv moved to **.venv-py39**; new .venv on 3.13.13; pip pinned below 24.1; `--no-deps -r requirements-openstates.txt` exit 0; `--no-deps -e openstates-core` exit 0 (the checkout's ^3.9 range accepted 3.13); import path /opt/ddp-open-states/openstates-core/openstates/__init__.py.
- **Same checks on the new venv (18:15:50):** the nv dry run's summary lines **identical** to the baseline; the change list identical; the validator output identical (OK, 16 jurisdictions, exit 0); 0 error lines; os-text-extract and os-people present in the new venv.
- **`rollout-manifest.sh --host ec2 --ddp-sync-root /opt/ddp-sync --dry-run`: exit 0** (list valid, every list agrees with it, md5 6301f403f729b940d1e62533fe8d94f8, nothing changed).
- Rollback: `rm -rf .venv && mv .venv-py39 .venv`. **.venv-py39 is kept** until one real pass has run on the new venv; deleting it needs Ramon's go.

**Weakness to know:** nv's change list is empty (everything is already recomputed), so "the change lists are identical" is true but proves little; the summary-lines match and the import and validator checks carry the gate. Say if you want a second comparison on a state with changes.

**One local change:** I added `.venv-py39/` to the checkout's .git/info/exclude (local only, not tracked) so the kept old venv does not show as untracked in `git status` and trip the clean-checkout gates. Nothing else in the checkout changed.
