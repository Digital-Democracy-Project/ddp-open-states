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

# -- OPEN-327: jurisdiction_codes (which jurisdictions have a boolean field set to true) --
CODES_FIXTURE=$(mktemp /tmp/jurisdiction-codes-test.XXXXXX.yaml)
cat > "$CODES_FIXTURE" <<'YAML'
us:
  archive: {enabled: true}
  scrape: {allow_duplicates: false}
fl:
  archive: {enabled: true}
  scrape: {allow_duplicates: true}
nc:
  archive: {enabled: false}
  scrape: {allow_duplicates: false}
YAML
trap 'rm -f "$FIXTURE" "$CODES_FIXTURE"' EXIT

out=$(jurisdiction_codes archive.enabled "$CODES_FIXTURE"); rc=$?
check "codes: true on some, manifest order"   "us,fl" "$out"
check "codes: exit 0"                          "0"     "$rc"

out=$(jurisdiction_codes scrape.allow_duplicates "$CODES_FIXTURE")
check "codes: a single match"                  "fl"    "$out"

printf 'us:\n  archive: {enabled: false}\n' > "$CODES_FIXTURE"
out=$(jurisdiction_codes archive.enabled "$CODES_FIXTURE"); rc=$?
check "codes: none true prints an empty line"  ""      "$out"
check "codes: none true is still exit 0"       "0"     "$rc"

printf 'us:\n  archive: {enabled: true}\nfl:\n  archive: {}\n' > "$CODES_FIXTURE"
jurisdiction_codes archive.enabled "$CODES_FIXTURE" >/dev/null 2>&1
check "codes: field missing on one jurisdiction: exit 4 (never a silent skip)" "4" "$?"

printf 'us:\n  archive: {enabled: "yes"}\n' > "$CODES_FIXTURE"
jurisdiction_codes archive.enabled "$CODES_FIXTURE" >/dev/null 2>&1
check "codes: non-boolean leaf: exit 4"        "4"     "$?"

jurisdiction_codes archive.enabled "/nonexistent/manifest.yaml" >/dev/null 2>&1
check "codes: missing manifest: exit 2"        "2"     "$?"

printf 'not: [valid' > "$CODES_FIXTURE"
jurisdiction_codes archive.enabled "$CODES_FIXTURE" >/dev/null 2>&1
check "codes: invalid YAML: exit 2"            "2"     "$?"

jurisdiction_codes >/dev/null 2>&1
check "codes: usage error: exit 1"             "1"     "$?"

printf 'us:\n  archive: {enabled: true}\n' > "$CODES_FIXTURE"
out=$("$SCRIPT_DIR/jurisdiction-field.sh" --codes archive.enabled "$CODES_FIXTURE")
check "CLI: --codes"                           "us"    "$out"

# the real manifest: every list the shell scripts now derive must be readable from it
for f in archive.enabled enrollment.people_refresh enrollment.api_smoke_test enrollment.qa_sweep scrape.allow_duplicates; do
    "$SCRIPT_DIR/jurisdiction-field.sh" --codes "$f" >/dev/null 2>&1
    check "real manifest: --codes $f"          "0"     "$?"
done

echo
if [ "$FAIL" -eq 0 ]; then
    echo "ALL PASS ($PASS assertions)"
    exit 0
fi
echo "$FAIL FAILED, $PASS passed"
exit 1
