#!/usr/bin/env python3
r"""
Read-only: list Washington bills that have a "Chapter N, YYYY Laws" action but no stored chapter
citation, per session, and (with --verify) fail if any remain.

OPEN-432. Washington files a bill's session-law chapter under the version that passed (for example
ESSB 5167), but the scraper looked it up under the bare bill id (HB 1052) and got an HTTP 500, so the
citation was never stored. Upstream #5876 (the OPEN-401 catch-up, OPEN-409) fixes the lookup, but only
a bill that is scraped again picks it up, and an incremental run does not revisit enacted bills. This
lists what is still missing, writes the bill list for a targeted rescrape, and is the after-check.

Writes nothing (the session is read-only; no repair script on purpose: the repair is a rescrape,
which replaces the bill's data from the source). A bill "has a chapter citation" when its `citations`
column holds an entry with citation_type = 'chapter' (what scrape_chapter() adds).

Usage:
  ./check-wa-chapter-citations.py                       # per-session counts
  ./check-wa-chapter-citations.py --list                # plus one line per bill missing its citation
  ./check-wa-chapter-citations.py --bill-list FILE      # write the missing bills as bill_no= arguments (HB1052,...)
  ./check-wa-chapter-citations.py --verify              # exit 1 if any Chapter-action bill still has no citation
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


def bill_no(identifier):
    """'HB 1052' -> 'HB1052', the shape the scraper's bill_no= argument takes."""
    return re.sub(r"\s+", "", identifier)


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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="print each bill missing its citation")
    ap.add_argument("--bill-list", help="write the missing bills, comma separated as bill_no= takes them, to FILE")
    ap.add_argument("--verify", action="store_true", help="exit 1 if any Chapter-action bill has no citation")
    args = ap.parse_args()

    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_session(readonly=True)
    cur = conn.cursor()
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
        with open(args.bill_list, "w") as f:
            f.write(",".join(bill_no(i) for i in all_missing) + "\n")
        print(f"wrote {len(all_missing)} bills to {args.bill_list}")
    if args.verify and not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
