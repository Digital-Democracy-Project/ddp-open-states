#!/usr/bin/env bash
# test-jurisdiction-field.sh — tests for jurisdiction-field.sh (OPEN-221, PM-review round 1 fold).
#
# Round 1 flagged that this script's PR description claimed manual verification under real bash
# 3.2.57 but had no automated test file backing that claim -- everything else in this PR (the
# validator) got 26 pytest cases, this got none. This is that coverage: sourced-function usage,
# direct-CLI usage, every documented exit code, every scalar output shape (string/bool/list/null),
# and the round-1-fold block-path rejection.
#
#     bash test-jurisdiction-field.sh

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PASS=0
FAIL=0

check() {
    local desc="$1" expected="$2" actual="$3"
    if [ "$expected" = "$actual" ]; then
        PASS=$((PASS + 1)); echo "  ok   $desc"
    else
        FAIL=$((FAIL + 1)); echo "  FAIL $desc"
        echo "         expected: [$expected]"
        echo "         actual  : [$actual]"
    fi
}

FIXTURE=$(mktemp /tmp/jurisdiction-field-test.XXXXXX.yaml)
cat > "$FIXTURE" <<'YAML'
fl:
  name: Florida
  status: live
  scrape:
    timeout_s: 57600
    allow_duplicates: true
    session_arg: null
  api_keys: ["ONE_KEY", "TWO_KEY"]
YAML
trap 'rm -f "$FIXTURE"' EXIT

# -- sourced-function usage --
. "$SCRIPT_DIR/jurisdiction-field.sh"

out=$(jurisdiction_field fl scrape.timeout_s "$FIXTURE"); rc=$?
check "sourced: leaf int value"       "57600" "$out"
check "sourced: leaf int value: exit" "0"     "$rc"

out=$(jurisdiction_field fl scrape.allow_duplicates "$FIXTURE")
check "sourced: bool true prints 'true'" "true" "$out"

out=$(jurisdiction_field fl scrape.session_arg "$FIXTURE")
check "sourced: YAML null prints empty string" "" "$out"

out=$(jurisdiction_field fl api_keys "$FIXTURE")
check "sourced: list prints comma-separated" "ONE_KEY,TWO_KEY" "$out"

jurisdiction_field zz scrape.timeout_s "$FIXTURE" >/dev/null 2>&1
check "sourced: unknown jurisdiction: exit 3" "3" "$?"

jurisdiction_field fl scrape.nonexistent "$FIXTURE" >/dev/null 2>&1
check "sourced: unknown field: exit 4" "4" "$?"

jurisdiction_field fl >/dev/null 2>&1
check "sourced: usage error (too few args): exit 1" "1" "$?"

# PM-review round 1 fold: a block path must be rejected, not printed as a Python repr.
jurisdiction_field fl scrape "$FIXTURE" >/dev/null 2>&1
check "sourced: block path rejected: exit 4" "4" "$?"
err=$(jurisdiction_field fl scrape "$FIXTURE" 2>&1 >/dev/null)
check "sourced: block path error mentions 'block'" "1" "$(echo "$err" | grep -c "block")"

# -- direct CLI usage --
out=$("$SCRIPT_DIR/jurisdiction-field.sh" fl scrape.timeout_s "$FIXTURE")
check "CLI: leaf int value" "57600" "$out"

"$SCRIPT_DIR/jurisdiction-field.sh" fl scrape.timeout_s "$FIXTURE" >/dev/null 2>&1
check "CLI: exit 0 on success" "0" "$?"

"$SCRIPT_DIR/jurisdiction-field.sh" fl scrape.timeout_s "/nonexistent/manifest.yaml" >/dev/null 2>&1
check "CLI: missing manifest: exit 2" "2" "$?"

echo
if [ "$FAIL" -eq 0 ]; then
    echo "ALL PASS ($PASS assertions)"
    exit 0
fi
echo "$FAIL FAILED, $PASS passed"
exit 1
