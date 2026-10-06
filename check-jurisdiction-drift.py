#!/usr/bin/env python3
"""
check-jurisdiction-drift.py -- fail when a hard-coded jurisdiction list disagrees with jurisdictions.yaml
(OPEN-318).

Adding a state used to mean remembering ~25 independent lists, and they had already drifted apart (NC was
on 8 of them and missing from 6; MA and AL on some and not others). jurisdictions.yaml is now the one place
that says which jurisdictions are enrolled in what, and this script is the gate that keeps every list that
still exists in step with it. It does not change any behaviour: nothing reads the manifest at run time yet
(the lists are still the consumers); it only compares.

What it compares, each as a SET of jurisdiction codes (or a per-code value) against the manifest:

  this repo           activate.sh ARCHIVE_ENABLED_STATES, run-people-refresh.sh, start-os-api.sh (the boot smoke
                      test), quality_check.py JURISDICTIONS, run-scrape.sh ALLOW_DUPLICATES_STATES
  ddp-sync (optional) config/sync_schedule.yaml: openstates_archive (jurisdictions + schedule),
                      knowledge_base_embedding, bill_search_refresh, openstates_scrape (primary, secondary,
                      cloud_path); and the SCRAPE_TIMEOUT_S / ARCHIVE_TIMEOUT_S tables in its Python source

Deliberately NOT compared (so nobody assumes they are covered): ddp-sync's in-code fallbacks and the
manual-trigger allow-list (SYNC-57), the DDP_OPENSTATES_JURISDICTIONS and LEGBOT_RDS_REPLICA_JURISDICTION_
ALLOWLIST environment values (live values are not in git), ddp-broker-py, votebot, ddp-agents, the per-feature
opt-in lists (sweep_import, scrape_retry, full_walk), and run-all-scrapes.sh (the retired nightly runner).
Each is a follow-up under OPEN-318.

Usage:
    python3 check-jurisdiction-drift.py                                  # this repo's lists
    python3 check-jurisdiction-drift.py --ddp-sync-root ../ddp-sync      # ... and ddp-sync's (or DDP_SYNC_ROOT)
    python3 check-jurisdiction-drift.py --ddp-sync-root ../ddp-sync --require-ddp-sync   # CI: a missing
                                                                          # ddp-sync checkout is an error
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

from validate_jurisdictions import load_and_validate

HERE = os.path.dirname(os.path.abspath(__file__))

# ddp-sync names the US scraper "usa" in its scrape tables and lists; everything else uses "us".
SYNC_SCRAPE_CODE = {"us": "usa"}


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


def shell_comma_list(path, variable):
    """export VAR="a,b,c" / VAR="a,b,c" at the start of a line."""
    value = _one_match(rf'^(?:export\s+)?{variable}="([^"]*)"', _read(path), f"{variable}= assignment", path)
    return {c.strip() for c in value.split(",") if c.strip()}


def shell_for_loop(path, variable):
    """for <variable> in a b c; do  at the start of a line."""
    value = _one_match(rf"^for {variable} in ([a-z ]+); do", _read(path), f"`for {variable} in ...; do` loop", path)
    return set(value.split())


def python_list(path, name):
    """NAME = ["a", "b"] at module level, evaluated as a literal."""
    tree = ast.parse(_read(path), filename=path)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            try:
                return set(ast.literal_eval(node.value))
            except ValueError as exc:
                raise SourceError(f"{path}: {name} is not a literal list: {exc}")
    raise SourceError(f"{path}: no module-level {name} assignment found")


def _const_int(node, path):
    """An int literal or a product/sum of them (ddp-sync writes 16 * 3600)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Mult, ast.Add)):
        left, right = _const_int(node.left, path), _const_int(node.right, path)
        return left * right if isinstance(node.op, ast.Mult) else left + right
    raise SourceError(f"{path}: timeout table has a value that is not an int expression")


def python_int_table(path, name):
    """NAME: dict[str, int] = {"fl": 16 * 3600, ..., "default": ...} -> {key: seconds}."""
    tree = ast.parse(_read(path), filename=path)
    for node in tree.body:
        target = node.target if isinstance(node, ast.AnnAssign) else (node.targets[0] if isinstance(node, ast.Assign) else None)
        if isinstance(target, ast.Name) and target.id == name and isinstance(node.value, ast.Dict):
            return {k.value: _const_int(v, path) for k, v in zip(node.value.keys, node.value.values)}
    raise SourceError(f"{path}: no module-level {name} dict found")


def sync_yaml(root):
    path = os.path.join(root, "config", "sync_schedule.yaml")
    data = yaml.safe_load(_read(path))
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
        "allow_duplicates": where(manifest, lambda e: e["scrape"]["allow_duplicates"]),
        # A paused jurisdiction is on no scrape schedule whatever its (required) tier field says.
        "primary": where(manifest, lambda e: e["tier"] == "primary" and e["status"] != "paused"),
        "secondary": where(manifest, lambda e: e["tier"] == "secondary" and e["status"] != "paused"),
    }


# ---------------------------------------------------------------------------------------------------
# the checks
# ---------------------------------------------------------------------------------------------------

def repo_checks(root, expect):
    p = lambda name: os.path.join(root, name)
    return [
        ("archive.enabled", "activate.sh ARCHIVE_ENABLED_STATES", expect["archive"],
         lambda: shell_comma_list(p("activate.sh"), "ARCHIVE_ENABLED_STATES")),
        ("enrollment.people_refresh", "run-people-refresh.sh `for state in`", expect["people_refresh"],
         lambda: shell_for_loop(p("run-people-refresh.sh"), "state")),
        ("enrollment.api_smoke_test", "start-os-api.sh boot smoke-test `for j in`", expect["api_smoke_test"],
         lambda: shell_for_loop(p("start-os-api.sh"), "j")),
        ("enrollment.qa_sweep", "quality_check.py JURISDICTIONS", expect["qa_sweep"],
         lambda: python_list(p("quality_check.py"), "JURISDICTIONS")),
        ("scrape.allow_duplicates", "run-scrape.sh ALLOW_DUPLICATES_STATES", expect["allow_duplicates"],
         lambda: shell_comma_list(p("run-scrape.sh"), "ALLOW_DUPLICATES_STATES")),
    ]


def sync_checks(sync_root, manifest, expect):
    data = sync_yaml(sync_root)
    scrape_py = os.path.join(sync_root, "src", "ddp_sync", "pipelines", "openstates_scrape.py")
    archive_py = os.path.join(sync_root, "src", "ddp_sync", "pipelines", "openstates_archive.py")
    archive = lambda *k, d: set(_sync_list(data, "openstates_archive", *k, path_desc=d))
    scrape = lambda *k, d: _sync_list(data, "openstates_scrape", *k, path_desc=d)

    def primary():
        block = scrape("primary", d="openstates_scrape.primary")
        return {_from_sync_code(k) for k, v in block.items() if isinstance(v, dict) and v.get("enabled", True)}

    sets = [
        ("archive.enabled", "ddp-sync openstates_archive.jurisdictions", expect["archive"],
         lambda: archive("jurisdictions", d="openstates_archive.jurisdictions")),
        ("archive.enabled", "ddp-sync openstates_archive.schedule (keys)", expect["archive"],
         lambda: set(_sync_list(data, "openstates_archive", "schedule", path_desc="openstates_archive.schedule"))),
        ("enrollment.embedding", "ddp-sync ...knowledge_base_embedding.jurisdictions", expect["embedding"],
         lambda: archive("knowledge_base_embedding", "jurisdictions", d="knowledge_base_embedding.jurisdictions")),
        ("enrollment.search_refresh", "ddp-sync ...bill_search_refresh.jurisdictions", expect["search_refresh"],
         lambda: archive("bill_search_refresh", "jurisdictions", d="bill_search_refresh.jurisdictions")),
        ("tier: primary", "ddp-sync openstates_scrape.primary (enabled)", expect["primary"], primary),
        ("tier: secondary", "ddp-sync openstates_scrape.secondary.jurisdictions", expect["secondary"],
         lambda: set(scrape("secondary", "jurisdictions", d="openstates_scrape.secondary.jurisdictions"))),
        ("enrollment.cloud_path", "ddp-sync openstates_scrape.cloud_path.jurisdictions", expect["cloud_path"],
         lambda: {_from_sync_code(c) for c in scrape("cloud_path", "jurisdictions", d="cloud_path.jurisdictions")}),
    ]

    def timeouts(table_name, source, manifest_key, key_for):
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
    removed on rollback (sync_schedule.yaml's own comment). So it must CONTAIN the cloud_path set."""
    cp = _sync_list(data, "openstates_scrape", "cloud_path", path_desc="cloud_path")
    floor = {_from_sync_code(c) for c in cp.get("memory_backend_jurisdictions", [])}
    return floor


# ---------------------------------------------------------------------------------------------------

def _fmt(codes):
    return ", ".join(sorted(codes)) if codes else "-"


def run(manifest, root, sync_root, require_sync, out):
    """Returns (exit_code). Prints every disagreement, not just the first."""
    expect = project(manifest)
    drift, errors = [], []

    def compare_sets(field, source, want, getter):
        try:
            have = getter()
        except SourceError as exc:
            errors.append(str(exc))
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
                if not expect["cloud_path"] <= floor:
                    drift.append(("enrollment.cloud_path", "ddp-sync cloud_path.memory_backend_jurisdictions",
                                  f"cloud_path is enrolled in the manifest but missing from the memory_backend floor: "
                                  f"{_fmt(expect['cloud_path'] - floor)}"))
            except SourceError as exc:
                errors.append(str(exc))
            for field, source, getter in tables:
                try:
                    have, want = getter()
                except SourceError as exc:
                    errors.append(str(exc))
                    continue
                bad = {c: (want[c], have[c]) for c in want if want[c] != have[c]}
                if bad:
                    drift.append((field, source, "\n".join(
                        f"    {c}: manifest {w}s, {source.split(' (')[0]} {h}s" for c, (w, h) in sorted(bad.items()))))
    elif require_sync:
        errors.append("--require-ddp-sync is set but no ddp-sync checkout was given (--ddp-sync-root / DDP_SYNC_ROOT)")
    else:
        out.write("NOTE: ddp-sync was not checked (no --ddp-sync-root / DDP_SYNC_ROOT); only this repo's lists were.\n")

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


MATRIX_COLUMNS = ["status", "tier", "archive", "people_refresh", "search_refresh", "embedding", "cloud_path", "api_smoke_test", "qa_sweep"]


def matrix(manifest, out):
    def cell(entry, column):
        if column in ("status", "tier"):
            return entry[column]
        if column == "archive":
            return "yes" if entry["archive"]["enabled"] else "-"
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
    return run(manifest, args.repo_root, args.ddp_sync_root, args.require_ddp_sync, out)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
