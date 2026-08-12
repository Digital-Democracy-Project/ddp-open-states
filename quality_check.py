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
import re
import sys
import json
import time
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

# Jurisdictions where a bill has two permanent, separate upstream identifiers over
# its life (a docket number assigned at filing, a bill number assigned once read
# in) and our own scraper deliberately keeps only one -- see
# PLAN-coverage-completeness-check.md §10 (MA: HD/SD docket numbers vs. H/S bill
# numbers). A naive Tier 1 identifier-set diff overstates the real gap for any
# jurisdiction with this shape by counting live's permanent docket-stage record as
# "missing" even though the bill is fully present locally under its bill number.
# Absent here == unaffected: run_coverage_check()'s behavior is unchanged for any
# jurisdiction not in this map.
DOCKET_PREFIX_MAP = {
    "ma": {"docket_prefixes": ("HD", "SD")},
    # FL: a Senate/House bill is filed under a temporary SPB/HPB docket number,
    # then replaced in place by a permanent SB/HB (or CS/SB, CS/HB) number once
    # formally read in -- confirmed live (OPEN-63): flsenate.gov/Session/Bill/2026/7000
    # (an SPB 7000 list entry's own URL) now renders as "CS/SB 7000", no trace of
    # the old identifier. Live's API keeps the frozen SPB/HPB record permanently
    # as its own entity even though the site itself has moved on -- same shape as
    # MA's HD/SD above.
    "fl": {"docket_prefixes": ("SPB", "HPB")},
}


def split_missing_by_docket_prefix(missing, jurisdiction):
    """Split a Tier 1 `missing` set into "real" (bills genuinely absent locally)
    and "docket_duplicate" (live's permanent docket-stage record of a bill we
    already have under its bill number -- not a real gap, see DOCKET_PREFIX_MAP
    above). Jurisdictions absent from DOCKET_PREFIX_MAP get `missing` back
    unchanged as "real" with an empty docket_duplicate set."""
    config = DOCKET_PREFIX_MAP.get(jurisdiction)
    if not config:
        return {"real": set(missing), "docket_duplicate": set()}

    docket_prefixes = tuple(config["docket_prefixes"])
    real, docket_duplicate = set(), set()
    for identifier in missing:
        if identifier.startswith(docket_prefixes):
            docket_duplicate.add(identifier)
        else:
            real.add(identifier)
    return {"real": real, "docket_duplicate": docket_duplicate}


def breakdown_by_prefix(identifiers):
    """Count identifiers by their leading alphabetic prefix, e.g. {'H': 61, 'S':
    101, 'HD': 4765, 'SD': 2656} -- informational only, generalizes the by-hand
    prefix table PLAN-coverage-completeness-check.md §10 built for MA to any
    jurisdiction's Tier 1 output."""
    counts = defaultdict(int)
    for identifier in identifiers:
        match = re.match(r"^[A-Za-z]+", identifier)
        counts[match.group(0) if match else identifier] += 1
    return dict(counts)

# ── Output helpers ─────────────────────────────────────────────────────────────

PASS  = "✓"
FAIL  = "✗"
WARN  = "~"
SKIP  = "-"


class Tee:
    """Write to multiple streams at once (console + log file)."""
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for s in self.streams:
            s.write(data)

    def flush(self):
        for s in self.streams:
            s.flush()


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


def fetch_all_local_identifiers(conn, jurisdiction_code, session):
    """Every bill identifier we have locally for a jurisdiction + session.
    US federal has no `state:` component in its OCD id (unlike every state
    jurisdiction), so it needs an exact match instead of the LIKE pattern below --
    same split sample_bills()/sample_bills_us() already use for the same reason."""
    cur = conn.cursor()
    if jurisdiction_code == "us":
        cur.execute("""
            SELECT b.identifier FROM opencivicdata_bill b
            JOIN opencivicdata_legislativesession ls ON b.legislative_session_id = ls.id
            JOIN opencivicdata_jurisdiction j ON ls.jurisdiction_id = j.id
            WHERE j.id = 'ocd-jurisdiction/country:us/government' AND ls.identifier = %s
        """, (session,))
    else:
        cur.execute("""
            SELECT b.identifier FROM opencivicdata_bill b
            JOIN opencivicdata_legislativesession ls ON b.legislative_session_id = ls.id
            JOIN opencivicdata_jurisdiction j ON ls.jurisdiction_id = j.id
            WHERE j.id LIKE %s AND ls.identifier = %s
        """, (f"%/state:{jurisdiction_code}/%", session))
    return {row[0] for row in cur.fetchall()}


def sample_local_bills_for_session(conn, jurisdiction_code, session, limit=None, random_order=False):
    """Identifiers for a jurisdiction + session, sampled entirely from the local DB --
    no live API pagination needed. This is what lets Tier 2 run standalone: it doesn't
    need Tier 1's public/local diff, just a starting set of bills to check individually
    against live. Same us/state: split as fetch_all_local_identifiers, for the same
    reason (US federal's OCD id has no state: component)."""
    cur = conn.cursor()
    order_clause = "ORDER BY RANDOM()" if random_order else "ORDER BY b.identifier"
    limit_clause = "LIMIT %s" if limit else ""
    if jurisdiction_code == "us":
        params = (session, limit) if limit else (session,)
        cur.execute(f"""
            SELECT b.identifier FROM opencivicdata_bill b
            JOIN opencivicdata_legislativesession ls ON b.legislative_session_id = ls.id
            JOIN opencivicdata_jurisdiction j ON ls.jurisdiction_id = j.id
            WHERE j.id = 'ocd-jurisdiction/country:us/government' AND ls.identifier = %s
            {order_clause} {limit_clause}
        """, params)
    else:
        like_pattern = f"%/state:{jurisdiction_code}/%"
        params = (like_pattern, session, limit) if limit else (like_pattern, session)
        cur.execute(f"""
            SELECT b.identifier FROM opencivicdata_bill b
            JOIN opencivicdata_legislativesession ls ON b.legislative_session_id = ls.id
            JOIN opencivicdata_jurisdiction j ON ls.jurisdiction_id = j.id
            WHERE j.id LIKE %s AND ls.identifier = %s
            {order_clause} {limit_clause}
        """, params)
    return [row[0] for row in cur.fetchall()]


def fetch_all_public_identifiers(jurisdiction, session, api_key):
    """Every bill identifier the live API has for a jurisdiction + session (paginated).
    Sleeps between pages to stay under the licensed tier's 2 req/sec limit (§6 of the plan).
    Retries a page a few times on transient network errors before giving up -- a single
    flaky request out of ~900+ pages shouldn't kill the whole run."""
    identifiers = set()
    page = 1
    while True:
        for attempt in range(4):
            try:
                r = requests.get(f"{LIVE_API}/bills", params={
                    "jurisdiction": jurisdiction, "session": session,
                    "page": page, "per_page": 20, "apikey": api_key,
                }, timeout=30)
                r.raise_for_status()
                data = r.json()
                break
            except (requests.exceptions.RequestException,) as e:
                if attempt == 3:
                    raise
                wait = 2 ** attempt
                print(f"    ...page {page} failed ({e.__class__.__name__}), "
                      f"retry {attempt + 1}/3 in {wait}s")
                time.sleep(wait)
        identifiers.update(b["identifier"] for b in data["results"])
        max_page = data["pagination"]["max_page"]
        if page % 50 == 0:
            print(f"    ...page {page}/{max_page}, {len(identifiers)} identifiers so far")
        if page >= max_page:
            break
        page += 1
        time.sleep(0.5)
    return identifiers


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


def diff_voters(lv, rv):
    """Diff two paired vote events' per-voter votes[] lists (not just their aggregate
    counts[] tally) -- returns the (voter_name, option) tuples present on only one side
    as (local_only, live_only) sets. Pure/DB-free: this is the decisive check OPEN-26 and
    OPEN-28 both had to do by hand, diffing raw votes[] instead of just counts[]."""
    local_voters = {(v.get("voter_name"), v.get("option")) for v in (lv.get("votes") or [])}
    live_voters = {(v.get("voter_name"), v.get("option")) for v in (rv.get("votes") or [])}
    return local_voters - live_voters, live_voters - local_voters


def describe_voter_diff(local_only, live_only):
    """Format diff_voters()'s output into the specific "who and what" a tally mismatch
    hides behind its aggregate counts -- e.g. "Elizabeth B. Bennett-Parker (yes): local
    only" (the exact OPEN-26 finding). Multiple diffs are joined with "; ". A tally
    mismatch with no per-voter diff at all is itself informative (e.g. the same option
    labeled differently on each side) rather than a silent no-op, so it gets its own
    message instead of an empty string."""
    parts = [f"{name} ({option}): local only" for name, option in sorted(local_only)]
    parts += [f"{name} ({option}): live only" for name, option in sorted(live_only)]
    if not parts:
        return "no per-voter difference found (tally differs for another reason)"
    return "; ".join(parts)


def count_shared_date_signature(conn, jurisdiction_code, session, date, voter_signature,
                                 exclude_identifier, cache=None):
    """Given one bill's mismatched-vote date and its voter-diff signature (the
    (voter_name, option) tuples diff_voters() found), count how many OTHER local bills in
    the same jurisdiction/session share at least one of those same (voter_name, option)
    pairs on that date -- automates the full-corpus scan both OPEN-26 (266 bills) and
    OPEN-28 did by hand. Local-DB-only, matching AC #2's "checks other local bills"
    wording exactly -- costs zero live-API budget, unlike a live re-verification would.
    Reuses the same us/state: jurisdiction split already used by
    fetch_all_local_identifiers()/sample_local_bills_for_session() rather than adding a
    third copy of that branch. `cache`, if supplied, memoizes by
    (jurisdiction_code, session, date, frozenset(voter_signature)) so an identical
    signature repeating across many bills in one run (OPEN-26's was 266) queries once."""
    voter_signature = frozenset(voter_signature)
    if not voter_signature:
        # An empty IN (...) clause is invalid SQL, and an empty signature means the
        # tally differed for a reason other than a voter-presence diff -- nothing to size.
        return 0

    cache_key = (jurisdiction_code, session, date, voter_signature)
    if cache is not None and cache_key in cache:
        return cache[cache_key]

    cur = conn.cursor()
    if jurisdiction_code == "us":
        cur.execute("""
            SELECT COUNT(DISTINCT b.id) FROM opencivicdata_bill b
            JOIN opencivicdata_legislativesession ls ON b.legislative_session_id = ls.id
            JOIN opencivicdata_jurisdiction j ON ls.jurisdiction_id = j.id
            JOIN opencivicdata_voteevent ve ON ve.bill_id = b.id
            JOIN opencivicdata_personvote pv ON pv.vote_event_id = ve.id
            WHERE j.id = 'ocd-jurisdiction/country:us/government' AND ls.identifier = %s
              AND LEFT(ve.start_date, 10) = %s
              AND (pv.voter_name, pv.option) IN %s
              AND b.identifier != %s
        """, (session, date, tuple(voter_signature), exclude_identifier))
    else:
        cur.execute("""
            SELECT COUNT(DISTINCT b.id) FROM opencivicdata_bill b
            JOIN opencivicdata_legislativesession ls ON b.legislative_session_id = ls.id
            JOIN opencivicdata_jurisdiction j ON ls.jurisdiction_id = j.id
            JOIN opencivicdata_voteevent ve ON ve.bill_id = b.id
            JOIN opencivicdata_personvote pv ON pv.vote_event_id = ve.id
            WHERE j.id LIKE %s AND ls.identifier = %s
              AND LEFT(ve.start_date, 10) = %s
              AND (pv.voter_name, pv.option) IN %s
              AND b.identifier != %s
        """, (f"%/state:{jurisdiction_code}/%", session, date, tuple(voter_signature),
              exclude_identifier))

    count = cur.fetchone()[0]
    if cache is not None:
        cache[cache_key] = count
    return count


def compare_bills(report, local, live, label, conn=None, jurisdiction_code=None, session=None,
                   blast_radius_cache=None):
    """Diff local vs live bill on key fields.

    conn/jurisdiction_code/session/blast_radius_cache are optional and additive: when all
    three of conn/jurisdiction_code/session are supplied and a vote-tally mismatch has a
    non-empty per-voter diff, the same-date blast radius is sized via
    count_shared_date_signature() and folded into the existing WARN. Callers that omit
    them (or pass conn=None) get the per-voter diff detail with no blast-radius sizing --
    fully backward compatible with any caller that doesn't pass them.
    """

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
    # local > live is expected for UT/MI (we have fixes not yet merged upstream) and for FL
    # (openstates-scrapers PR #5 / _FLHouseWAFSource: upstream's un-patched scraper loses FL
    # House committee votes ~1hr into any long FL scrape, when flhouse.gov's WAF session
    # cookie expires — confirmed via direct DB + live-API diff 2026-08-05, OPEN-27; upstream
    # contribution: https://github.com/openstates/openstates-scrapers/pull/5751).
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

    # Vote tallies — match same-day votes between local and live before
    # comparing counts. Comparing by list position (local_votes[0] vs
    # live_votes[0]) breaks down whenever the two sides order/paginate a
    # bill's vote events differently, which makes two unrelated roll calls
    # look like a tally mismatch.
    # Normalize to the calendar date (first 10 chars) rather than the full
    # start_date string — both sides return full ISO timestamps in practice,
    # but the two APIs aren't guaranteed to agree on time-of-day/timezone
    # formatting, and "same day" is the granularity that actually matters here.
    def vote_date(v):
        return (v.get("start_date") or "")[:10]

    local_by_date = defaultdict(list)
    for v in local_votes:
        local_by_date[vote_date(v)].append(v)
    live_by_date = defaultdict(list)
    for v in live_votes:
        live_by_date[vote_date(v)].append(v)

    shared_dates = sorted(d for d in local_by_date if d in live_by_date)
    if local_votes and live_votes and not shared_dates:
        report.record(WARN, f"{label}: no shared vote dates to compare tallies against",
                      f"local={sorted(local_by_date)} live={sorted(live_by_date)}")

    def tally(v):
        return {c["option"]: c["value"] for c in (v.get("counts") or [])}

    for date in shared_dates:
        lvs, rvs = list(local_by_date[date]), list(live_by_date[date])

        # A single day can carry more than one vote (companion votes, committee
        # + floor, or a "vote-a-rama" of amendments all dated the same day) --
        # matching same-date votes by list position breaks down exactly the
        # same way full-list position did. motion_text (e.g. "Passed", "do pass
        # amended") identifies the actual roll call and survives reordering
        # even when identifier is blank on both sides, so pair on that first.
        lvs_by_motion = defaultdict(list)
        for v in lvs:
            lvs_by_motion[normalize(v.get("motion_text"))].append(v)
        rvs_by_motion = defaultdict(list)
        for v in rvs:
            rvs_by_motion[normalize(v.get("motion_text"))].append(v)

        pairs = []
        for motion in list(lvs_by_motion):
            if not motion or motion not in rvs_by_motion:
                continue
            lgroup, rgroup = lvs_by_motion.pop(motion), rvs_by_motion.pop(motion)
            pairs.extend(zip(lgroup, rgroup))
            # Uneven counts under the same motion_text fall through to the
            # positional fallback below rather than being silently dropped.
            lvs_by_motion[""].extend(lgroup[len(rgroup):])
            rvs_by_motion[""].extend(rgroup[len(lgroup):])

        # Whatever motion_text couldn't match on both sides (blank, or only
        # present on one side) falls back to positional pairing -- worse than
        # a motion_text match, but still better than dropping the comparison.
        remaining_local = [v for group in lvs_by_motion.values() for v in group]
        remaining_live = [v for group in rvs_by_motion.values() for v in group]
        pairs.extend(zip(remaining_local, remaining_live))

        for lv, rv in pairs:
            lc, rc = tally(lv), tally(rv)
            if lc == rc:
                report.record(PASS, f"{label}: vote tally matches on {date} ({lc})")
            else:
                local_only, live_only = diff_voters(lv, rv)
                detail = f"local={lc} live={rc} | {describe_voter_diff(local_only, live_only)}"
                signature = local_only | live_only
                if signature and conn is not None and jurisdiction_code is not None \
                        and session is not None:
                    shared_count = count_shared_date_signature(
                        conn, jurisdiction_code, session, date, signature,
                        exclude_identifier=local.get("identifier"),
                        cache=blast_radius_cache,
                    )
                    detail += (f" | {shared_count} other local bill(s) share this "
                               f"signature on {date}")
                report.record(WARN, f"{label}: vote tally differs on {date}", detail)
        if len(lvs) != len(rvs):
            report.record(WARN, f"{label}: vote count on {date} differs",
                          f"local={len(lvs)} live={len(rvs)}")

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

# ── Coverage & completeness (PLAN-coverage-completeness-check.md) ─────────────

def run_coverage_check(report, conn, jurisdiction, session, api_key, tier2_limit=None,
                        tier2_random=False, blast_radius_cache=None):
    """
    Tier 1: full identifier-set diff (public vs local) for a jurisdiction+session --
    catches bills we never scraped at all, not just bills that differ once scraped.
    Tier 2: compare_bills() over every identifier present in BOTH sets, reusing the
    existing WARN/FAIL split (local>live votes = our unmerged fix; live>local = real gap).
    """
    if blast_radius_cache is None:
        blast_radius_cache = {}
    print(f"\n{'═'*60}")
    print(f"  COVERAGE CHECK: {jurisdiction.upper()} {session}")
    print(f"{'═'*60}")

    print("  Fetching full identifier set from live API (paginated)...")
    public_ids = fetch_all_public_identifiers(jurisdiction, session, api_key)
    local_ids = fetch_all_local_identifiers(conn, jurisdiction, session)

    missing = public_ids - local_ids   # THE headline number -- bills we don't have at all
    extra = local_ids - public_ids     # informational only, not a failure -- see plan §4
    both = public_ids & local_ids

    # Normalize away docket/bill-number duplication (DOCKET_PREFIX_MAP) before
    # deciding pass/fail -- a no-op for jurisdictions not in that map, so
    # real_missing == missing and docket_duplicate is empty there.
    split = split_missing_by_docket_prefix(missing, jurisdiction)
    real_missing = split["real"]
    docket_duplicate = split["docket_duplicate"]

    print(f"  live={len(public_ids)}  local={len(local_ids)}  "
          f"missing={len(missing)}  extra={len(extra)}  both={len(both)}")
    if docket_duplicate:
        print(f"  ...of which {len(docket_duplicate)} are docket-stage duplicates, "
              f"not a real gap (see PLAN-coverage-completeness-check.md §10) -- "
              f"real gap: {len(real_missing)}")
        print(f"  missing by prefix: {breakdown_by_prefix(missing)}")

    if real_missing:
        report.record(FAIL, f"{jurisdiction.upper()} {session}: Tier 1 coverage — "
                             f"{len(real_missing)} bills exist live but not locally at all")
    else:
        report.record(PASS, f"{jurisdiction.upper()} {session}: Tier 1 coverage — "
                             f"no missing bills ({len(local_ids)} local == {len(public_ids)} live)")
    if docket_duplicate:
        report.record(WARN, f"{jurisdiction.upper()} {session}: {len(docket_duplicate)} "
                             f"docket-stage duplicates in the raw diff, not a real gap "
                             f"(see PLAN-coverage-completeness-check.md §10)")
    if extra:
        report.record(WARN, f"{jurisdiction.upper()} {session}: {len(extra)} bills local-only "
                             f"(not automatically a failure -- see plan §4)")

    # Tier 2: sub-record completeness on every bill present in both sets.
    # tier2_limit caps API usage for a first manual run; omit for a full sweep.
    # tier2_random samples that many bills at random instead of taking the first N
    # (sorted) -- first-N skews toward low-numbered, early-filed bills every time.
    tier2_ids = sorted(both)
    if tier2_limit:
        if tier2_random:
            tier2_ids = sorted(random.sample(tier2_ids, min(tier2_limit, len(tier2_ids))))
        else:
            tier2_ids = tier2_ids[:tier2_limit]
    print(f"  Running Tier 2 sub-record checks on {len(tier2_ids)} of {len(both)} "
          f"bills present in both...")
    for i, identifier in enumerate(tier2_ids):
        label = f"{jurisdiction.upper()} {identifier} ({session})"
        local = fetch_bill(LOCAL_API, LOCAL_KEY, jurisdiction, session, identifier)
        live = fetch_bill(LIVE_API, api_key, jurisdiction, session, identifier)
        compare_bills(report, local, live, label,
                      conn=conn, jurisdiction_code=jurisdiction, session=session,
                      blast_radius_cache=blast_radius_cache)
        if i % 25 == 0:
            print(f"    ...{i}/{len(tier2_ids)}")
        time.sleep(0.5)  # stay under the live API's 2 req/sec limit

    return {
        "live": len(public_ids), "local": len(local_ids),
        "missing": sorted(missing), "extra": sorted(extra),
        "missing_real": sorted(real_missing),
        "missing_docket_duplicate": sorted(docket_duplicate),
        "missing_by_prefix": breakdown_by_prefix(missing),
        "tier2_checked": len(tier2_ids),
    }


def run_tier2_only_check(report, conn, jurisdiction, session, api_key, tier2_limit=None,
                          tier2_random=False, blast_radius_cache=None):
    """Tier 2 sub-record completeness, standalone -- no Tier 1 identifier diff first.
    Samples bills straight from the local DB (sample_local_bills_for_session) instead of
    from Tier 1's public/local overlap, so this never pages through live's full bill list.
    A locally-sampled bill that turns out not to exist live at all still produces a normal
    compare_bills() finding ("missing from live API") rather than being silently excluded --
    that's a real, useful signal here, just not one this mode set out looking for."""
    if blast_radius_cache is None:
        blast_radius_cache = {}

    print(f"\n{'═'*60}")
    print(f"  TIER 2 (standalone): {jurisdiction.upper()} {session}")
    print(f"{'═'*60}")

    tier2_ids = sample_local_bills_for_session(conn, jurisdiction, session,
                                                limit=tier2_limit, random_order=tier2_random)
    print(f"  Checking {len(tier2_ids)} bills sampled directly from the local DB "
          f"({'random' if tier2_random else 'identifier order'})...")
    for i, identifier in enumerate(tier2_ids):
        label = f"{jurisdiction.upper()} {identifier} ({session})"
        local = fetch_bill(LOCAL_API, LOCAL_KEY, jurisdiction, session, identifier)
        live = fetch_bill(LIVE_API, api_key, jurisdiction, session, identifier)
        compare_bills(report, local, live, label,
                      conn=conn, jurisdiction_code=jurisdiction, session=session,
                      blast_radius_cache=blast_radius_cache)
        if i % 25 == 0:
            print(f"    ...{i}/{len(tier2_ids)}")
        time.sleep(0.5)  # stay under the live API's 2 req/sec limit

    return {"tier2_checked": len(tier2_ids)}

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
    parser.add_argument("--coverage", nargs=2, metavar=("JURISDICTION", "SESSION"),
                        help="Run a Tier 1+2 coverage/completeness check instead of the "
                             "default sample-based check (PLAN-coverage-completeness-check.md)")
    parser.add_argument("--tier2", nargs=2, metavar=("JURISDICTION", "SESSION"),
                        help="Run Tier 2 sub-record completeness standalone, with no Tier 1 "
                             "identifier diff first -- samples bills directly from the local "
                             "DB instead of from Tier 1's public/local overlap, so it never "
                             "pages through live's full bill list. Use --coverage instead if "
                             "you also want Tier 1's coverage numbers.")
    parser.add_argument("--tier2-limit", type=int, default=None,
                        help="Cap Tier 2 sub-record checks to N bills (with --coverage: N "
                             "present in both APIs; with --tier2: N sampled from the local DB; "
                             "omit either for a full sweep). Takes the first N in sorted order "
                             "by default -- combine with --tier2-random to randomly sample N "
                             "instead.")
    parser.add_argument("--tier2-random",  action="store_true",
                        help="With --tier2-limit, randomly sample that many bills instead of "
                             "taking the first N in sorted order (only with --coverage or "
                             "--tier2)")
    args = parser.parse_args()

    if not LIVE_KEY:
        print("ERROR: set OPENSTATES_API_KEY to your live v3.openstates.org API key")
        sys.exit(1)

    if args.coverage:
        jurisdiction, session = args.coverage
        os.makedirs("logs/quality-check", exist_ok=True)
        log_path = f"logs/quality-check/{jurisdiction}_{session}.log"
        with open(log_path, "w") as logf:
            tee = Tee(sys.stdout, logf)
            old_stdout, sys.stdout = sys.stdout, tee
            try:
                report = Report()
                conn = psycopg2.connect(DB_URL)
                run_coverage_check(report, conn, jurisdiction, session, LIVE_KEY,
                                   tier2_limit=args.tier2_limit,
                                   tier2_random=args.tier2_random,
                                   blast_radius_cache={})
                conn.close()
                ok = report.summary()
            finally:
                sys.stdout = old_stdout
        print(f"\n  (full output also written to {log_path})")
        sys.exit(0 if ok else 1)

    if args.tier2:
        jurisdiction, session = args.tier2
        os.makedirs("logs/quality-check", exist_ok=True)
        log_path = f"logs/quality-check/{jurisdiction}_{session}_tier2only.log"
        with open(log_path, "w") as logf:
            tee = Tee(sys.stdout, logf)
            old_stdout, sys.stdout = sys.stdout, tee
            try:
                report = Report()
                conn = psycopg2.connect(DB_URL)
                run_tier2_only_check(report, conn, jurisdiction, session, LIVE_KEY,
                                      tier2_limit=args.tier2_limit,
                                      tier2_random=args.tier2_random,
                                      blast_radius_cache={})
                conn.close()
                ok = report.summary()
            finally:
                sys.stdout = old_stdout
        print(f"\n  (full output also written to {log_path})")
        sys.exit(0 if ok else 1)

    jurisdictions = [args.jurisdiction] if args.jurisdiction else JURISDICTIONS
    # Add US if not limiting to a specific jurisdiction
    include_us = not args.jurisdiction or args.jurisdiction == "us"

    report = Report()
    conn = psycopg2.connect(DB_URL)
    blast_radius_cache = {}

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
            compare_bills(report, local, live, label,
                          conn=conn, jurisdiction_code=jcode, session=session,
                          blast_radius_cache=blast_radius_cache)

    if include_us:
        rows = sample_bills_us(conn, args.bills)
        if rows:
            print(f"\n  [US]")
            for identifier, session, jid in rows:
                label = f"US {identifier} ({session})"
                local = fetch_bill(LOCAL_API, LOCAL_KEY, jid, session, identifier)
                live  = fetch_bill(LIVE_API,  LIVE_KEY,  jid, session, identifier)
                compare_bills(report, local, live, label,
                              conn=conn, jurisdiction_code="us", session=session,
                              blast_radius_cache=blast_radius_cache)

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
