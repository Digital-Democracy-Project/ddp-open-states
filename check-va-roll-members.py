#!/usr/bin/env python3
"""
OPEN-429: read-only audit -- do Virginia's stored roll calls list the same members as LIS does today?

Compares, by LIS VoteID, the members stored for each Virginia vote event with what the LIS API
returns now, and sorts every difference into one of four kinds:

  dropped      a member is stored but LIS no longer lists them (OPEN-429: Del. Barry Knight, who
               died 2026-02-19, was dropped from the 2026-02-17 and 02-19 rolls)
  no-response  LIS lists a member with no response. The scraper skips these rows on purpose
               (scrapers/va/bills.py), so they are absent from stored data and a rescrape changes
               nothing. Reported separately so they are not mistaken for dropped members.
  added        LIS lists a member with a response that is not stored
  option       same member in both, but a different option

Nothing is written anywhere. Stored votes come from the Postgres replica; LIS is read with the
scraper's own key, paced, and the run stops at the first HTTP 403 or 429.

Usage:
    VA_API_KEY=<key> python3 check-va-roll-members.py --session 2026 --chamber lower
    VA_API_KEY=<key> python3 check-va-roll-members.py --bill HB410 --bill HB1256
    VA_API_KEY=<key> python3 check-va-roll-members.py --cache-dir ~/.cache/open429   # reruns are free

Environment:
    VA_API_KEY            LIS key (required; read in-process, never printed)
    OPENSTATES_DB_*       same defaults as the fix-open*.py family (host, port 5433, name, user, password)

About 0.4 s per bill with stored votes; the 2026 House (1,843 bills) takes about 13 minutes.
"""
import argparse
import collections
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import psycopg2

DB_CONFIG = {
    "host": os.getenv("OPENSTATES_DB_HOST", "localhost"),
    "port": int(os.getenv("OPENSTATES_DB_PORT", "5433")),
    "dbname": os.getenv("OPENSTATES_DB_NAME", "openstates"),
    "user": os.getenv("OPENSTATES_DB_USER", "openstates"),
    "password": os.getenv("OPENSTATES_DB_PASSWORD", "openstates_dev"),
}
JURISDICTION_LIKE = "ocd-jurisdiction/country:us/state:va/%"
LIS_BASE = "https://lis.virginia.gov"
# Our session identifier -> LIS session code.
LIS_SESSION = {"2026": "20261", "2026S1": "20262"}
# LIS response code -> the options the scraper may have stored for it.
OPTIONS = {
    "Y": {"yes"},
    "N": {"no"},
    "X": {"not voting"},
    "A": {"abstain", "other"},
    "V": {"other"},
}

STORED_SQL = """
SELECT ve.dedupe_key, ve.start_date,
       COALESCE(string_agg(pv.voter_name || '=' || pv.option, ';' ORDER BY pv.voter_name), '')
FROM opencivicdata_voteevent ve
JOIN opencivicdata_legislativesession s ON s.id = ve.legislative_session_id
JOIN opencivicdata_organization o ON o.id = ve.organization_id
LEFT JOIN opencivicdata_personvote pv ON pv.vote_event_id = ve.id
WHERE s.jurisdiction_id LIKE %(jur)s AND s.identifier = %(session)s
  AND o.classification = %(chamber)s AND ve.dedupe_key ~ '^[0-9]+-'
GROUP BY ve.id
"""


def compare_vote(stored, lis_members):
    """Differences between one stored vote and LIS's current roll.

    stored: {member name: stored option}. lis_members: [(name, response code or None), ...].
    Returns {"dropped": [names], "no-response": [names], "added": [names], "option": [names]}.
    Names are compared stripped; LIS lists a member once per roll.
    """
    live = {}
    for name, code in lis_members:
        live[(name or "").strip()] = code
    stored = {k.strip(): v for k, v in stored.items()}
    out = {"dropped": [], "no-response": [], "added": [], "option": []}
    for name in sorted(set(stored) - set(live)):
        out["dropped"].append(name)
    for name in sorted(set(live) - set(stored)):
        out["no-response" if live[name] is None else "added"].append(name)
    for name in sorted(set(live) & set(stored)):
        code = live[name]
        if code is None or stored[name] not in OPTIONS.get(code, set()):
            out["option"].append(name)
    return out


def summarize(results):
    """results: [(vote key, bill, date, compare_vote output)] -> printable counters."""
    totals = collections.Counter()
    by_kind = {k: collections.Counter() for k in ("dropped", "no-response", "added", "option")}
    dates = {k: collections.Counter() for k in by_kind}
    for _key, _bill, date, diff in results:
        totals["compared"] += 1
        if not any(diff.values()):
            totals["identical"] += 1
        for kind, names in diff.items():
            if names:
                totals["votes with " + kind] += 1
                dates[kind][date] += 1
            for n in names:
                by_kind[kind][n] += 1
    return totals, by_kind, dates


class Lis:
    def __init__(self, key, pace, cache_dir=None):
        self.headers = {"WebAPIKey": key, "Accept": "application/json", "User-Agent": "DDP-datacheck"}
        self.pace, self.cache_dir, self.last = pace, cache_dir, 0.0

    def _call(self, path, params=None, post=None):
        wait = self.pace - (time.time() - self.last)
        if wait > 0:
            time.sleep(wait)
        url = LIS_BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
        headers, data = dict(self.headers), None
        if post is not None:
            headers["Content-Type"], data = "application/json", json.dumps(post).encode()
        for attempt in range(2):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=headers, data=data), timeout=60) as r:
                    self.last = time.time()
                    return json.loads(r.read())
            except urllib.error.HTTPError as e:
                self.last = time.time()
                if e.code in (403, 429):
                    raise SystemExit("STOP: HTTP %d from LIS on %s; not retrying" % (e.code, path))
                if attempt:
                    return None
            time.sleep(2)

    def legislation_ids(self, session_code):
        body = self._call(
            "/Legislation/api/getlegislationlistasync", post={"SessionCode": session_code, "IncludeFailed": True}
        )
        return {r["LegislationNumber"]: r["LegislationID"] for r in (body or {}).get("Legislations", [])}

    def votes(self, session_code, legislation_id):
        cache = self.cache_dir and os.path.join(self.cache_dir, "%s-%s.json" % (session_code, legislation_id))
        if cache and os.path.exists(cache):
            return json.load(open(cache))
        body = self._call(
            "/Vote/api/getvotebyidasync", {"sessionCode": session_code, "legislationID": str(legislation_id)}
        )
        votes = {}
        for v in (body or {}).get("Votes", []):
            votes.setdefault(
                str(v["VoteID"]),
                [(m["MemberDisplayName"], m.get("ResponseCode")) for m in v.get("VoteMember", [])],
            )
        if cache:
            os.makedirs(self.cache_dir, exist_ok=True)
            json.dump(votes, open(cache, "w"))
        return votes


def load_stored(session, chamber, bills=None):
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_session(readonly=True)
    cur = conn.cursor()
    cur.execute(STORED_SQL, {"jur": JURISDICTION_LIKE, "session": session, "chamber": chamber})
    stored = {}
    for dedupe_key, date, members in cur.fetchall():
        # The scraper builds the key as "<LIS VoteID>-<LIS legislation number>"; use that bill,
        # not the vote's bill link, because it is the one LIS files the vote under.
        m = re.match(r"^(\d+)-(.+)$", dedupe_key)
        bill = m.group(2).strip()
        if bills and bill.replace(" ", "") not in bills:
            continue
        mem = {}
        for item in filter(None, members.split(";")):
            name, option = item.rsplit("=", 1)
            mem[name] = option
        stored[(bill, m.group(1))] = (date, mem)
    conn.close()
    return stored


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--session", default="2026", choices=sorted(LIS_SESSION))
    ap.add_argument("--chamber", default="lower", choices=["lower", "upper"])
    ap.add_argument("--bill", action="append", help="limit to a bill, e.g. HB410 (repeatable)")
    ap.add_argument("--pace", type=float, default=0.4, help="seconds between LIS requests")
    ap.add_argument("--cache-dir", help="keep each LIS response here so reruns make no requests")
    args = ap.parse_args()

    key = os.getenv("VA_API_KEY")
    if not key:
        sys.exit("VA_API_KEY is not set")
    bills = {b.replace(" ", "") for b in args.bill} if args.bill else None
    stored = load_stored(args.session, args.chamber, bills)
    print("stored votes read: %d (%s, %s)" % (len(stored), args.session, args.chamber))

    lis = Lis(key, args.pace, args.cache_dir)
    code = LIS_SESSION[args.session]
    ids = lis.legislation_ids(code)
    by_bill = collections.defaultdict(list)
    for (bill, vote_id), (date, mem) in stored.items():
        by_bill[bill].append((vote_id, date, mem))

    results, not_found = [], []
    for bill in sorted(by_bill):
        lid = ids.get(bill.replace(" ", ""))
        live = lis.votes(code, lid) if lid else None
        for vote_id, date, mem in by_bill[bill]:
            if live is None or vote_id not in live:
                not_found.append((bill, vote_id))
                continue
            results.append((vote_id, bill, date, compare_vote(mem, live[vote_id])))

    totals, by_kind, dates = summarize(results)
    print("\n".join("%-28s %d" % (k, v) for k, v in sorted(totals.items())))
    print("stored votes LIS no longer returns:", len(not_found))
    for kind in ("dropped", "added", "option", "no-response"):
        if by_kind[kind]:
            print("\n%s (votes affected per member):" % kind)
            for name, n in by_kind[kind].most_common(10):
                print("  %-34s %d" % (name, n))
            print("  dates:", ", ".join("%s x%d" % (d, n) for d, n in sorted(dates[kind].items())[:12]))


if __name__ == "__main__":
    main()
