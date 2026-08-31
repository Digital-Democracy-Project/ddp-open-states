#!/usr/bin/env python3
"""
validate_jurisdictions.py — schema validator for jurisdictions.yaml (OPEN-221).

PLAN-push-button-onboarding.md §4.1 ("Manifest v0"): a new tracked file, jurisdictions.yaml,
plus a checked-in validator. This is that validator. It knows nothing about scraping or
archiving -- it only checks the manifest's own shape: required fields present, enum values valid,
types correct. It does not read from or write to the database, the scrapers, or any live service.

Usage:
    python3 validate_jurisdictions.py                       # validates ./jurisdictions.yaml
    python3 validate_jurisdictions.py path/to/other.yaml     # validates a specific file

Exit code 0 and "OK: N jurisdiction(s) valid" on success. Exit code 1 and one line per problem
found on failure -- every problem is reported in one pass, not just the first (a PR review is
cheaper against a full list than a fix-rerun-fix loop).

Deliberately does NOT validate `quality.walk_direction` -- PLAN-push-button-onboarding.md's
2026-08-07 update marks that field obsolete (superseded by OPEN-34's content-based version-stage
classifier) and says not to build it. If it shows up in a manifest entry anyway, that's flagged
as an unknown field (see UNKNOWN field handling below) rather than silently accepted.
"""

import sys

try:
    import yaml
except ImportError:  # pragma: no cover - exercised only in a broken environment
    sys.stderr.write(
        "validate_jurisdictions.py requires PyYAML (already a project dependency -- see "
        "requirements-openstates.txt). Run this with the repo's own venv python, e.g.\n"
        "    .venv/bin/python3 validate_jurisdictions.py\n"
    )
    sys.exit(2)


class _DuplicateKeyCheckingLoader(yaml.SafeLoader):
    """PM-review round 1 fold: PyYAML's default SafeLoader silently accepts duplicate mapping
    keys (last value wins) -- a real gap for a file meant to be this fleet's authoritative
    per-jurisdiction source of truth, where a duplicated jurisdiction code or a duplicated nested
    field (e.g. two `timeout_s:` lines under one state) would otherwise silently drop a reviewed
    value with no error at all. Overrides construct_mapping to raise instead."""

    def construct_mapping(self, node, deep=False):
        mapping = set()
        for key_node, _value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in mapping:
                raise yaml.constructor.ConstructorError(
                    None, None, f"found duplicate key {key!r}", key_node.start_mark
                )
            mapping.add(key)
        return super().construct_mapping(node, deep=deep)


DEFAULT_MANIFEST_PATH = "jurisdictions.yaml"

STATUS_VALUES = {"probing", "scraping", "validating", "archived", "live", "paused"}
TIER_VALUES = {"primary", "secondary"}
WAF_PROFILE_VALUES = {"none", "cookie_provider", "custom"}

# top-level required fields, each with an expected Python type
TOP_LEVEL_FIELDS = {
    "name": str,
    "status": str,
    "tier": str,
    "scrape": dict,
    "archive": dict,
    "waf": dict,
    "quality": dict,
    "api_keys": list,
    "onboarding": dict,
}

SCRAPE_FIELDS = {
    "allow_duplicates": bool,
    "timeout_s": int,
    "session_arg": (str, type(None)),
    "votes_scraper": bool,
    "start_filter": bool,
}

ARCHIVE_FIELDS = {
    "enabled": bool,
    "timeout_s": int,
}

WAF_FIELDS = {
    "profile": str,
}

QUALITY_FIELDS = {
    "diff_cleaner": str,
}

ONBOARDING_FIELDS = {
    "epic": (str, type(None)),
    "evidence": (str, type(None)),
}


def _type_name(expected):
    if isinstance(expected, tuple):
        return " or ".join(t.__name__ for t in expected)
    return expected.__name__


def _check_type(value, expected, path, errors):
    """Type-check `value` against `expected` (a type or tuple of types), bool-vs-int-safe.

    Python's bool is a subclass of int, so a naive isinstance(x, int) check would silently
    accept True/False wherever an int is expected (e.g. timeout_s: true) -- guard against that
    explicitly rather than trusting isinstance alone.
    """
    if expected is int and isinstance(value, bool):
        errors.append(f"{path}: expected int, got bool ({value!r})")
        return False
    if not isinstance(value, expected):
        errors.append(f"{path}: expected {_type_name(expected)}, got {type(value).__name__} ({value!r})")
        return False
    return True


def _check_block(node, fields, path, errors):
    """Check one nested dict (`scrape`, `archive`, etc.) against its required-field map."""
    if not isinstance(node, dict):
        errors.append(f"{path}: expected a mapping, got {type(node).__name__}")
        return
    for field, expected in fields.items():
        if field not in node:
            errors.append(f"{path}.{field}: missing required field")
            continue
        _check_type(node[field], expected, f"{path}.{field}", errors)
    for field in node:
        if field not in fields:
            errors.append(f"{path}.{field}: unknown field (not in the §4.1 schema)")


def validate(data):
    """Validate a parsed jurisdictions.yaml document. Returns a list of error strings (empty = valid)."""
    errors = []

    if data is None:
        return ["manifest is empty"]
    if not isinstance(data, dict):
        return [f"manifest root must be a mapping of jurisdiction code -> entry, got {type(data).__name__}"]
    if not data:
        return ["manifest has no jurisdiction entries"]

    for code, entry in data.items():
        if not isinstance(code, str) or not code:
            errors.append(f"jurisdiction key {code!r}: keys must be non-empty strings")
            continue
        if not code.islower() or not code.replace("_", "").isalpha():
            errors.append(
                f"{code}: jurisdiction key should be lowercase letters, optionally "
                f"underscore-separated (e.g. 'fl', 'us'), not {code!r}"
            )

        if not isinstance(entry, dict):
            errors.append(f"{code}: entry must be a mapping, got {type(entry).__name__}")
            continue

        for field, expected in TOP_LEVEL_FIELDS.items():
            if field not in entry:
                errors.append(f"{code}.{field}: missing required field")
                continue
            _check_type(entry[field], expected, f"{code}.{field}", errors)

        for field in entry:
            if field not in TOP_LEVEL_FIELDS:
                errors.append(f"{code}.{field}: unknown field (not in the §4.1 schema)")

        if isinstance(entry.get("status"), str) and entry["status"] not in STATUS_VALUES:
            errors.append(
                f"{code}.status: {entry['status']!r} is not one of {sorted(STATUS_VALUES)}"
            )
        if isinstance(entry.get("tier"), str) and entry["tier"] not in TIER_VALUES:
            errors.append(f"{code}.tier: {entry['tier']!r} is not one of {sorted(TIER_VALUES)}")

        if isinstance(entry.get("scrape"), dict):
            _check_block(entry["scrape"], SCRAPE_FIELDS, f"{code}.scrape", errors)
            timeout = entry["scrape"].get("timeout_s")
            if isinstance(timeout, int) and not isinstance(timeout, bool) and timeout <= 0:
                errors.append(f"{code}.scrape.timeout_s: must be positive, got {timeout}")

        if isinstance(entry.get("archive"), dict):
            _check_block(entry["archive"], ARCHIVE_FIELDS, f"{code}.archive", errors)
            timeout = entry["archive"].get("timeout_s")
            if isinstance(timeout, int) and not isinstance(timeout, bool) and timeout <= 0:
                errors.append(f"{code}.archive.timeout_s: must be positive, got {timeout}")

        if isinstance(entry.get("waf"), dict):
            _check_block(entry["waf"], WAF_FIELDS, f"{code}.waf", errors)
            profile = entry["waf"].get("profile")
            if isinstance(profile, str) and profile not in WAF_PROFILE_VALUES:
                errors.append(f"{code}.waf.profile: {profile!r} is not one of {sorted(WAF_PROFILE_VALUES)}")

        if isinstance(entry.get("quality"), dict):
            _check_block(entry["quality"], QUALITY_FIELDS, f"{code}.quality", errors)

        if isinstance(entry.get("onboarding"), dict):
            _check_block(entry["onboarding"], ONBOARDING_FIELDS, f"{code}.onboarding", errors)

        api_keys = entry.get("api_keys")
        if isinstance(api_keys, list):
            for i, key in enumerate(api_keys):
                if not isinstance(key, str) or not key:
                    errors.append(f"{code}.api_keys[{i}]: must be a non-empty string, got {key!r}")

    return errors


def load_and_validate(path):
    """Read and validate a manifest file. Returns (data, errors); data is None if unreadable/unparsable."""
    try:
        with open(path, "r") as f:
            raw = f.read()
    except OSError as exc:
        return None, [f"cannot read {path}: {exc}"]

    try:
        data = yaml.load(raw, Loader=_DuplicateKeyCheckingLoader)
    except yaml.YAMLError as exc:
        return None, [f"{path} is not valid YAML: {exc}"]

    return data, validate(data)


def main(argv):
    path = argv[1] if len(argv) > 1 else DEFAULT_MANIFEST_PATH
    data, errors = load_and_validate(path)

    if errors:
        sys.stderr.write(f"validate_jurisdictions.py: {len(errors)} problem(s) in {path}:\n")
        for e in errors:
            sys.stderr.write(f"  - {e}\n")
        return 1

    count = len(data) if isinstance(data, dict) else 0
    print(f"OK: {count} jurisdiction(s) valid in {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
