#!/usr/bin/env python3
r"""
Read-only: list Washington bills that have a "Chapter N, YYYY Laws" action but no stored chapter
citation, per session, and (with --verify) fail if any remain.

OPEN-432. Washington files a bill's session-law chapter under the version that passed (for example
ESSB 5167), but the scraper looked it up under the bare bill id (HB 1052) and got an HTTP 500, so the
citation was never stored. Upstream #5876 (the OPEN-401 catch-up, OPEN-409) fixes the lookup, but only
a bill that is scraped again picks it up, and an incremental run does not revisit enacted bills. This
lists what is still missing, writes the bill list for a targeted rescrape, and is the after-check.

With --targets (the frozen list --bill-list wrote, before the rescrape) --verify checks each listed bill
directly, so a bill that lost its Chapter action or its row cannot pass by dropping out of the "missing" set:
it must still exist, still carry its Chapter action, carry a chapter citation whose number and year match
that action, and (with --baseline, the --snapshot taken before) have no fewer actions, sponsors, versions,
documents, sources or vote events than before.

Writes nothing (the session is read-only; no repair script on purpose: the repair is a rescrape,
which replaces the bill's data from the source). A bill "has a chapter citation" when its `citations`
column holds an entry with citation_type = 'chapter' (what scrape_chapter() adds).

Usage:
  ./check-wa-chapter-citations.py                       # per-session counts
  ./check-wa-chapter-citations.py --list                # plus one line per bill missing its citation
  ./check-wa-chapter-citations.py --bill-list FILE      # write the missing bills as bill_no= arguments, 20 per line
  ./check-wa-chapter-citations.py --verify              # exit 1 if any Chapter-action bill still has no citation
  ./check-wa-chapter-citations.py --targets FILE --snapshot OUT.csv   # before the rescrape: child-row counts of the frozen list
  ./check-wa-chapter-citations.py --targets FILE --baseline OUT.csv --verify   # after: every target still enacted, cited correctly, nothing lost
Environment: OPENSTATES_DB_HOST/PORT/NAME/USER/PASSWORD, as the other scripts here.
"""
import argparse
import os
import re
import sys

import psycopg2

from quality_check import FAIL, PASS, WARN, Report

DB_CONFIG = {
    "host": os.getenv("OPENSTATES_DB_HOST", "localhost"),
    "port": int(os.getenv("OPENSTATES_DB_PORT", "5433")),
    "dbname": os.getenv("OPENSTATES_DB_NAME", "openstates"),
    "user": os.getenv("OPENSTATES_DB_USER", "openstates"),
    "password": os.getenv("OPENSTATES_DB_PASSWORD", "openstates_dev"),
}

WA_LIKE = "ocd-jurisdiction/country:us/state:wa/%"
# the status line the legislature writes when a bill becomes law: "Chapter 327, 2025 Laws."
CHAPTER_ACTION_RE = r"^Chapter [0-9]+, [0-9]{4} Laws"

BILLS_SQL = """
SELECT ls.identifier, b.identifier,
       EXISTS (SELECT 1 FROM opencivicdata_billaction a
               WHERE a.bill_id = b.id AND a.description ~ %(action_re)s) AS chapter_action,
       EXISTS (SELECT 1 FROM jsonb_array_elements(coalesce(b.citations, '[]'::jsonb)) c
               WHERE c->>'citation_type' = 'chapter') AS chapter_citation
FROM opencivicdata_bill b
JOIN opencivicdata_legislativesession ls ON ls.id = b.legislative_session_id
WHERE ls.jurisdiction_id LIKE %(like)s
ORDER BY ls.identifier, b.identifier
"""


TARGETS_SQL = """
SELECT b.identifier,
       coalesce((SELECT array_agg(a.description) FROM opencivicdata_billaction a
                 WHERE a.bill_id = b.id AND a.description ~ %(action_re)s), '{}') AS chapter_actions,
       coalesce((SELECT jsonb_agg(c) FROM jsonb_array_elements(coalesce(b.citations, '[]'::jsonb)) c
                 WHERE c->>'citation_type' = 'chapter'), '[]'::jsonb) AS chapter_citations,
       (SELECT count(*) FROM opencivicdata_billaction x WHERE x.bill_id = b.id) AS actions,
       (SELECT count(*) FROM opencivicdata_billsponsorship x WHERE x.bill_id = b.id) AS sponsors,
       (SELECT count(*) FROM opencivicdata_billversion x WHERE x.bill_id = b.id) AS versions,
       (SELECT count(*) FROM opencivicdata_billdocument x WHERE x.bill_id = b.id) AS documents,
       (SELECT count(*) FROM opencivicdata_billsource x WHERE x.bill_id = b.id) AS sources,
       (SELECT count(*) FROM opencivicdata_voteevent x WHERE x.bill_id = b.id) AS votes
FROM opencivicdata_bill b
JOIN opencivicdata_legislativesession ls ON ls.id = b.legislative_session_id
WHERE ls.jurisdiction_id LIKE %(like)s AND ls.identifier = %(session)s AND b.identifier = ANY(%(identifiers)s)
"""


def bill_no(identifier):
    """'HB 1052' -> 'HB1052', the shape the scraper's bill_no= argument takes."""
    return re.sub(r"\s+", "", identifier)


def chunks(items, size):
    """Lists of at most `size` items. run-scrape.sh names its marker files after the whole
    argument string, so one 494-bill bill_no= list would exceed the 255-byte file name limit."""
    return [items[i : i + size] for i in range(0, len(items), size)]


def read_targets(path):
    """Bill identifiers from a --bill-list file: lines of comma separated bill_no= values."""
    return [t.strip() for line in open(path) for t in line.split(",") if t.strip()]


def identifier_from_bill_no(token):
    """'HB1052' -> 'HB 1052' (the stored form)."""
    m = re.match(r"^([A-Za-z]+)\s*0*(\d+)$", token)
    return f"{m.group(1).upper()} {m.group(2)}" if m else token


def action_chapter(description):
    """(chapter number, year) from 'Chapter 327, 2025 Laws.', or None."""
    m = re.match(r"^Chapter ([0-9]+), ([0-9]{4}) Laws", description or "")
    return (m.group(1), m.group(2)) if m else None


COUNT_COLUMNS = ("actions", "sponsors", "versions", "documents", "sources", "votes")


def check_target(row, baseline=None):
    """Problems for one target bill (empty list = fine). row: dict from TARGETS_SQL or None if the
    bill is not stored; baseline: its counts before the rescrape."""
    if row is None:
        return ["bill not found"]
    problems = []
    chapters = [action_chapter(a) for a in row["chapter_actions"]]
    chapters = [c for c in chapters if c]
    if not chapters:
        problems.append("no Chapter action")
    cites = [c for c in row["chapter_citations"] if c.get("citation_type") == "chapter"]
    if not cites:
        problems.append("no chapter citation")
    elif chapters:
        want = {(f"Chapter {n}", f"WA {y} Laws") for n, y in chapters}
        have = {(c.get("citation"), c.get("publication")) for c in cites}
        if not want & have:
            problems.append(f"citation {sorted(have)} does not match the action {sorted(want)}")
    if baseline:
        for col in COUNT_COLUMNS:
            if row[col] < baseline[col]:
                problems.append(f"{col} fell from {baseline[col]} to {row[col]}")
    return problems


def summarize(rows):
    """rows: (session, identifier, chapter_action, chapter_citation) ->
    {session: {"bills": n, "chapter_action": n, "missing": [identifier, ...], "citation_without_action": n}}"""
    out = {}
    for session, identifier, action, citation in rows:
        s = out.setdefault(session, {"bills": 0, "chapter_action": 0, "missing": [], "citation_without_action": 0})
        s["bills"] += 1
        if action:
            s["chapter_action"] += 1
            if not citation:
                s["missing"].append(identifier)
        elif citation:
            s["citation_without_action"] += 1
    return out


def target_rows(cur, args):
    wanted = [identifier_from_bill_no(t) for t in read_targets(args.targets)]
    cur.execute(TARGETS_SQL, {"like": WA_LIKE, "session": args.session, "action_re": CHAPTER_ACTION_RE, "identifiers": wanted})
    cols = ["identifier", "chapter_actions", "chapter_citations", *COUNT_COLUMNS]
    found = {r[0]: dict(zip(cols, r)) for r in cur.fetchall()}
    return wanted, found


def run_targets(cur, args):
    print(f"database {DB_CONFIG['user']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']} (read-only), session {args.session}")
    wanted, found = target_rows(cur, args)
    if len(set(wanted)) != len(wanted):
        print(f"the targets file lists {len(wanted) - len(set(wanted))} bill(s) twice")
        return 1
    if args.snapshot:
        with open(args.snapshot, "w") as f:
            f.write(",".join(["identifier", *COUNT_COLUMNS]) + "\n")
            for ident in wanted:
                r = found.get(ident)
                f.write(",".join([ident, *[str(r[c]) if r else "" for c in COUNT_COLUMNS]]) + "\n")
        print(f"wrote {len(wanted)} bills ({len(found)} found) to {args.snapshot}")
        return 0
    baseline = {}
    if args.baseline:
        lines = [l.rstrip("\n").split(",") for l in open(args.baseline)][1:]
        baseline = {l[0]: {c: int(v) for c, v in zip(COUNT_COLUMNS, l[1:]) if v != ""} for l in lines}
    bad = 0
    for ident in wanted:
        base = baseline.get(ident) if baseline else None
        problems = check_target(found.get(ident), base if base else None)
        if problems:
            bad += 1
            print(f"  {ident}: " + "; ".join(problems))
    print(f"{len(wanted)} targets: {len(wanted) - bad} fine, {bad} with a problem")
    return 1 if (bad and args.verify) else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="print each bill missing its citation")
    ap.add_argument("--bill-list", help="write the missing bills to FILE, one line per run, comma separated as bill_no= takes them")
    ap.add_argument("--chunk-size", type=int, default=20, help="bills per line of --bill-list (default 20)")
    ap.add_argument("--verify", action="store_true", help="exit 1 if any Chapter-action bill has no citation")
    ap.add_argument("--targets", help="the frozen --bill-list file; with --verify, check each listed bill directly")
    ap.add_argument("--session", default="2025-2026", help="session of the --targets bills (default 2025-2026)")
    ap.add_argument("--snapshot", help="with --targets: write the targets' child-row counts to this CSV and stop")
    ap.add_argument("--baseline", help="with --targets --verify: the --snapshot taken before the rescrape")
    args = ap.parse_args()

    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_session(readonly=True)
    cur = conn.cursor()
    if args.targets:
        sys.exit(run_targets(cur, args))
    print(f"database {DB_CONFIG['user']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']} (read-only)")
    cur.execute(BILLS_SQL, {"like": WA_LIKE, "action_re": CHAPTER_ACTION_RE})
    summary = summarize(cur.fetchall())
    conn.rollback()
    conn.close()

    report = Report()
    all_missing = []
    for session, s in sorted(summary.items()):
        missing = s["missing"]
        all_missing += missing
        detail = f"{s['bills']} bills, {s['chapter_action']} with a Chapter action, {len(missing)} without the citation"
        if s["citation_without_action"]:
            detail += f"; {s['citation_without_action']} have a citation but no Chapter action"
        report.record(PASS if not missing else FAIL, f"WA {session}", detail)
        if args.list:
            for identifier in missing:
                print(f"      {identifier}")
    if not summary:
        report.record(WARN, "WA", "no Washington bills in this database")
    ok = report.summary()

    if args.bill_list:
        lines = [",".join(bill_no(i) for i in c) for c in chunks(all_missing, args.chunk_size)]
        with open(args.bill_list, "w") as f:
            f.write("".join(line + "\n" for line in lines))
        print(f"wrote {len(all_missing)} bills to {args.bill_list} ({len(lines)} lines)")
    if args.verify and not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
