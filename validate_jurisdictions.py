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

import datetime
import re
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
WAF_PROFILE_VALUES = {"none", "cookie_provider", "custom"}

# top-level required fields, each with an expected Python type
TOP_LEVEL_FIELDS = {
    "name": str,
    "status": str,
    "scrape": dict,
    "archive": dict,
    "enrollment": dict,
    "waf": dict,
    "quality": dict,
    "chambers": dict,
    "votes": dict,
    "api_keys": list,
    # OPEN-555 (PLAN-state-specific-handling Phase 4): the openstates-scrapers module (US Congress is "usa", every
    # state its own code) and the OpenStates jurisdiction id stored in the database.
    "scraper_module": str,
    "ocd_id": str,
    "onboarding": dict,
}

SCRAPE_FIELDS = {
    "allow_duplicates": bool,
    "timeout_s": int,
    "session_arg": (str, type(None)),
    "votes_scraper": bool,
    "start_filter": bool,
    # SYNC-157: ddp-sync's per-state scrape behaviour, read from here (its sync_schedule.yaml keeps only the global
    # switches and numbers, and refuses a per-state list at load).
    "sweep_import": bool,                      # import-as-you-go sweep (OPEN-86)
    "full_walk": bool,                         # periodic forced full walk (OPEN-162)
    "retry": bool,                             # bounded whole-run retry (OPEN-87); refused with a WAF below (OPEN-53)
    "cadence_escalation": bool,                # dynamic cadence may raise the state to nightly (OPEN-140)
    "fargate_max_wait_s": (int, type(None)),   # this state's own Fargate ceiling; null = the shared one (OPEN-476)
    "load_on_fargate": bool,                   # OPEN-633: the load runs as a Fargate task of the scrapers image, not in ddp-sync
    # OPEN-555: Utah's session-list retry (scrapers/ut/__init__.py, OPEN-106); null for every other state.
    "session_list_attempts": (int, type(None)),
    "session_list_backoff_s": (int, type(None)),
}

ARCHIVE_FIELDS = {
    "enabled": bool,    # the state's scrape is followed by its archive (ddp-sync's one pipeline per state, SYNC-152/153)
    "timeout_s": int,
}

# OPEN-521 (plan "One pipeline per state", 2026-11-10): two fields that no longer exist. Who is scraped is the
# status rule (not probing or paused), the archive follows each scrape when archive.enabled, and WHEN a state is
# scraped is ddp-sync's openstates_scrape.timing (OPEN-124: timing belongs to the scheduler). They stay rejected
# like any unknown field; this only says why, so nobody adds them back.
REMOVED_FIELDS = {
    "tier": "removed by OPEN-521: when a state is scraped is ddp-sync's openstates_scrape.timing; who is its status",
    "archive.scheduled": "removed by OPEN-521: the archive follows every scrape of a state with archive.enabled",
    "voatz": "removed by BROKER-494: this file is OpenStates data; a state's Voatz test precinct and its private poll "
             "creator id (BROKER-482) live in its Voatz entry in AWS Secrets Manager, read by the broker; never add a "
             "voatz block back",
    "actions": "removed by OPEN-544: every state's bill actions are stored oldest first (fixed in the scrapers: LA, NE, "
               "NC, US), so actions.newest_first was false everywhere and nothing reads it; a state found storing them "
               "newest first is fixed in its scraper, not labelled here",
}

# 2026-11-03 (pilot #2): a state that has left `probing` must already carry the flags its stage needs, so nobody
# has to remember to flip them. Pilot #2's first scrapes loaded with 0 legislators because people_refresh was
# still false when the state went to `scraping`. `paused` is left out on purpose (a paused state keeps whatever
# it had), and LegBot (enrollment.legbot_replica), embedding and routing stay human decisions: they are not here.
STATUSES_THAT_NEED_PEOPLE_AND_ARCHIVE = {"scraping", "validating", "archived", "live"}

# OPEN-318: which per-feature jurisdiction lists this jurisdiction belongs to. Each is the manifest's
# statement of a list that is otherwise hard-coded somewhere (see check-jurisdiction-drift.py for where),
# so adding a state means editing the manifest and then bringing every list it names into agreement.
ENROLLMENT_FIELDS = {
    "people_refresh": bool,   # run-people-refresh.sh
    "search_refresh": bool,   # ddp-sync openstates_archive.bill_search_refresh
    "embedding": bool,        # ddp-sync openstates_archive.knowledge_base_embedding
    "cloud_path": bool,       # ddp-sync openstates_scrape.cloud_path (+ memory_backend)
    "api_smoke_test": bool,   # start-os-api.sh's boot smoke test
    "qa_sweep": bool,         # quality_check.py JURISDICTIONS
    # OPEN-330: the two lists that live in an env var on each host, not in git. Compared with the live values
    # by `check-jurisdiction-drift.py --live NAME=VALUE` (and by ddp-sync's daily check for its own env).
    "replica_routing": bool,  # DDP_OPENSTATES_JURISDICTIONS (ddp-broker-py and ddp-sync): reads from the replica
    "legbot_replica": bool,   # LegBot reads text from the replica (ddp-sync reads it here; its env list is deleted, SYNC-157)
    "broker_bill_event_signal": bool,  # SYNC-157: ddp-sync asks the broker to check bill events after a scrape (SYNC-128)
}

WAF_FIELDS = {
    "profile": str,
    # OPEN-464: a separate question from profile -- whether this jurisdiction's WAF cookie can be
    # produced from an arbitrary cloud IP (Fargate), not which WAF implementation it uses. mi and
    # fl both have profile: cookie_provider but answer this differently (see jurisdictions.yaml's
    # own header comment). Read by verify-jurisdiction's fargate_refusal() and probe-on-fargate
    # instead of either one keeping its own hard-coded refused-states set.
    "fargate_safe": bool,
    # SYNC-157: ddp-sync mints WAF cookies with ScrapeBot before this state's scrape and archive (PLAN-scrapebot.md 3.7).
    "scrapebot_fallback": bool,
    # OPEN-555: fetch limits, read by openstates-core's RESILIENCE_PROFILES (requests_per_minute,
    # max_consecutive_blocks) and the FL/MI scrapers (the rest), each falling back to its old constant. Null for a
    # state with no WAF profile; a state with one needs the first two (its profile reads them).
    "requests_per_minute": (int, type(None)),
    "max_consecutive_blocks": (int, type(None)),
    "max_attempts": (int, type(None)),
    "cooldown_after_failures": (int, type(None)),
    "cooldown_s": (int, type(None)),
}

WAF_LIMIT_FIELDS = ("requests_per_minute", "max_consecutive_blocks", "max_attempts", "cooldown_after_failures",
                    "cooldown_s")
WAF_PROFILE_NEEDS = ("requests_per_minute", "max_consecutive_blocks")

QUALITY_FIELDS = {
    "diff_cleaner": str,
}

# OPEN-556 (PLAN-state-specific-handling C7): the legislature's own chamber names, for display, instead of "House" and
# "Senate" everywhere (wrong for an Assembly, Virginia's House of Delegates and Nebraska). `upper` and `lower` are
# OpenStates' chamber classifications. A one-house legislature (`unicameral: true`, Nebraska) has its one name in
# `upper`, because OpenStates' `legislature` chamber is read as the upper chamber (BROKER-456), and `lower: null`.
# Display only: no stored data uses these. api-v3 serves them at GET /ddp/enrollment.
CHAMBERS_FIELDS = {
    "unicameral": bool,
    "upper": str,
    "lower": (str, type(None)),
}

# OPEN-555: per-state values a scraper uses to read votes, each falling back to its old constant in the scraper.
VOTES_FIELDS = {
    "house_speaker_by_session": (dict, type(None)),  # ma: who "Mr. Speaker" is, per session (OPEN-474)
    "senate_president_by_session": (dict, type(None)),  # la: who "Mr. President" is, per session (OPEN-764)
    "bare_key_session": (str, type(None)),           # nc: the session whose votes keep a bare roll-call key (OPEN-397)
}

SCRAPER_MODULE_RE = re.compile(r"^[a-z]+(_[a-z]+)*$")
# OPEN-785: the scrapers that read the presiding officers through openstates-scrapers' utils/presiding_officers.py,
# the only reader that understands a dated session (id, ms, mo and ma take a plain name)
DATED_OFFICER_STATES = {"la", "ri"}


def _is_day(value):
    """A quoted 'YYYY-MM-DD' that is a real date."""
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        return False
    return True
OCD_ID_RE = re.compile(r"^ocd-jurisdiction/country:us(/(state|district|territory):[a-z]{2})?/government$")

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


def _check_positive_or_null(node, field, path, errors):
    """OPEN-555: a count or a number of seconds, when set, is a whole number above zero (the type is checked apart)."""
    value = node.get(field)
    if isinstance(value, bool) or (isinstance(value, int) and value <= 0):  # bool is an int subclass
        errors.append(f"{path}.{field}: must be null or a positive whole number, got {value!r}")


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
            errors.append(_unknown(f"{path}.{field}"))


def _unknown(path):
    """`code.field` or `code.block.field` -> the unknown-field error, saying why when the field was removed."""
    why = REMOVED_FIELDS.get(path.split(".", 1)[1])
    return f"{path}: unknown field (not in the §4.1 schema)" + (f"; {why}" if why else "")


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
                errors.append(_unknown(f"{code}.{field}"))

        if isinstance(entry.get("status"), str) and entry["status"] not in STATUS_VALUES:
            errors.append(
                f"{code}.status: {entry['status']!r} is not one of {sorted(STATUS_VALUES)}"
            )
        if isinstance(entry.get("scrape"), dict):
            _check_block(entry["scrape"], SCRAPE_FIELDS, f"{code}.scrape", errors)
            timeout = entry["scrape"].get("timeout_s")
            if isinstance(timeout, int) and not isinstance(timeout, bool) and timeout <= 0:
                errors.append(f"{code}.scrape.timeout_s: must be positive, got {timeout}")
            wait = entry["scrape"].get("fargate_max_wait_s")
            if isinstance(wait, bool) or (isinstance(wait, int) and wait <= 0):  # bool is an int subclass
                errors.append(f"{code}.scrape.fargate_max_wait_s: must be null or a positive whole number of seconds, got {wait!r}")
            # SYNC-157 (was ddp-sync's scrape_retry.jurisdictions_excluded: ["mi"]): a blind retry against a WAF worsens a
            # block instead of recovering from it (OPEN-53), so a state with a WAF profile can never be enrolled in retry.
            waf = entry.get("waf")
            if entry["scrape"].get("retry") is True and isinstance(waf, dict) and waf.get("profile") not in (None, "none"):
                errors.append(f"{code}.scrape.retry: must be false for a state with a WAF profile ({waf.get('profile')!r}): "
                              f"retrying against a WAF worsens a block (OPEN-53)")

        if isinstance(entry.get("scrape"), dict):
            for field in ("session_list_attempts", "session_list_backoff_s"):
                _check_positive_or_null(entry["scrape"], field, f"{code}.scrape", errors)

        if isinstance(entry.get("scraper_module"), str) and not SCRAPER_MODULE_RE.match(entry["scraper_module"]):
            errors.append(f"{code}.scraper_module: must be an openstates-scrapers module name (lowercase letters), "
                          f"got {entry['scraper_module']!r}")
        if isinstance(entry.get("ocd_id"), str) and not OCD_ID_RE.match(entry["ocd_id"]):
            errors.append(f"{code}.ocd_id: must look like ocd-jurisdiction/country:us/state:<xx>/government "
                          f"(or country:us/government for US Congress), got {entry['ocd_id']!r}")

        if isinstance(entry.get("archive"), dict):
            _check_block(entry["archive"], ARCHIVE_FIELDS, f"{code}.archive", errors)
            timeout = entry["archive"].get("timeout_s")
            if isinstance(timeout, int) and not isinstance(timeout, bool) and timeout <= 0:
                errors.append(f"{code}.archive.timeout_s: must be positive, got {timeout}")

        if isinstance(entry.get("enrollment"), dict):
            _check_block(entry["enrollment"], ENROLLMENT_FIELDS, f"{code}.enrollment", errors)

        status = entry.get("status")
        if isinstance(status, str) and status in STATUSES_THAT_NEED_PEOPLE_AND_ARCHIVE:
            if isinstance(entry.get("enrollment"), dict) and entry["enrollment"].get("people_refresh") is False:
                errors.append(
                    f"{code}.enrollment.people_refresh: must be true when status is {status!r}: the weekly legislator "
                    f"refresh has to include every state that has been scraped, or its votes and sponsors import "
                    f"unresolved (runbook rule 1; pilot #2, 2026-11-03). `advance-jurisdiction` sets it."
                )
            if isinstance(entry.get("archive"), dict) and entry["archive"].get("enabled") is False:
                errors.append(
                    f"{code}.archive.enabled: must be true when status is {status!r}: a scraped state's scrape is "
                    f"followed by its archive. `advance-jurisdiction` sets it."
                )

        if isinstance(entry.get("waf"), dict):
            _check_block(entry["waf"], WAF_FIELDS, f"{code}.waf", errors)
            profile = entry["waf"].get("profile")
            if isinstance(profile, str) and profile not in WAF_PROFILE_VALUES:
                errors.append(f"{code}.waf.profile: {profile!r} is not one of {sorted(WAF_PROFILE_VALUES)}")
            for field in WAF_LIMIT_FIELDS:
                _check_positive_or_null(entry["waf"], field, f"{code}.waf", errors)
            if profile == "none":
                for field in WAF_LIMIT_FIELDS:
                    if entry["waf"].get(field) is not None:
                        errors.append(f"{code}.waf.{field}: must be null for a state with no WAF profile (nothing "
                                      f"reads it), got {entry['waf'][field]!r}")
            elif isinstance(profile, str):
                for field in WAF_PROFILE_NEEDS:
                    if field in entry["waf"] and entry["waf"][field] is None:
                        errors.append(f"{code}.waf.{field}: a state with a WAF profile ({profile!r}) needs it "
                                      f"(openstates-core's resilience profile reads it), got null")

        if isinstance(entry.get("quality"), dict):
            _check_block(entry["quality"], QUALITY_FIELDS, f"{code}.quality", errors)

        if isinstance(entry.get("chambers"), dict):
            _check_block(entry["chambers"], CHAMBERS_FIELDS, f"{code}.chambers", errors)
            chambers = entry["chambers"]
            for side in ("upper", "lower"):
                if isinstance(chambers.get(side), str) and not chambers[side].strip():
                    errors.append(f"{code}.chambers.{side}: must be the chamber's name, got an empty string")
            unicameral, lower = chambers.get("unicameral"), chambers.get("lower")
            if unicameral is True and lower is not None:
                errors.append(f"{code}.chambers.lower: must be null for a one-house legislature (unicameral: true); "
                              f"its one name goes in chambers.upper, got {lower!r}")
            if unicameral is False and "lower" in chambers and lower is None:
                errors.append(f"{code}.chambers.lower: a two-house legislature (unicameral: false) needs its lower "
                              f"chamber's name, got null")

        if isinstance(entry.get("votes"), dict):
            _check_block(entry["votes"], VOTES_FIELDS, f"{code}.votes", errors)
            for field, officer in (("house_speaker_by_session", "Speaker"),
                                   ("senate_president_by_session", "Senate President")):
                officers = entry["votes"].get(field)
                if isinstance(officers, dict):
                    for session, name in officers.items():
                        # OPEN-785: a session whose officer changed maps each first day held ('YYYY-MM-DD') to a name
                        dated = code in DATED_OFFICER_STATES and isinstance(name, dict) and name and all(
                            _is_day(d) and isinstance(n, str) and n.strip() for d, n in name.items())
                        if not isinstance(session, str) or not (dated or isinstance(name, str) and name.strip()):
                            errors.append(f"{code}.votes.{field}: each entry must be a session name and the "
                                          f"{officer}'s name, or (la, ri) a map of quoted first days held "
                                          f"('YYYY-MM-DD') to names, got {session!r}: {name!r}")
            bare = entry["votes"].get("bare_key_session")
            if isinstance(bare, str) and not bare.strip():
                errors.append(f"{code}.votes.bare_key_session: must be a session name or null, got an empty string")

        if isinstance(entry.get("onboarding"), dict):
            _check_block(entry["onboarding"], ONBOARDING_FIELDS, f"{code}.onboarding", errors)

        api_keys = entry.get("api_keys")
        if isinstance(api_keys, list):
            for i, key in enumerate(api_keys):
                if not isinstance(key, str) or not key:
                    errors.append(f"{code}.api_keys[{i}]: must be a non-empty string, got {key!r}")

    # OPEN-555: code_for_scraper_module() maps a module name back to ONE entry, so two entries may not share one.
    modules = {}
    for code, entry in data.items():
        module = entry.get("scraper_module") if isinstance(entry, dict) else None
        if isinstance(module, str):
            modules.setdefault(module, []).append(code)
    for module, codes in modules.items():
        if len(codes) > 1:
            errors.append(f"{', '.join(codes)}: scraper_module {module!r} is used by more than one entry; each "
                          f"jurisdiction has its own scraper module")

    return errors


def scraper_module_for(code, manifest, fallback):
    """OPEN-555: `code`'s `scraper_module` from a loaded manifest (None: not loaded), else the caller's old override
    table `fallback` (e.g. {"us": "usa"}), else the code itself."""
    entry = (manifest or {}).get(code) if isinstance(manifest, dict) else None
    module = entry.get("scraper_module") if isinstance(entry, dict) else None
    return module if isinstance(module, str) and module else fallback.get(code, code)


def code_for_scraper_module(module, manifest, fallback):
    """OPEN-555: the manifest code whose `scraper_module` is `module`, else the caller's old table `fallback` (e.g.
    {"usa": "us"}), else the module name itself."""
    for code, entry in (manifest.items() if isinstance(manifest, dict) else ()):
        if isinstance(entry, dict) and entry.get("scraper_module") == module:
            return code
    return fallback.get(module, module)


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
