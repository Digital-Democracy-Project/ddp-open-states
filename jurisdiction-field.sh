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
# OPEN-327: the same file answers "which jurisdictions are on this list?" so a script can derive
# a comma list from the manifest instead of hard-coding one:
#   . ./jurisdiction-field.sh
#   states=$(jurisdiction_codes archive.enabled) || exit 1      # e.g. "fl,ut,az,wa,..."
# Or directly:  ./jurisdiction-field.sh --codes enrollment.people_refresh
# The field must be a boolean on every jurisdiction; the codes where it is true print in manifest
# order, comma-joined (an empty line when none is true). Same exit codes as below.
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

_jf_manifest_path() {  # print the manifest path: $JURISDICTIONS_YAML, else next to this file
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    echo "${JURISDICTIONS_YAML:-$script_dir/jurisdictions.yaml}"
}

_jf_python() {  # <caller-name>: print the python3 to use; return 1 (with a message) when there is none
    # Prefer this checkout's own dedicated venv (OS_VENV, set by activate.sh/activate-dev.sh —
    # see PRIMITIVES.md's OPEN-159 note on why inputs may fall back but outputs never do; a read
    # of a checked-in config file is an input). Fall back to plain `python3` on PATH so this
    # helper is still usable from a context that hasn't sourced activate.sh at all.
    if [ -n "${OS_VENV:-}" ] && [ -x "$OS_VENV/bin/python3" ]; then
        echo "$OS_VENV/bin/python3"
    elif command -v python3 >/dev/null 2>&1; then
        echo "python3"
    else
        echo "$1: no python3 interpreter found on PATH (need one with PyYAML)" >&2
        return 1
    fi
}

jurisdiction_field() {  # <jurisdiction-code> <dotted.field.path> [manifest-path]
    if [ "$#" -lt 2 ]; then
        echo "usage: jurisdiction_field <code> <dotted.field.path> [manifest-path]" >&2
        return 1
    fi
    local juris="$1" field="$2"
    local manifest py

    manifest="${3:-$(_jf_manifest_path)}"
    py="$(_jf_python jurisdiction_field)" || return 1

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

if isinstance(node, dict):
    # PM-review round 1 fold: a block path (e.g. "scrape" instead of "scrape.timeout_s") has
    # no stable shell serialization -- printing Python's dict repr would be a silently-wrong,
    # unparseable string handed to whatever bash expected a scalar. Every documented usage
    # example asks for a leaf value; enforce that rather than let this slide through.
    sys.stderr.write(f"jurisdiction_field: '{field}' on '{juris}' is a block, not a leaf value "
                      f"-- request a specific field inside it instead\n")
    sys.exit(4)
elif node is None:
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


jurisdiction_codes() {  # <dotted.bool.field> [manifest-path]  -> comma list of codes where it is true
    if [ "$#" -lt 1 ]; then
        echo "usage: jurisdiction_codes <dotted.bool.field> [manifest-path]" >&2
        return 1
    fi
    local field="$1" manifest py
    manifest="${2:-$(_jf_manifest_path)}"
    py="$(_jf_python jurisdiction_codes)" || return 1

    "$py" - "$manifest" "$field" <<'PYEOF'
import sys

try:
    import yaml
except ImportError:
    sys.stderr.write("jurisdiction_codes: python3 has no PyYAML -- use the repo's venv (OS_VENV)\n")
    sys.exit(1)

manifest_path, field = sys.argv[1], sys.argv[2]

try:
    with open(manifest_path) as f:
        data = yaml.safe_load(f)
except OSError as exc:
    sys.stderr.write(f"jurisdiction_codes: cannot read {manifest_path}: {exc}\n")
    sys.exit(2)
except yaml.YAMLError as exc:
    sys.stderr.write(f"jurisdiction_codes: {manifest_path} is not valid YAML: {exc}\n")
    sys.exit(2)

if not isinstance(data, dict) or not data:
    sys.stderr.write(f"jurisdiction_codes: {manifest_path} has no jurisdictions\n")
    sys.exit(2)

codes = []
for code, entry in data.items():
    node = entry
    for part in field.split("."):
        if not isinstance(node, dict) or part not in node:
            sys.stderr.write(f"jurisdiction_codes: no field '{field}' on '{code}'\n")
            sys.exit(4)
        node = node[part]
    # A list that silently skipped a jurisdiction is the failure this exists to prevent, so a
    # non-boolean leaf is an error, not a "false".
    if not isinstance(node, bool):
        sys.stderr.write(f"jurisdiction_codes: '{field}' on '{code}' is not true/false\n")
        sys.exit(4)
    if node:
        codes.append(str(code))

print(",".join(codes))
PYEOF
    return $?
}

# Allow direct CLI usage (./jurisdiction-field.sh fl scrape.timeout_s, or
# ./jurisdiction-field.sh --codes archive.enabled) as well as sourcing.
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    if [ "${1:-}" = "--codes" ]; then
        shift
        jurisdiction_codes "$@"
    else
        jurisdiction_field "$@"
    fi
    exit $?
fi
