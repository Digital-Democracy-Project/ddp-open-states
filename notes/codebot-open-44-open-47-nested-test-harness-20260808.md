# OPEN-44 / OPEN-47: CodeBot's nested-repo `.codebot/test.sh` discovery gap — found, fixed, closed out for all four forks

## Context

Surfaced while submitting OPEN-42 (`openstates-scrapers` PR #23): CodeBot reported it couldn't
run that repo's test suite, and its PR body said so explicitly — a plain `pip install` of the
`openstates==6.25.3` dependency chain failed against the workspace's Python 3.14, with no
pyenv/poetry available to get to the pinned Python 3.9 the project needs.

That symptom looked at first like a missing test environment. It wasn't — `openstates-scrapers`
already had a working `.codebot/test.sh` (a Docker image pinned to `python:3.9-slim` + poetry,
built from the repo's own `Dockerfile`), merged 2026-08-01, a full week before OPEN-42 ran into
this.

## Root cause

CodeBot's workspace for `ddp-open-states` tickets is a single top-level clone with independent
sibling repos nested inside it — `openstates-scrapers/`, `openstates-core/`, `api-v3/`, `people/`
— each its own `.git` checkout, not a submodule (see `ddp-infra/PLAN-fork-management.md` for the
fork model each one follows). A ticket's real change, and the test harness for it, can live
entirely inside one of those nested repos.

The devos `test-ticket` skill's Step 0 ("prefer a project-provided test helper") only ever
checked for `.codebot/test.sh` at the *top-level* checkout root. It never found the one sitting
one directory down in `openstates-scrapers/`, so it fell through to Steps 3-4 — a generic flow
written for an npm/TypeScript monorepo, with no Python fallback — hence the improvised (and
failing) `pip install`.

## Fix: OPEN-44

`Digital-Democracy-Project/ddp-devos-package` PR #4 (branch `fix/OPEN-44`, merged): Step 0 now
also scans immediate subdirectories that are themselves git repos for their own
`.codebot/test.sh`, and prefers those over the generic fallback. Added a matching bullet to the
skill's Guardrails section.

**Operational gotcha, not yet resolved:** `~/devos` on the Mac Studio is a `setup.sh`-installed
copy of `ddp-devos-package`, not a git checkout. Merging that PR doesn't update it automatically
— it needs a manual redeploy before CodeBot actually picks up the fix.

## Follow-up: OPEN-47

Checked all four nested repos against the fix and found `people` was the only one with no
`.codebot/test.sh` of its own — `openstates-core` and `api-v3` both already had one (added
2026-08-01 and 2026-07-30 respectively, same as scrapers).

`people` is a data-only repo: no Dockerfile, no pytest suite. Its own CI
(`.github/workflows/lint-yaml.yml`) runs `os-people lint`, `os-committees lint`, and
`.github/scripts/check_duplicate_people.py`, scoped to whichever states changed. Added via
`Digital-Democracy-Project/people` PR #1 (branch `fix/OPEN-47`):

- `.codebot/Dockerfile` — Python 3.9 + poetry, scoped under `.codebot/` since this repo has no
  other Docker usage to reuse (unlike the other three, which each already had a production
  Dockerfile for a real deploy purpose).
- `.codebot/test.sh` — auto-detects which states changed on the branch (`git diff` against
  `origin/main`) and runs the same three checks CI runs, scoped to just those states. Linting
  all ~50 states on every ticket would be needlessly slow for a change that usually touches one
  or two.

**Real bug caught while building it:** the first draft of the Dockerfile mirrored
`openstates-core`'s two-step `poetry install` pattern (install deps, add source, install again to
pick up the root package). That second install failed: `Error: The current project could not be
installed: No file/folder found for package ospeople` — `people`'s `pyproject.toml` names a
package, `ospeople`, that doesn't exist as an actual directory, because this repo has nothing to
install as a package. Fixed by dropping the second install and using `--no-root`, matching what
this repo's own CI has always done. Verified end-to-end locally afterward: an explicit-state run
(`bash .codebot/test.sh smoke-test ri`) builds and lints cleanly, and a no-args run on a branch
with no `data/` changes correctly reports "nothing to lint" and exits 0.

**Side finding, already corrected locally:** the `ddp-open-states-dev` checkout's nested
`people/` clone only had `origin -> openstates/people` configured, missing the `ddp -> Digital-
Democracy-Project/people` remote its `openstates-core`/`api-v3` siblings there already have. The
production checkout's `people/` had it configured correctly the whole time — this was purely a
dev-checkout gap. Added the `ddp` remote locally to open the PR; no fork was actually missing (an
initial `mcp__github__search_repositories org:Digital-Democracy-Project people` returned zero
results and looked like proof the fork didn't exist, but GitHub's repo search excludes forks by
default unless `fork:true` is passed — a tooling false negative, not a real gap).

## Current state

All four nested repos (`openstates-scrapers`, `openstates-core`, `api-v3`, `people`) now carry
their own `.codebot/test.sh`. `test-ticket`'s Step 0 (once the devos redeploy above happens) will
find and use whichever one actually applies to a given ticket's changes, instead of guessing.

| Repo | `.codebot/test.sh` | Added |
|---|---|---|
| `openstates-scrapers` | Docker (Python 3.9 + poetry, existing `Dockerfile`) | 2026-08-01 |
| `openstates-core` | Docker Compose (Python 3.9 + poetry + Postgres, existing `Dockerfile`) | 2026-08-01 |
| `api-v3` | Docker Compose, existing `Dockerfile` | 2026-07-30 |
| `people` | Docker (Python 3.9 + poetry, new `.codebot/Dockerfile`) | 2026-08-08 (OPEN-47) |

## References

- OPEN-44: https://digitaldemocracyproject.atlassian.net/browse/OPEN-44
- OPEN-47: https://digitaldemocracyproject.atlassian.net/browse/OPEN-47
- Fix: https://github.com/Digital-Democracy-Project/ddp-devos-package/pull/4
- Follow-up: https://github.com/Digital-Democracy-Project/people/pull/1
- Symptom ticket: OPEN-42, https://github.com/Digital-Democracy-Project/openstates-scrapers/pull/23
