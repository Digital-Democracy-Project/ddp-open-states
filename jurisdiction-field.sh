#!/usr/bin/env bash
# jurisdiction-field.sh — read one field out of jurisdictions.yaml for a given jurisdiction
# (OPEN-221, PLAN-push-button-onboarding.md §4.1's "tiny read helper").
#
# This repo has no `yq` (checked before writing this — not a dependency here or anywhere else in
# the fleet's bash scripts), but PyYAML already is (requirements-openstates.txt, loaded today by
# classify_motion.py for motion_classification.yaml). So this shells out to the repo's own venv
# python for the actual parsing rather than hand-rolling a YAML reader in bash — the same
# shell-out-to-python-for-one-line-of-stdout pattern run-scrape.sh already uses for its votes-
# scraper probe (see PRIMITIVES.md's `run-scrape.sh` section, "print("votes" if ... else "")").
#
# bash 3.2.57-safe (this Mac's frozen /bin/bash — see PRIMITIVES.md's discipline checklist #8):
# no associative arrays, no $BASHPID, no process substitution relied upon.
#
# Usage (source it, call the function):
#   . ./jurisdiction-field.sh
#   timeout_s=$(jurisdiction_field fl scrape.timeout_s) || exit 1
#
# Or call it directly as a script:
#   ./jurisdiction-field.sh fl scrape.timeout_s
#   ./jurisdiction-field.sh fl waf.profile
#
# Exit codes (both as a function return and as a script exit):
#   0  — found; value printed to stdout (empty line for YAML null)
#   1  — usage error (missing args) or the python interpreter/PyYAML isn't available
#   2  — manifest file missing/unreadable, or not valid YAML
#   3  — jurisdiction code not found in the manifest
#   4  — field path not found on that jurisdiction's entry
#
# A list value prints as a comma-separated line (e.g. api_keys -> "VA_API_KEY"); a bool prints
# as the literal string "true"/"false"; other scalars print via YAML's own str().

jurisdiction_field() {  # <jurisdiction-code> <dotted.field.path> [manifest-path]
    if [ "$#" -lt 2 ]; then
        echo "usage: jurisdiction_field <code> <dotted.field.path> [manifest-path]" >&2
        return 1
    fi
    local juris="$1" field="$2"
    local script_dir manifest py

    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    manifest="${3:-${JURISDICTIONS_YAML:-$script_dir/jurisdictions.yaml}}"

    # Prefer this checkout's own dedicated venv (OS_VENV, set by activate.sh/activate-dev.sh —
    # see PRIMITIVES.md's OPEN-159 note on why inputs may fall back but outputs never do; a read
    # of a checked-in config file is an input). Fall back to plain `python3` on PATH so this
    # helper is still usable from a context that hasn't sourced activate.sh at all.
    if [ -n "${OS_VENV:-}" ] && [ -x "$OS_VENV/bin/python3" ]; then
        py="$OS_VENV/bin/python3"
    elif command -v python3 >/dev/null 2>&1; then
        py="python3"
    else
        echo "jurisdiction_field: no python3 interpreter found on PATH (need one with PyYAML)" >&2
        return 1
    fi

    "$py" - "$manifest" "$juris" "$field" <<'PYEOF'
import sys

try:
    import yaml
except ImportError:
    sys.stderr.write("jurisdiction_field: python3 has no PyYAML -- use the repo's venv (OS_VENV)\n")
    sys.exit(1)

manifest_path, juris, field = sys.argv[1], sys.argv[2], sys.argv[3]

try:
    with open(manifest_path) as f:
        data = yaml.safe_load(f)
except OSError as exc:
    sys.stderr.write(f"jurisdiction_field: cannot read {manifest_path}: {exc}\n")
    sys.exit(2)
except yaml.YAMLError as exc:
    sys.stderr.write(f"jurisdiction_field: {manifest_path} is not valid YAML: {exc}\n")
    sys.exit(2)

if not isinstance(data, dict) or juris not in data:
    sys.stderr.write(f"jurisdiction_field: no jurisdiction '{juris}' in {manifest_path}\n")
    sys.exit(3)

node = data[juris]
for part in field.split("."):
    if not isinstance(node, dict) or part not in node:
        sys.stderr.write(f"jurisdiction_field: no field '{field}' on '{juris}'\n")
        sys.exit(4)
    node = node[part]

if node is None:
    print("")
elif isinstance(node, bool):
    print("true" if node else "false")
elif isinstance(node, list):
    print(",".join(str(x) for x in node))
else:
    print(node)
PYEOF
    return $?
}

# Allow direct CLI usage (./jurisdiction-field.sh fl scrape.timeout_s) as well as sourcing.
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    jurisdiction_field "$@"
    exit $?
fi
