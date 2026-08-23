#!/usr/bin/env bash
# OPEN-125: can every scraper module actually be imported? Walks every
# openstates-scrapers/scrapers/<abbr>/ package, calls openstates' own
# get_jurisdiction("scrapers.<abbr>") on it, and reports which ones fail and why.
#
# Why this exists: the venv is built `pip install --no-deps -r requirements-openstates.txt`
# (activate.sh) — a hand-maintained pin list — while the scrapers declare their real
# dependencies in openstates-scrapers/pyproject.toml. Nothing reconciles the two, so a
# scraper whose dependency was never hand-added to the pin list just raises
# ModuleNotFoundError on import, silently, until someone tries that state. That is how
# ga/gu/mp/nh/oh were found broken (OPEN-125) — by importing all 50+, not by grepping.
# Adding the missing pins fixes those five; only a check stops the sixth. Same shape as
# the openstates-core "silently running the pinned PyPI release, not the local checkout"
# gap: a pinned install diverging from the real source with nothing looking.
#
# Read-only and safe to run against the production venv during a live scrape — it imports
# modules and instantiates the State subclass, it does not touch the DB, the cache, the
# data dir, or the network. It does NOT install anything: if it reports a missing module,
# the fix is a pin in requirements-openstates.txt plus a venv rebuild, not a pip install
# into the live venv.
#
# Deliberately NOT wired to cron, CI or alerting — same call as check-fork-drift.sh
# (PLAN-fork-management.md §5.F): not worth it at DDP's current scale. Run it manually
# before onboarding a new state, and after any requirements-openstates.txt change.
#
# Exit status is the "hard failure or warning?" decision (OPEN-125 item 3):
#   MISSING MODULE / other import error -> hard failure, exit 1. A pin is missing, or the
#       scraper is genuinely broken. Nobody can run that state.
#   MISSING CREDENTIAL (e.g. dc's KeyError: 'DC_API_KEY') -> reported, but exit 0. That is
#       a signup/ops step, not a dependency bug (OPEN-126), and it is expected today.
# So a clean tree exits 0 with dc listed as credential-gated, and a newly-diverged pin list
# exits 1.
#
# Env seams (for testing a candidate venv without touching the live one — the production
# venv must never be rebuilt or installed into while scrapes are in flight):
#   IMPORT_CHECK_VENV          default $SCRIPT_DIR/.venv
#   IMPORT_CHECK_SCRAPERS_DIR  default $SCRIPT_DIR/openstates-scrapers
# Both need overriding when running from a git worktree: openstates-scrapers is gitignored
# and is its own repo, so it does not exist inside a worktree of this one.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${IMPORT_CHECK_VENV:-$SCRIPT_DIR/.venv}"
SCRAPERS_DIR="${IMPORT_CHECK_SCRAPERS_DIR:-$SCRIPT_DIR/openstates-scrapers}"

[ -x "$VENV/bin/python" ] || { echo "no python at $VENV/bin/python" >&2; exit 2; }
[ -d "$SCRAPERS_DIR/scrapers" ] || { echo "no scrapers/ under $SCRAPERS_DIR" >&2; exit 2; }

# Matches activate.sh's PYTHONPATH (scrapers/ itself, for the sibling-module imports
# scrapers do — e.g. fl/bills.py's `from classify_motion import classify_motion`), plus
# $SCRAPERS_DIR so the `scrapers` package itself resolves.
export PYTHONPATH="$SCRAPERS_DIR/scrapers:$SCRAPERS_DIR${PYTHONPATH:+:$PYTHONPATH}"

cd "$SCRAPERS_DIR"
exec "$VENV/bin/python" - <<'PY'
import logging
import os
import pathlib
import re
import warnings

warnings.filterwarnings("ignore")
# openstates configures logging on import; silence it so the report is the only output.
logging.disable(logging.CRITICAL)

from openstates.cli.update import get_jurisdiction  # noqa: E402

# scrapers/utils/ is the shared helper package, not a jurisdiction. It fails the probe with
# `CommandError: Unable to import State subclass from utils` — correct behaviour, not a bug
# (explicitly called out in OPEN-125 so nobody re-files it). Kept as an explicit list rather
# than a name heuristic: if upstream adds another helper package this check fails loudly and
# someone adds it here, instead of a clever rule silently skipping a real state.
NON_JURISDICTIONS = {"utils"}

scrapers = pathlib.Path("scrapers")
abbrs = sorted(
    p.name
    for p in scrapers.iterdir()
    if p.is_dir() and (p / "__init__.py").is_file() and p.name not in NON_JURISDICTIONS
)

ok, missing_module, missing_credential, other = [], [], [], []

for abbr in abbrs:
    try:
        get_jurisdiction(f"scrapers.{abbr}")
    except ModuleNotFoundError as e:
        missing_module.append((abbr, f"no module named {e.name!r}"))
    except KeyError as e:
        # A scraper reading os.environ[...] at import time — a credential, not a package.
        # Narrowly matched on purpose: an ENV_VAR-shaped name that really is absent from the
        # environment. A plain dict lookup that happens to raise KeyError is a genuine scraper
        # bug and must stay a hard failure, not get downgraded to an exit-0 warning.
        key = e.args[0] if e.args else None
        if isinstance(key, str) and re.fullmatch(r"[A-Z][A-Z0-9_]*", key) and key not in os.environ:
            missing_credential.append((abbr, f"KeyError: {key!r} (env var not set)"))
        else:
            other.append((abbr, f"KeyError: {key!r}"))
    except Exception as e:
        other.append((abbr, f"{type(e).__name__}: {e}"))
    else:
        ok.append(abbr)

for label, rows in (
    ("MISSING MODULE", missing_module),
    ("MISSING CREDENTIAL", missing_credential),
    ("OTHER FAILURE", other),
):
    for abbr, why in rows:
        print(f"{abbr:<5} {label:<19} {why}")

print(
    f"{len(abbrs)} jurisdiction(s) checked: {len(ok)} import OK, "
    f"{len(missing_module)} missing a module, "
    f"{len(missing_credential)} missing a credential, "
    f"{len(other)} other failure(s). "
    f"Skipped non-jurisdiction dir(s): {', '.join(sorted(NON_JURISDICTIONS))}."
)

# Missing credentials are a known ops step, not a broken pin list — see header.
raise SystemExit(1 if (missing_module or other) else 0)
PY
