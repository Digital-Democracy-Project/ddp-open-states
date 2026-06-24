#!/usr/bin/env python3
"""
Data quality check: samples bills and people from the local openstates DB,
fetches the same records from both local api-v3 (localhost:8002) and the live
v3.openstates.org API, and diffs the key fields.

Designed to stay well within the 250 req/day API rate limit by default.

Usage:
    OPENSTATES_API_KEY=<key> python3 quality_check.py
    OPENSTATES_API_KEY=<key> python3 quality_check.py --bills 10 --people 5
    OPENSTATES_API_KEY=<key> python3 quality_check.py --jurisdiction fl

Environment:
    OPENSTATES_API_KEY   Real API key for v3.openstates.org (required)
    DATABASE_URL         Local openstates DB (default: openstates:openstates_dev@localhost/openstates)
"""

import os
import sys
import json
import random
import argparse
import textwrap
import psycopg2
import requests
from collections import defaultdict

# ── Config ────────────────────────────────────────────────────────────────────

LOCAL_API  = "http://localhost:8002"
LIVE_API   = "https://v3.openstates.org"
LOCAL_KEY  = "00000000-0000-0000-0000-000000000001"
LIVE_KEY   = os.environ.get("OPENSTATES_API_KEY", "")
DB_URL     = os.environ.get(
    "DATABASE_URL",
    "postgresql://openstates:openstates_dev@localhost:5433/openstates",
)

# Jurisdictions with data in our local DB (va blocked, us handled separately)
JURISDICTIONS = ["fl", "wa", "mi", "ut", "al", "ma", "az"]
US_JURISDICTION = "us"

# OCD jurisdiction → short code (inverse of what api-v3 stores)
OCD_TO_CODE = {
    "ocd-jurisdiction/country:us/state:fl/government": "fl",
    "ocd-jurisdiction/country:us/state:wa/government": "wa",
    "ocd-jurisdiction/country:us/state:mi/government": "mi",
    "ocd-jurisdiction/country:us/state:ut/government": "ut",
    "ocd-jurisdiction/country:us/state:al/government": "al",
    "ocd-jurisdiction/country:us/state:ma/government": "ma",
    "ocd-jurisdiction/country:us/state:az/government": "az",
    "ocd-jurisdiction/country:us/government":          "us",
}

# ── Output helpers ─────────────────────────────────────────────────────────────

PASS  = "✓"
FAIL  = "✗"
WARN  = "~"
SKIP  = "-"

class Report:
    def __init__(self):
        self.checks = []

    def record(self, symbol, label, detail=""):
        self.checks.append((symbol, label, detail))
        icon = {"✓": "\033[32m✓\033[0m", "✗": "\033[31m✗\033[0m",
                "~": "\033[33m~\033[0m", "-": "\033[90m-\033[0m"}.get(symbol, symbol)
        line = f"  {icon}  {label}"
        if detail:
            line += f"  [{detail}]"
        print(line)

    def summary(self):
        total  = len(self.checks)
        passed = sum(1 for s, _, _ in self.checks if s == PASS)
        warned = sum(1 for s, _, _ in self.checks if s == WARN)
        failed = sum(1 for s, _, _ in self.checks if s == FAIL)
        skipped = sum(1 for s, _, _ in self.checks if s == SKIP)
        print()
        print("─" * 60)
        print(f"  {passed}/{total} passed  |  {warned} warnings  |  {failed} failures  |  {skipped} skipped")
        print("─" * 60)
        return failed == 0

# ── Sampling from local DB ────────────────────────────────────────────────────

def sample_bills(conn, jurisdiction_code, n):
    """Return n random (identifier, session, jurisdiction_ocd_id) tuples."""
    cur = conn.cursor()
    cur.execute("""
        SELECT b.identifier, ls.identifier AS session, j.id AS jid
        FROM opencivicdata_bill b
        JOIN opencivicdata_legislativesession ls ON b.legislative_session_id = ls.id
        JOIN opencivicdata_jurisdiction j ON ls.jurisdiction_id = j.id
        WHERE j.id LIKE %s
        ORDER BY RANDOM()
        LIMIT %s
    """, (f"%/state:{jurisdiction_code}/%", n))
    return cur.fetchall()


def sample_bills_us(conn, n):
    """Sample from US federal bills specifically."""
    cur = conn.cursor()
    cur.execute("""
        SELECT b.identifier, ls.identifier AS session, j.id AS jid
        FROM opencivicdata_bill b
        JOIN opencivicdata_legislativesession ls ON b.legislative_session_id = ls.id
        JOIN opencivicdata_jurisdiction j ON ls.jurisdiction_id = j.id
        WHERE j.id = 'ocd-jurisdiction/country:us/government'
        ORDER BY RANDOM()
        LIMIT %s
    """, (n,))
    return cur.fetchall()


def sample_people(conn, jurisdiction_code, n):
    """Return n random (person_id, name) tuples."""
    cur = conn.cursor()
    # DISTINCT + ORDER BY RANDOM() needs a subquery in PostgreSQL
    cur.execute("""
        SELECT id, name FROM (
            SELECT DISTINCT p.id, p.name
            FROM opencivicdata_person p
            JOIN opencivicdata_membership m ON m.person_id = p.id
            JOIN opencivicdata_organization o ON m.organization_id = o.id
            JOIN opencivicdata_jurisdiction j ON o.jurisdiction_id = j.id
            WHERE j.id LIKE %s
              AND o.classification IN ('upper', 'lower')
        ) sub
        ORDER BY RANDOM()
        LIMIT %s
    """, (f"%/state:{jurisdiction_code}/%", n))
    return cur.fetchall()

# ── API helpers ───────────────────────────────────────────────────────────────

def fetch_bill(base_url, api_key, jurisdiction, session, identifier):
    """Fetch a bill with votes + sponsorships from an api-v3 endpoint."""
    params = {
        "jurisdiction": jurisdiction,
        "session":      session,
        "identifier":   identifier,
        "include":      ["votes", "sponsorships", "actions"],
        "apikey":       api_key,
    }
    try:
        r = requests.get(f"{base_url}/bills", params=params, timeout=15)
        r.raise_for_status()
        results = r.json().get("results", [])
        return results[0] if results else None
    except Exception as e:
        return {"_error": str(e)}


def fetch_person(base_url, api_key, person_id):
    """Fetch a person record."""
    params = {"id": person_id, "apikey": api_key}
    try:
        r = requests.get(f"{base_url}/people", params=params, timeout=15)
        r.raise_for_status()
        results = r.json().get("results", [])
        return results[0] if results else None
    except Exception as e:
        return {"_error": str(e)}

# ── Comparison logic ──────────────────────────────────────────────────────────

def normalize(s):
    return (s or "").strip().lower()


def compare_bills(report, local, live, label):
    """Diff local vs live bill on key fields."""

    if local is None and live is None:
        report.record(SKIP, f"{label}: not found in either API")
        return
    if local is None:
        report.record(FAIL, f"{label}: missing from local api-v3")
        return
    if live is None:
        report.record(FAIL, f"{label}: missing from live API (may not exist upstream)")
        return
    if "_error" in local:
        report.record(FAIL, f"{label}: local API error", local["_error"])
        return
    if "_error" in live:
        report.record(FAIL, f"{label}: live API error", live["_error"])
        return

    # Title
    if normalize(local.get("title")) == normalize(live.get("title")):
        report.record(PASS, f"{label}: title matches")
    else:
        report.record(WARN, f"{label}: title differs",
                      f"local={repr(local.get('title','')[:40])} live={repr(live.get('title','')[:40])}")

    # Latest action
    la_local = normalize(local.get("latest_action_description") or "")
    la_live  = normalize(live.get("latest_action_description") or "")
    if la_local == la_live:
        report.record(PASS, f"{label}: latest_action matches")
    else:
        report.record(WARN, f"{label}: latest_action differs",
                      f"local={repr(la_local[:50])} live={repr(la_live[:50])}")

    # Vote event count
    # local > live is expected for UT/MI (we have fixes not yet merged upstream).
    # live > local means we're missing votes — that's the real problem.
    local_votes = local.get("votes") or []
    live_votes  = live.get("votes") or []
    lv_count, rv_count = len(local_votes), len(live_votes)
    if lv_count == rv_count:
        report.record(PASS, f"{label}: vote event count matches ({lv_count})")
    elif lv_count > rv_count:
        # We have more votes than upstream — likely our scraper fix is better
        report.record(WARN, f"{label}: local has MORE votes than live (our fix not merged?)",
                      f"local={lv_count} live={rv_count}")
    else:
        # Live has more votes than us — we're behind
        report.record(FAIL, f"{label}: local is MISSING votes vs live",
                      f"local={lv_count} live={rv_count}")

    # Vote counts on first vote event present in both
    if local_votes and live_votes:
        lv = local_votes[0]
        rv = live_votes[0]
        lc = {c["option"]: c["value"] for c in (lv.get("counts") or [])}
        rc = {c["option"]: c["value"] for c in (rv.get("counts") or [])}
        if lc == rc:
            report.record(PASS, f"{label}: first vote counts match ({lc})")
        else:
            report.record(WARN, f"{label}: first vote counts differ",
                          f"local={lc} live={rc}")

    # Sponsorship count (allow ±1 — upstream may have added one since our scrape)
    ls = len(local.get("sponsorships") or [])
    rs = len(live.get("sponsorships") or [])
    if ls == rs:
        report.record(PASS, f"{label}: sponsorship count matches ({ls})")
    elif abs(ls - rs) <= 1:
        report.record(WARN, f"{label}: sponsorship count off by 1",
                      f"local={ls} live={rs}")
    else:
        report.record(FAIL, f"{label}: sponsorship count mismatch",
                      f"local={ls} live={rs}")


def compare_people(report, local, live, label):
    if local is None and live is None:
        report.record(SKIP, f"{label}: not found in either API")
        return
    if local is None:
        report.record(FAIL, f"{label}: missing from local api-v3")
        return
    if live is None:
        report.record(FAIL, f"{label}: missing from live API")
        return
    if "_error" in local:
        report.record(FAIL, f"{label}: local error", local["_error"])
        return
    if "_error" in live:
        report.record(FAIL, f"{label}: live error", live["_error"])
        return

    # Name
    if normalize(local.get("name")) == normalize(live.get("name")):
        report.record(PASS, f"{label}: name matches ({local.get('name')})")
    else:
        report.record(WARN, f"{label}: name differs",
                      f"local={local.get('name')} live={live.get('name')}")

    # Current role
    lr = local.get("current_role") or {}
    rr = live.get("current_role") or {}
    if lr.get("org_classification") == rr.get("org_classification"):
        report.record(PASS, f"{label}: chamber matches ({lr.get('org_classification')})")
    else:
        report.record(FAIL, f"{label}: chamber mismatch",
                      f"local={lr.get('org_classification')} live={rr.get('org_classification')}")

    if str(lr.get("district")) == str(rr.get("district")):
        report.record(PASS, f"{label}: district matches ({lr.get('district')})")
    else:
        report.record(WARN, f"{label}: district differs",
                      f"local={lr.get('district')} live={rr.get('district')}")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bills",        type=int, default=5,
                        help="Bills to sample per jurisdiction (default: 5)")
    parser.add_argument("--people",       type=int, default=3,
                        help="People to sample per jurisdiction (default: 3)")
    parser.add_argument("--jurisdiction", type=str, default=None,
                        help="Limit to one jurisdiction code (e.g. fl)")
    parser.add_argument("--no-people",    action="store_true",
                        help="Skip people checks")
    args = parser.parse_args()

    if not LIVE_KEY:
        print("ERROR: set OPENSTATES_API_KEY to your live v3.openstates.org API key")
        sys.exit(1)

    jurisdictions = [args.jurisdiction] if args.jurisdiction else JURISDICTIONS
    # Add US if not limiting to a specific jurisdiction
    include_us = not args.jurisdiction or args.jurisdiction == "us"

    report = Report()
    conn = psycopg2.connect(DB_URL)

    # ── Bills ──────────────────────────────────────────────────────────────
    print(f"\n{'═'*60}")
    print(f"  BILL CHECKS  ({args.bills} per jurisdiction)")
    print(f"{'═'*60}")

    for jcode in jurisdictions:
        rows = sample_bills(conn, jcode, args.bills)
        if not rows:
            print(f"\n  [{jcode.upper()}] no bills in local DB — skipping")
            continue
        print(f"\n  [{jcode.upper()}]")
        for identifier, session, jid in rows:
            label = f"{jcode.upper()} {identifier} ({session})"
            local = fetch_bill(LOCAL_API, LOCAL_KEY, jid, session, identifier)
            live  = fetch_bill(LIVE_API,  LIVE_KEY,  jid, session, identifier)
            compare_bills(report, local, live, label)

    if include_us:
        rows = sample_bills_us(conn, args.bills)
        if rows:
            print(f"\n  [US]")
            for identifier, session, jid in rows:
                label = f"US {identifier} ({session})"
                local = fetch_bill(LOCAL_API, LOCAL_KEY, jid, session, identifier)
                live  = fetch_bill(LIVE_API,  LIVE_KEY,  jid, session, identifier)
                compare_bills(report, local, live, label)

    # ── People ─────────────────────────────────────────────────────────────
    if not args.no_people:
        print(f"\n{'═'*60}")
        print(f"  PEOPLE CHECKS  ({args.people} per jurisdiction)")
        print(f"{'═'*60}")

        for jcode in jurisdictions:
            rows = sample_people(conn, jcode, args.people)
            if not rows:
                print(f"\n  [{jcode.upper()}] no people in local DB — skipping")
                continue
            print(f"\n  [{jcode.upper()}]")
            for person_id, name in rows:
                label = f"{jcode.upper()} {name}"
                local = fetch_person(LOCAL_API, LOCAL_KEY, person_id)
                live  = fetch_person(LIVE_API,  LIVE_KEY,  person_id)
                compare_people(report, local, live, label)

    conn.close()

    # ── Rate limit estimate ────────────────────────────────────────────────
    n_jur = len(jurisdictions) + (1 if include_us else 0)
    total_reqs = n_jur * args.bills + (0 if args.no_people else n_jur * args.people)
    print(f"\n  (used ~{total_reqs * 2} API requests: {total_reqs} local + {total_reqs} live)")

    ok = report.summary()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
