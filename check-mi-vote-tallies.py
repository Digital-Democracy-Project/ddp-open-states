#!/usr/bin/env python3
r"""
Read-only: compare each stored Michigan roll call's voters with the tally printed in its own
motion text ("... Roll Call # 319 YEAS 22 NAYS 13 EXCUSED 2 NOT VOTING 0").

OPEN-424. Michigan's journals were read wrongly in two ways (a page decoded with the wrong
character set, and table rows whose option header sits before the names it does not label), so
some stored votes carry no Yea voters, or count excused members as nays. The official tally is in
the vote's own motion text, so the check needs no outside data. Run it before a targeted rescrape
to list what is wrong, and again after to show it is fixed.

Writes nothing (the session is read-only). Verdict per vote, comparing stored yes/no voter rows
with the declared YEAS/NAYS:

  ok         both match
  no-yea     declared yeas, stored 0                 (the OPEN-424 headline shape)
  nays-high  yeas right, stored nays above declared  (excused counted as nays)
  other      anything else

Usage:
  ./check-mi-vote-tallies.py                      # all of 2025-2026, summary
  ./check-mi-vote-tallies.py --list               # plus one line per disagreeing vote
  ./check-mi-vote-tallies.py --bills FILE --list  # only these bills ("SB 415" per line, or a JSON list)
  ./check-mi-vote-tallies.py --bills FILE --expect-clean   # exit 1 if any listed bill still disagrees,
                                                           # exit 2 if a listed bill had no vote it could audit (needs --bills;
                                                           # a disagreement exits 1 even if a bill is also unaudited)

Votes whose motion text has no YEAS/NAYS tally are counted and skipped, not guessed at.
"""
import argparse
import collections
import json
import os
import re
import sys

import psycopg2

DB_CONFIG = {
    "host": os.getenv("OPENSTATES_DB_HOST", "localhost"),
    "port": int(os.getenv("OPENSTATES_DB_PORT", "5433")),
    "dbname": os.getenv("OPENSTATES_DB_NAME", "openstates"),
    "user": os.getenv("OPENSTATES_DB_USER", "openstates"),
    "password": os.getenv("OPENSTATES_DB_PASSWORD", "openstates_dev"),
}

MI_LIKE = "ocd-jurisdiction/country:us/state:mi/%"

VOTES_SQL = """
SELECT ve.id, o.classification, ve.start_date, ve.motion_text, b.identifier,
       count(*) FILTER (WHERE pv.option = 'yes') AS yes,
       count(*) FILTER (WHERE pv.option = 'no') AS no
FROM opencivicdata_voteevent ve
JOIN opencivicdata_legislativesession ls ON ls.id = ve.legislative_session_id
JOIN opencivicdata_organization o ON o.id = ve.organization_id
JOIN opencivicdata_bill b ON b.id = ve.bill_id
LEFT JOIN opencivicdata_personvote pv ON pv.vote_event_id = ve.id
WHERE ls.jurisdiction_id LIKE %(like)s AND ls.identifier = %(session)s
GROUP BY ve.id, o.classification, ve.start_date, ve.motion_text, b.identifier
ORDER BY ve.start_date, b.identifier
"""


def declared_tally(motion_text):
    """(yeas, nays) printed in the motion text, or None when it carries no tally."""
    yeas = re.search(r"YEAS\W{0,3}(\d+)", motion_text or "", re.I)
    nays = re.search(r"NAYS\W{0,3}(\d+)", motion_text or "", re.I)
    if not (yeas and nays):
        return None
    return int(yeas.group(1)), int(nays.group(1))


def verdict(stored_yes, stored_no, declared):
    yeas, nays = declared
    if (stored_yes, stored_no) == (yeas, nays):
        return "ok"
    if stored_yes == 0 and yeas > 0:
        return "no-yea"
    if stored_yes == yeas and stored_no > nays:
        return "nays-high"
    return "other"


def unaudited_bills(wanted, audited):
    """Listed bills with no audited vote: absent from the database, or every vote skipped for
    lack of a tally. --expect-clean must not call these clean."""
    return sorted(set(wanted) - set(audited))


def read_bills(path):
    text = open(path).read().strip()
    if text.startswith("["):
        return {b.strip() for b in json.loads(text)}
    return {line.strip() for line in text.splitlines() if line.strip()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--session", default="2025-2026")
    ap.add_argument("--bills", help="file of bill identifiers to limit to")
    ap.add_argument("--list", action="store_true", help="print each disagreeing vote")
    ap.add_argument("--expect-clean", action="store_true", help="exit 1 if any checked vote disagrees")
    args = ap.parse_args()
    bills = read_bills(args.bills) if args.bills else None
    if bills is not None and not bills:
        sys.exit("--bills file lists no bills; refusing to report an empty audit as clean")

    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_session(readonly=True)
    cur = conn.cursor()
    print(f"database {DB_CONFIG['user']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']} (read-only), session {args.session}")
    cur.execute(VOTES_SQL, {"like": MI_LIKE, "session": args.session})

    counts = collections.Counter()
    bad = []
    audited = set()
    for vid, chamber, date, motion, bill, yes, no in cur.fetchall():
        if bills is not None and bill not in bills:
            continue
        tally = declared_tally(motion)
        if tally is None:
            counts[(chamber, "no tally in motion text")] += 1
            continue
        audited.add(bill)
        v = verdict(yes, no, tally)
        counts[(chamber, v)] += 1
        if v != "ok":
            bad.append((chamber, str(date), bill, v, f"stored {yes}/{no}", f"declared {tally[0]}/{tally[1]}", vid))
    conn.rollback()
    conn.close()

    for (chamber, v), n in sorted(counts.items()):
        print(f"  {chamber:6} {v:22} {n}")
    print(f"disagreeing votes: {len(bad)}")
    if args.list:
        for row in bad:
            print("  " + "  ".join(row))
    missing = unaudited_bills(bills, audited) if bills is not None else []
    if missing:
        print(f"listed bills with no audited vote (not found, or no tally in any motion text): {missing}")
    if args.expect_clean and bad:
        sys.exit(1)
    if args.expect_clean and missing:
        sys.exit(2)


if __name__ == "__main__":
    main()
