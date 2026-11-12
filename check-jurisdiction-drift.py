#!/usr/bin/env python3
"""
check-jurisdiction-drift.py -- fail when a hard-coded jurisdiction list disagrees with jurisdictions.yaml
(OPEN-318).

Adding a state used to mean remembering ~25 independent lists, and they had already drifted apart (NC was
on 8 of them and missing from 6; MA and AL on some and not others). jurisdictions.yaml is now the one place
that says which jurisdictions are enrolled in what, and this script is the gate that keeps every list that
still exists in step with it. It does not change any behaviour; it only compares (and, for this repo's own
scripts since OPEN-327, checks they still read the manifest instead of keeping a list).

What it compares, each as a SET of jurisdiction codes (or a per-code value) against the manifest:

  this repo           (OPEN-327) activate.sh ARCHIVE_ENABLED_STATES, run-people-refresh.sh, start-os-api.sh (the
                      boot smoke test), quality_check.py JURISDICTIONS and run-scrape.sh ALLOW_DUPLICATES_STATES
                      now DERIVE their lists from this manifest, so the check here is that each still does (the
                      call is present and the old hand-typed list has not come back), not a set comparison
  ddp-sync (optional) config/sync_schedule.yaml: knowledge_base_embedding, bill_search_refresh,
                      openstates_scrape.cloud_path (+ its memory_backend floor), and openstates_scrape.timing,
                      which may name only states the manifest scrapes; and the SCRAPE_TIMEOUT_S /
                      ARCHIVE_TIMEOUT_S tables in its Python source. Since OPEN-521 (SYNC-152/153) ddp-sync keeps
                      NO list of who is scraped or archived: it reads the manifest's status (scraped = not probing
                      or paused) and archive.enabled itself, so there is nothing of that left to compare here.
                      Its openstates_scrape.timing says only WHEN (OPEN-124), and a timing entry for a state the
                      manifest does not scrape is drift.

  openstates-core (optional, OPEN-462) openstates/cli/text_extract.py's apply_prediff_cleaning(): its
                      `if jurisdiction_name == "<name>":` dispatch is parsed directly (an AST walk, not a
                      second hand-kept table here) into {jurisdiction name: cleaner name}, then compared
                      against every manifest entry's quality.diff_cleaner (its own `name` field maps a code
                      to the dispatch's display name; no second code->name table). A name absent from the
                      dispatch expects "none". Found MA/NC/AL stale (manifest said none, the code already
                      cleaned all three) -- this is the fix. NOT yet extended to the procedural-document
                      stage table in utils/version_ordering.py (also keyed on display name, with a second
                      copy in api-v3) -- survey row B6, a related but separate gap, left for a follow-up
                      decision rather than folded in here.

  live values (OPEN-330)  `--live LABEL:NAME=a,b,c`, repeatable: a DDP_OPENSTATES_JURISDICTIONS or
                      LEGBOT_RDS_REPLICA_JURISDICTION_ALLOWLIST value read from a real host's environment
                      (not in git), compared with enrollment.replica_routing / enrollment.legbot_replica.
                      Reading the value is the caller's job (ddp-sync's daily check does it for its own env)

  openstates-core (optional, OPEN-464)  a sibling openstates-core checkout's
                      openstates/utils/resilience_profiles.py: every manifest jurisdiction whose waf.profile
                      is not "none" is compared (both directions) with RESILIENCE_PROFILES' keys, read by a
                      static ast parse (python_dict_keys(), the same discipline as python_int_table() --
                      never imported, so this checker stays free of openstates-core's own dependency chain).
                      openstates-core is gitignored here like ddp-sync. CI checks out its public fork's main
                      (OPEN-462) and passes --require-openstates-core, so this comparison runs in CI too.

SYNC-157: ddp-sync deletes its per-state lists and tables and reads this file (scrape.sweep_import/full_walk/retry/
cadence_escalation/fargate_max_wait_s, waf.scrapebot_fallback, enrollment.broker_bill_event_signal, the cloud_path,
embedding and search_refresh lists, the memory floor and the SCRAPE_/ARCHIVE_TIMEOUT_S tables). While ddp-sync main still
has one, it is compared (the values were copied from it); once it is gone it is skipped, and ddp-sync's own tests and
start-up refuse it coming back.

actions.newest_first and voatz.* (BROKER-368) need no comparison: their only reader, ddp-broker-py, takes them from
api-v3's GET /ddp/enrollment and keeps no copy (its guard test, common/tests/test_no_state_tables.py, fails if a
per-state table comes back), so there is nothing to drift. --matrix shows them.

Deliberately NOT compared (so nobody assumes they are covered): ddp-sync's in-code fallbacks and the
manual-trigger allow-list (SYNC-57; ddp-sync dual-reads those since OPEN-328), ddp-broker-py's own code,
votebot, ddp-agents, and the version_ordering.py procedural-document table (survey row B6, OPEN-462's own PR). Each is a
follow-up under OPEN-318 (or, for B6, a question for Ramon).
Also deliberately not compared, by design (OPEN-419/OPEN-464 -- see PRIMITIVES.md's WAF-decision
catalog): cloud_collector.py's and cloud_archiver.py's own `if state == "mi"` published-cookie gates
(genuinely code, not manifest-derived behaviour, per this ticket's own scoping note below), and
ddp-agents' config/scrapebot_jurisdictions.yaml / ddp-sync's mi_cookie_publish.py (different
repos/images; waf.profile cannot predict either one, since fl shares the same profile and is not on
those lists).

Usage:
    python3 check-jurisdiction-drift.py                                  # this repo's lists
    python3 check-jurisdiction-drift.py --ddp-sync-root ../ddp-sync      # ... and ddp-sync's (or DDP_SYNC_ROOT)
    python3 check-jurisdiction-drift.py --ddp-sync-root ../ddp-sync --require-ddp-sync   # CI: a missing
                                                                          # ddp-sync checkout is an error
    python3 check-jurisdiction-drift.py --openstates-core-root ../openstates-core        # ... and quality.diff_cleaner,
                                                                          # and waf.profile vs. RESILIENCE_PROFILES
                                                                          # (or OPENSTATES_CORE_ROOT; --require-openstates-core
                                                                          # makes a missing checkout an error, same as ddp-sync)
    python3 check-jurisdiction-drift.py --live broker-prod:DDP_OPENSTATES_JURISDICTIONS=US,FL,...   # a host's env
    python3 check-jurisdiction-drift.py --matrix                         # who is enrolled in what

Exit 0: every list compared agrees. Exit 1: drift (each disagreement is printed with both sides). Exit 2:
a source could not be read or its expected shape was not found. A source that cannot be parsed is an ERROR,
never a pass: a checker that quietly checks nothing is how the staleness watchdog went blind (LESSONS.md).
"""

import argparse
import ast
import os
import re
import sys

try:
    import yaml
except ImportError:  # pragma: no cover - broken environment only
    sys.stderr.write("check-jurisdiction-drift.py requires PyYAML (see requirements-openstates.txt); "
                     "run it with the repo's venv python.\n")
    sys.exit(2)

from validate_jurisdictions import load_and_validate, _DuplicateKeyCheckingLoader

HERE = os.path.dirname(os.path.abspath(__file__))

# ddp-sync names the US scraper "usa" in its scrape tables and lists; everything else uses "us".
SYNC_SCRAPE_CODE = {"us": "usa"}

# A paused state is not scraped, and neither is one still being probed (PLAN-push-button-onboarding.md Stage 0): it is
# scraped from Stage 2, when its status moves to `scraping`. The same rule as ddp-sync's jurisdiction_enrollment.py
# (`_UNSCHEDULED_STATUSES`), which since OPEN-521 / SYNC-152 is how ddp-sync decides who it scrapes.
UNSCHEDULED_STATUSES = ("paused", "probing")


class SourceError(Exception):
    """A source file is missing or does not have the shape this checker expects."""


# ---------------------------------------------------------------------------------------------------
# extractors: each returns a set of codes, or a {code: value} dict, from one real source
# ---------------------------------------------------------------------------------------------------

def _read(path):
    try:
        with open(path) as f:
            return f.read()
    except OSError as exc:
        raise SourceError(f"cannot read {path}: {exc}")


def _one_match(pattern, text, what, path):
    """Exactly one match, or SourceError: zero means the file's shape changed under us; more than one
    means the pattern is ambiguous. Either way a silent pass would be a lie."""
    found = re.findall(pattern, text, flags=re.MULTILINE)
    if len(found) != 1:
        raise SourceError(f"{path}: expected exactly one {what}, found {len(found)} "
                          f"(pattern {pattern!r}); update this checker if the file's shape changed on purpose")
    return found[0]


def derived_from_manifest(path, call_pattern, literal_pattern, what):
    """OPEN-327: a script that derives its list from the manifest has no list to compare, so the check is that
    it still derives it: the call is present and the old hand-typed literal has not come back. Either way a
    failure is an ERROR (exit 2), never a pass: a file that quietly stopped reading the manifest, or grew its
    own list again, is exactly the drift this whole ticket exists to stop."""
    text = _read(path)
    if not re.search(call_pattern, text, flags=re.MULTILINE):
        raise SourceError(f"{path}: expected {what}, but the call is not there; it must derive this list from jurisdictions.yaml")
    if re.search(literal_pattern, text, flags=re.MULTILINE):
        raise SourceError(f"{path}: has a hard-coded list again ({what} replaced it); derive it from jurisdictions.yaml")
    return None


def _const_int(node, path):
    """An int literal or a product/sum of them (ddp-sync writes 16 * 3600)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Mult, ast.Add)):
        left, right = _const_int(node.left, path), _const_int(node.right, path)
        return left * right if isinstance(node.op, ast.Mult) else left + right
    raise SourceError(f"{path}: timeout table has a value that is not an int expression")


def _module_dict_literal(path, name):
    """Find the one module-level NAME = {...} (or NAME: Ann = {...}) dict literal in a Python
    source file and return its ast.Dict node. Shared shape-validation for python_int_table() and
    python_dict_keys() -- neither imports the module, so a source that does not have this exact
    shape (zero, more than one, or not a dict literal at all) is a SourceError, not a guess."""
    tree = ast.parse(_read(path), filename=path)
    found = []
    for node in tree.body:
        target = node.target if isinstance(node, ast.AnnAssign) else (node.targets[0] if isinstance(node, ast.Assign) else None)
        if isinstance(target, ast.Name) and target.id == name:
            found.append(node)
    if len(found) != 1 or not isinstance(found[0].value, ast.Dict):
        raise SourceError(f"{path}: expected exactly one module-level {name} dict, found {len(found)}")
    return found[0].value


def python_int_table(path, name):
    """NAME: dict[str, int] = {"fl": 16 * 3600, ..., "default": ...} -> {key: seconds}."""
    node = _module_dict_literal(path, name)
    keys = [k.value for k in node.keys]
    if len(keys) != len(set(keys)):
        raise SourceError(f"{path}: {name} has a duplicate key")
    return {k.value: _const_int(v, path) for k, v in zip(node.keys, node.values)}


def python_dict_keys(path, name):
    """NAME: dict[str, X] = {"fl": WafResilienceProfile(...), ...} -> the key set. Unlike
    python_int_table(), the values are never inspected -- RESILIENCE_PROFILES' values are
    dataclass constructor calls, not plain literals, and this check only needs to know which
    jurisdictions have an entry, not what is in it."""
    node = _module_dict_literal(path, name)
    keys = []
    for k in node.keys:
        if not (isinstance(k, ast.Constant) and isinstance(k.value, str)):
            raise SourceError(f"{path}: {name} has a key that is not a string literal")
        keys.append(k.value)
    if len(keys) != len(set(keys)):
        raise SourceError(f"{path}: {name} has a duplicate key")
    return set(keys)


def diff_cleaner_table(path):
    """{jurisdiction display name: cleaner name} from openstates-core's
    apply_prediff_cleaning() dispatch (OPEN-462) -- read directly from the AST rather than kept as a
    second, hand-maintained copy here, so a renamed, removed, or newly-added branch changes this table
    automatically instead of leaving a stale copy for quality.diff_cleaner to quietly disagree with
    (exactly how this field went stale for MA/NC/AL in the first place). The manifest convention is the
    called function's name with its leading underscore removed (e.g. `_clean_nc_text` -> `clean_nc_text`);
    a jurisdiction with no branch is not in the returned table at all -- the caller treats that as the
    expected value "none"."""
    tree = ast.parse(_read(path), filename=path)
    apply_fn = next(
        (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "apply_prediff_cleaning"),
        None,
    )
    if apply_fn is None:
        raise SourceError(f"{path}: no apply_prediff_cleaning() function found; update this checker if it moved or was renamed")

    table = {}
    for stmt in apply_fn.body:
        if not isinstance(stmt, ast.If):
            continue
        test = stmt.test
        shape_ok = (
            isinstance(test, ast.Compare)
            and isinstance(test.left, ast.Name) and test.left.id == "jurisdiction_name"
            and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq)
            and len(test.comparators) == 1
            and isinstance(test.comparators[0], ast.Constant) and isinstance(test.comparators[0].value, str)
        )
        if not shape_ok:
            raise SourceError(
                f"{path}: apply_prediff_cleaning() has an `if` this checker cannot parse (expected "
                f'`if jurisdiction_name == "X":`); update this checker if the dispatch shape changed on purpose'
            )
        name = test.comparators[0].value
        called = {
            inner.func.id
            for inner in ast.walk(stmt)
            if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name) and inner.func.id.startswith("_")
        }
        if len(called) != 1:
            raise SourceError(
                f"{path}: apply_prediff_cleaning()'s {name!r} branch calls {len(called)} distinct cleaner "
                f"function(s) ({sorted(called)}); expected exactly one"
            )
        table[name] = called.pop()[1:]
    return table


def sync_yaml(root):
    path = os.path.join(root, "config", "sync_schedule.yaml")
    try:
        data = yaml.load(_read(path), Loader=_DuplicateKeyCheckingLoader)  # duplicate keys are an error, not last-wins
    except yaml.YAMLError as exc:
        raise SourceError(f"{path}: not valid YAML (or has a duplicate key): {exc}")
    if not isinstance(data, dict):
        raise SourceError(f"{path}: not a YAML mapping")
    return data


def _sync_list(data, *keys, path_desc):
    node = data
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            raise SourceError(f"ddp-sync sync_schedule.yaml: no {path_desc}")
        node = node[key]
    return node


def _sync_optional(data, *keys):
    """A ddp-sync sync_schedule.yaml node, or None when it is absent (SYNC-157 deleted the per-state lists)."""
    node = data
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node


def _from_sync_code(code):
    return {v: k for k, v in SYNC_SCRAPE_CODE.items()}.get(code, code)


# ---------------------------------------------------------------------------------------------------
# the manifest, projected into the sets each consumer should agree with
# ---------------------------------------------------------------------------------------------------

def where(manifest, predicate):
    return {code for code, entry in manifest.items() if predicate(entry)}


def project(manifest):
    return {
        "archive": where(manifest, lambda e: e["archive"]["enabled"]),
        "people_refresh": where(manifest, lambda e: e["enrollment"]["people_refresh"]),
        "search_refresh": where(manifest, lambda e: e["enrollment"]["search_refresh"]),
        "embedding": where(manifest, lambda e: e["enrollment"]["embedding"]),
        "cloud_path": where(manifest, lambda e: e["enrollment"]["cloud_path"]),
        "api_smoke_test": where(manifest, lambda e: e["enrollment"]["api_smoke_test"]),
        "qa_sweep": where(manifest, lambda e: e["enrollment"]["qa_sweep"]),
        "replica_routing": where(manifest, lambda e: e["enrollment"]["replica_routing"]),
        "legbot_replica": where(manifest, lambda e: e["enrollment"]["legbot_replica"]),
        "allow_duplicates": where(manifest, lambda e: e["scrape"]["allow_duplicates"]),
        "cookie_provider": where(manifest, lambda e: e["waf"]["profile"] != "none"),
        "scraped": where(manifest, lambda e: e["status"] not in UNSCHEDULED_STATUSES),
        # SYNC-157: ddp-sync's per-state behaviour, now read from here
        "sweep_import": where(manifest, lambda e: e["scrape"]["sweep_import"]),
        "full_walk": where(manifest, lambda e: e["scrape"]["full_walk"]),
        "retry": where(manifest, lambda e: e["scrape"]["retry"]),
        "no_cadence_escalation": where(manifest, lambda e: not e["scrape"]["cadence_escalation"]),
        "scrapebot_fallback": where(manifest, lambda e: e["waf"]["scrapebot_fallback"]),
        "broker_bill_event_signal": where(manifest, lambda e: e["enrollment"]["broker_bill_event_signal"]),
        "fargate_max_wait_s": {f"{c}={e['scrape']['fargate_max_wait_s']}" for c, e in manifest.items()
                               if e["scrape"]["fargate_max_wait_s"] is not None},
    }


# ---------------------------------------------------------------------------------------------------
# the checks
# ---------------------------------------------------------------------------------------------------

def repo_checks(root, expect):
    """This repo's own scripts derive their lists from the manifest (OPEN-327), so each check asserts the
    derivation is still in place and returns the manifest's own set (nothing to disagree with)."""
    p = lambda name: os.path.join(root, name)

    def derived(name, call, literal, key, what):
        def run():
            derived_from_manifest(p(name), call, literal, what)
            return expect[key]
        return run

    def shell_call(field):
        return rf"jurisdiction_codes\s+{re.escape(field)}\b"

    return [
        ("archive.enabled", "activate.sh ARCHIVE_ENABLED_STATES", expect["archive"],
         derived("activate.sh", shell_call("archive.enabled"), r'^(?:export\s+)?ARCHIVE_ENABLED_STATES="[a-z]',
                 "archive", "`jurisdiction_codes archive.enabled`")),
        ("enrollment.people_refresh", "run-people-refresh.sh `for state in`", expect["people_refresh"],
         derived("run-people-refresh.sh", shell_call("enrollment.people_refresh"), r"^for state in [a-z]",
                 "people_refresh", "`jurisdiction_codes enrollment.people_refresh`")),
        ("enrollment.api_smoke_test", "start-os-api.sh boot smoke-test `for j in`", expect["api_smoke_test"],
         derived("start-os-api.sh", shell_call("enrollment.api_smoke_test"), r"^for j in [a-z]",
                 "api_smoke_test", "`jurisdiction_codes enrollment.api_smoke_test`")),
        ("enrollment.qa_sweep", "quality_check.py JURISDICTIONS", expect["qa_sweep"],
         derived("quality_check.py", r'e\["enrollment"\]\["qa_sweep"\]', r"^JURISDICTIONS\s*=\s*\[\s*['\"]",
                 "qa_sweep", "JURISDICTIONS built from enrollment.qa_sweep")),
        ("scrape.allow_duplicates", "run-scrape.sh ALLOW_DUPLICATES_STATES", expect["allow_duplicates"],
         derived("run-scrape.sh", shell_call("scrape.allow_duplicates"), r'^ALLOW_DUPLICATES_STATES="[a-z]',
                 "allow_duplicates", "`jurisdiction_codes scrape.allow_duplicates`")),
    ]


def sync_checks(sync_root, manifest, expect):
    data = sync_yaml(sync_root)
    scrape_py = os.path.join(sync_root, "src", "ddp_sync", "pipelines", "openstates_scrape.py")
    archive_py = os.path.join(sync_root, "src", "ddp_sync", "pipelines", "openstates_archive.py")
    # SYNC-157: ddp-sync deletes these lists and reads the manifest itself (its scheduler refuses a config that still has
    # one). Until that ddp-sync release is on main, its lists are still compared; once a list is gone, it is skipped
    # (None), because there is nothing left to drift.
    def archive(*k, d):
        node = _sync_optional(data, "openstates_archive", *k)
        return None if node is None else set(node)

    def scrape(*k, d):
        return _sync_optional(data, "openstates_scrape", *k)

    sets = [
        ("enrollment.embedding", "ddp-sync ...knowledge_base_embedding.jurisdictions", expect["embedding"],
         lambda: archive("knowledge_base_embedding", "jurisdictions", d="knowledge_base_embedding.jurisdictions")),
        ("enrollment.search_refresh", "ddp-sync ...bill_search_refresh.jurisdictions", expect["search_refresh"],
         lambda: archive("bill_search_refresh", "jurisdictions", d="bill_search_refresh.jurisdictions")),
        ("enrollment.cloud_path", "ddp-sync openstates_scrape.cloud_path.jurisdictions", expect["cloud_path"],
         lambda: (lambda listed: None if listed is None else {_from_sync_code(c) for c in listed})(
             scrape("cloud_path", "jurisdictions", d="cloud_path.jurisdictions"))),
    ]

    # SYNC-157: while ddp-sync main still carries its per-state behaviour lists, they must equal the manifest's new fields
    # (the values were copied from them). Each is skipped once ddp-sync has deleted it.
    def codes(node):
        return None if node is None else {_from_sync_code(str(c).lower()) for c in node}

    def retry_set():
        listed = scrape("scrape_retry", "jurisdictions", d="")
        if listed is None:
            return None
        return codes(listed) - (codes(scrape("scrape_retry", "jurisdictions_excluded", d="")) or set())

    def fargate_map():  # compared as a set of (state, seconds) pairs, like the other comparisons
        by_state = scrape("cloud_path", "fargate", "max_wait_seconds_by_jurisdiction", d="")
        return None if by_state is None else {f"{_from_sync_code(str(c).lower())}={v}" for c, v in by_state.items()}

    sets += [
        ("scrape.sweep_import", "ddp-sync openstates_scrape.sweep_import.jurisdictions", expect["sweep_import"],
         lambda: codes(scrape("sweep_import", "jurisdictions", d=""))),
        ("scrape.full_walk", "ddp-sync openstates_scrape.full_walk.jurisdictions", expect["full_walk"],
         lambda: codes(scrape("full_walk", "jurisdictions", d=""))),
        ("scrape.retry", "ddp-sync openstates_scrape.scrape_retry (jurisdictions minus jurisdictions_excluded)",
         expect["retry"], retry_set),
        ("scrape.cadence_escalation", "ddp-sync openstates_scrape.dynamic_cadence.jurisdictions_excluded",
         expect["no_cadence_escalation"], lambda: codes(scrape("dynamic_cadence", "jurisdictions_excluded", d=""))),
        ("waf.scrapebot_fallback", "ddp-sync openstates_scrape.scrapebot_fallback.jurisdictions",
         expect["scrapebot_fallback"], lambda: codes(scrape("scrapebot_fallback", "jurisdictions", d=""))),
        ("waf.scrapebot_fallback", "ddp-sync openstates_archive.scrapebot_fallback.jurisdictions",
         expect["scrapebot_fallback"], lambda: codes(_sync_optional(data, "openstates_archive", "scrapebot_fallback", "jurisdictions"))),
        ("enrollment.broker_bill_event_signal", "ddp-sync openstates_scrape.broker_bill_event_signal.jurisdictions",
         expect["broker_bill_event_signal"], lambda: codes(scrape("broker_bill_event_signal", "jurisdictions", d=""))),
        ("scrape.fargate_max_wait_s", "ddp-sync cloud_path.fargate.max_wait_seconds_by_jurisdiction",
         expect["fargate_max_wait_s"], fargate_map),
    ]

    def timeouts(table_name, source, manifest_key, key_for):
        # SYNC-157: ddp-sync deletes these copies and reads scrape/archive.timeout_s from here; skipped once gone.
        if re.search(rf"^{table_name}\b", _read(source), re.M) is None:
            return None
        table = python_int_table(source, table_name)
        if "default" not in table:
            raise SourceError(f"{source}: {table_name} has no \"default\" entry")
        return {c: table.get(key_for(c), table["default"]) for c in manifest}, {c: e[manifest_key]["timeout_s"] for c, e in manifest.items()}

    return sets, [
        ("scrape.timeout_s", "ddp-sync SCRAPE_TIMEOUT_S (default for codes with no entry)",
         lambda: timeouts("SCRAPE_TIMEOUT_S", scrape_py, "scrape", lambda c: SYNC_SCRAPE_CODE.get(c, c))),
        ("archive.timeout_s", "ddp-sync ARCHIVE_TIMEOUT_S (default for codes with no entry)",
         lambda: timeouts("ARCHIVE_TIMEOUT_S", archive_py, "archive", lambda c: c)),
    ], data


def memory_backend_floor(data, expect):
    """memory_backend_jurisdictions is a FLOOR: everyone who has ever been split to the cloud path, never
    removed on rollback (sync_schedule.yaml's own comment). So it must CONTAIN the cloud_path set. None once ddp-sync has
    deleted the list (SYNC-157: its memory backend follows the manifest's cloud_path)."""
    listed = _sync_optional(data, "openstates_scrape", "cloud_path", "memory_backend_jurisdictions")
    if listed is None:
        return None
    if not isinstance(listed, list):
        raise SourceError("ddp-sync sync_schedule.yaml: openstates_scrape.cloud_path.memory_backend_jurisdictions is not a list")
    return {_from_sync_code(c) for c in listed}


def scrape_timing(data):
    """OPEN-521: the states openstates_scrape.timing names. It is timing only (a state the manifest scrapes with no
    entry gets ddp-sync's defaults), so it must be a SUBSET of the scraped set, never a second list of who. A missing
    map is an ERROR, not an empty pass: it means ddp-sync is not on the one-pipeline-per-state layout (SYNC-152)."""
    timing = _sync_list(data, "openstates_scrape", "timing", path_desc="openstates_scrape.timing (SYNC-152)")
    if not isinstance(timing, dict):
        raise SourceError("ddp-sync sync_schedule.yaml: openstates_scrape.timing is not a mapping of state -> timing")
    return {_from_sync_code(c) for c in timing}


# ---------------------------------------------------------------------------------------------------

def _fmt(codes):
    return ", ".join(sorted(codes)) if codes else "-"


# OPEN-330: the lists that are an environment variable on a host (not in git), and the manifest set each must equal.
LIVE_ENV = {
    "DDP_OPENSTATES_JURISDICTIONS": ("enrollment.replica_routing", "replica_routing"),
    "LEGBOT_RDS_REPLICA_JURISDICTION_ALLOWLIST": ("enrollment.legbot_replica", "legbot_replica"),
}


def parse_live(items):
    """`--live LABEL:NAME=a,b,c` -> [(label, name, {codes})]. LABEL is free text saying where the value was read
    (e.g. broker-prod); NAME must be one of LIVE_ENV. Codes are compared case-insensitively ("US" == "us")."""
    parsed = []
    for item in items:
        label, sep, rest = item.partition(":")
        name, eq, value = rest.partition("=")
        if not (sep and eq) or not label.strip() or name.strip() not in LIVE_ENV:
            raise SourceError(f"--live {item!r}: expected LABEL:NAME=a,b,c with NAME one of {sorted(LIVE_ENV)}")
        parsed.append((label.strip(), name.strip(), {c.strip().lower() for c in value.split(",") if c.strip()}))
    return parsed


def run(manifest, root, sync_root, require_sync, out, live=(), openstates_core_root=None,
        require_openstates_core=False):
    """Returns (exit_code). Prints every disagreement, not just the first."""
    expect = project(manifest)
    drift, errors = [], []

    def compare_sets(field, source, want, getter):
        try:
            have = getter()
        except SourceError as exc:
            errors.append(str(exc))
            return
        if have is None:  # SYNC-157: the consumer deleted its list and reads the manifest; nothing to compare
            return
        if want != have:
            drift.append((field, source, f"in the manifest but not in {source}: {_fmt(want - have)}\n"
                                         f"    in {source} but not in the manifest: {_fmt(have - want)}"))

    for field, source, want, getter in repo_checks(root, expect):
        compare_sets(field, source, want, getter)

    if sync_root:
        try:
            sets, tables, data = sync_checks(sync_root, manifest, expect)
        except SourceError as exc:
            errors.append(str(exc))
        else:
            for field, source, want, getter in sets:
                compare_sets(field, source, want, getter)
            try:
                floor = memory_backend_floor(data, expect)
                if floor is not None and not expect["cloud_path"] <= floor:
                    drift.append(("enrollment.cloud_path", "ddp-sync cloud_path.memory_backend_jurisdictions",
                                  f"cloud_path is enrolled in the manifest but missing from the memory_backend floor: "
                                  f"{_fmt(expect['cloud_path'] - floor)}"))
            except SourceError as exc:
                errors.append(str(exc))
            try:
                extra = scrape_timing(data) - expect["scraped"]
                if extra:
                    drift.append(("status", "ddp-sync openstates_scrape.timing",
                                  f"timing for states the manifest does not scrape (status probing or paused, or "
                                  f"not in the manifest): {_fmt(extra)}"))
            except SourceError as exc:
                errors.append(str(exc))
            for field, source, getter in tables:
                try:
                    pair = getter()
                except SourceError as exc:
                    errors.append(str(exc))
                    continue
                if pair is None:  # SYNC-157: ddp-sync reads the manifest; nothing left to compare
                    continue
                have, want = pair
                bad = {c: (want[c], have[c]) for c in want if want[c] != have[c]}
                if bad:
                    drift.append((field, source, "\n".join(
                        f"    {c}: manifest {w}s, {source.split(' (')[0]} {h}s" for c, (w, h) in sorted(bad.items()))))
    elif require_sync:
        errors.append("--require-ddp-sync is set but no ddp-sync checkout was given (--ddp-sync-root / DDP_SYNC_ROOT)")
    else:
        out.write("NOTE: ddp-sync was not checked (no --ddp-sync-root / DDP_SYNC_ROOT); only this repo's lists were.\n")

    if openstates_core_root:
        try:
            table = diff_cleaner_table(os.path.join(openstates_core_root, "openstates", "cli", "text_extract.py"))
        except SourceError as exc:
            errors.append(str(exc))
        else:
            source = "openstates-core text_extract.py apply_prediff_cleaning()"
            want = {code: table.get(entry["name"], "none") for code, entry in manifest.items()}
            have = {code: entry["quality"]["diff_cleaner"] for code, entry in manifest.items()}
            bad = {c: (want[c], have[c]) for c in want if want[c] != have[c]}
            if bad:
                drift.append(("quality.diff_cleaner", source, "\n".join(
                    f"    {c}: code dispatches to {w!r}, manifest says {h!r}" for c, (w, h) in sorted(bad.items()))))
        resilience_py = os.path.join(openstates_core_root, "openstates", "utils", "resilience_profiles.py")
        compare_sets("waf.profile", "openstates-core RESILIENCE_PROFILES", expect["cookie_provider"],
                     lambda: python_dict_keys(resilience_py, "RESILIENCE_PROFILES"))
    else:
        if require_openstates_core:
            errors.append("--require-openstates-core is set but no openstates-core checkout was given (--openstates-core-root / OPENSTATES_CORE_ROOT)")
        if not require_openstates_core:
            out.write("NOTE: openstates-core was not checked (no --openstates-core-root / OPENSTATES_CORE_ROOT); "
                      "quality.diff_cleaner and waf.profile were not compared against the code.\n")

    try:
        live_values = parse_live(live)
    except SourceError as exc:
        errors.append(str(exc))
        live_values = []
    for label, name, have in live_values:
        field, key = LIVE_ENV[name]
        compare_sets(field, f"{name} on {label}", expect[key], lambda have=have: have)

    for field, source, detail in drift:
        out.write(f"DRIFT {field}: {source}\n    {detail}\n")
    for message in errors:
        out.write(f"ERROR {message}\n")
    if errors:
        return 2
    if drift:
        out.write(f"\n{len(drift)} list(s) disagree with jurisdictions.yaml. Fix the list, or the manifest if the manifest is "
                  f"what is wrong, in the same change.\n")
        return 1
    out.write(f"OK: every list compared agrees with jurisdictions.yaml ({len(manifest)} jurisdictions"
              f"{'' if sync_root else ', this repo only'}).\n")
    return 0


MATRIX_COLUMNS = ["status", "archive", "people_refresh", "search_refresh", "embedding", "cloud_path", "api_smoke_test",
                  "qa_sweep", "replica_routing", "legbot_replica", "newest_first", "voatz_creator"]


def matrix(manifest, out):
    def cell(entry, column):
        if column == "status":
            return entry[column]
        if column == "archive":
            return "yes" if entry["archive"]["enabled"] else "-"
        if column == "newest_first":  # BROKER-368
            return "yes" if entry["actions"]["newest_first"] else "-"
        if column == "voatz_creator":
            return "yes" if entry["voatz"]["creator_id"] is not None else "-"
        return "yes" if entry["enrollment"][column] else "-"

    widths = {c: max(len(c), *(len(cell(e, c)) for e in manifest.values())) for c in MATRIX_COLUMNS}
    out.write("code  " + "  ".join(c.ljust(widths[c]) for c in MATRIX_COLUMNS) + "\n")
    for code, entry in manifest.items():
        out.write(f"{code:<5} " + "  ".join(cell(entry, c).ljust(widths[c]) for c in MATRIX_COLUMNS) + "\n")


def main(argv, out=sys.stdout):
    parser = argparse.ArgumentParser(description="Compare hard-coded jurisdiction lists with jurisdictions.yaml (OPEN-318).")
    parser.add_argument("--manifest", default=os.path.join(HERE, "jurisdictions.yaml"))
    parser.add_argument("--repo-root", default=HERE, help="where activate.sh, run-scrape.sh ... live (default: this checkout)")
    parser.add_argument("--ddp-sync-root", default=os.environ.get("DDP_SYNC_ROOT"))
    parser.add_argument("--require-ddp-sync", action="store_true")
    parser.add_argument("--openstates-core-root", default=os.environ.get("OPENSTATES_CORE_ROOT"),
                        help="a sibling openstates-core checkout (CI fetches the public fork's main); when given, compares quality.diff_cleaner against "
                             "text_extract.py's apply_prediff_cleaning() (OPEN-462) and waf.profile against "
                             "openstates/utils/resilience_profiles.py's RESILIENCE_PROFILES (OPEN-464); "
                             "or OPENSTATES_CORE_ROOT")
    parser.add_argument("--require-openstates-core", action="store_true",
                        help="a missing openstates-core checkout is an error (quality.diff_cleaner and waf.profile comparisons)")
    parser.add_argument("--live", action="append", default=[], metavar="LABEL:NAME=a,b,c",
                        help="a value read from a host's environment (OPEN-330), e.g. "
                             "broker-prod:DDP_OPENSTATES_JURISDICTIONS=US,FL; repeatable; compared with the manifest")
    parser.add_argument("--matrix", action="store_true", help="print who is enrolled in what and exit")
    args = parser.parse_args(argv[1:])

    manifest, problems = load_and_validate(args.manifest)
    if problems:
        out.write(f"ERROR {args.manifest} does not validate (run validate_jurisdictions.py):\n")
        for problem in problems:
            out.write(f"  - {problem}\n")
        return 2
    if args.matrix:
        matrix(manifest, out)
        return 0
    return run(manifest, args.repo_root, args.ddp_sync_root, args.require_ddp_sync, out, args.live,
               openstates_core_root=args.openstates_core_root,
               require_openstates_core=args.require_openstates_core)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
