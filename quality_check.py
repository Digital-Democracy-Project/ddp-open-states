#!/usr/bin/env python3
"""
Data quality check: samples bills and people from the local openstates DB,
fetches the same records from both local api-v3 (localhost:8002) and the live
v3.openstates.org API, and diffs the key fields.

Designed to stay well within the 250 req/day API rate limit by default.

--coverage (OPEN-289): full Tier 1+2 sweep of every bill in a jurisdiction/session,
sourced from that jurisdiction's govbot-data git clone (https://github.com/chihacknight/
govbot) rather than the live API -- no per-request rate limit, so it isn't capped to a
sample. Falls back automatically to the live-API methodology only when govbot doesn't
have that jurisdiction/session locally synced.

Usage:
    OPENSTATES_API_KEY=<key> python3 quality_check.py
    OPENSTATES_API_KEY=<key> python3 quality_check.py --bills 10 --people 5
    OPENSTATES_API_KEY=<key> python3 quality_check.py --jurisdiction fl
    OPENSTATES_API_KEY=<key> python3 quality_check.py --coverage fl 2026

Environment:
    OPENSTATES_API_KEY   Real API key for v3.openstates.org (required)
    DATABASE_URL         Local openstates DB (default: openstates:openstates_dev@localhost/openstates)
    RESOLVE_RDS_LIVE     Set to "true" to resolve DATABASE_URL from Secrets Manager instead
                         (OPEN-260) -- for pointing this at RDS without relying on a cached
                         RDS_DATABASE_URL, which goes stale every time RDS's own automatic
                         7-day credential rotation fires. Requires RDS_CREDENTIALS_SECRET_ARN
                         to also be set.
    GOVBOT_DATA_DIR      Where --coverage clones/updates govbot-data repos (OPEN-289).
                         Default: ~/.govbot-data
"""

import os
import re
import sys
import json
import time
import random
import argparse
import textwrap
import subprocess
import shutil
import psycopg2
import requests
from collections import defaultdict

# ── Config ────────────────────────────────────────────────────────────────────

LOCAL_API  = "http://localhost:8002"
LIVE_API   = "https://v3.openstates.org"
LOCAL_KEY  = "00000000-0000-0000-0000-000000000001"
LIVE_KEY   = os.environ.get("OPENSTATES_API_KEY", "")


def _resolve_db_url() -> str:
    """Returns the DATABASE_URL this script should use.

    OPEN-260: mirrors openstates-core's own init_django()/_resolve_database_url() -- see that
    docstring for the full incident this fixes. RESOLVE_RDS_LIVE=true opts into resolving the
    current RDS credential from Secrets Manager instead of trusting whatever DATABASE_URL is
    set in this process's environment; off by default, so pointing this script at a local
    Postgres is unaffected.

    pm-review: matches this project's own `os.getenv(X, "false").lower() == "true"` boolean
    convention rather than a bare truthiness check -- RESOLVE_RDS_LIVE=0 or =false must NOT
    enable this, which a plain `if os.environ.get(...)` would have gotten wrong.
    """
    if os.environ.get("RESOLVE_RDS_LIVE", "false").lower() == "true":
        from openstates.utils.rds_credentials import resolve_rds_database_url

        url, error = resolve_rds_database_url()
        if error:
            raise RuntimeError(f"RESOLVE_RDS_LIVE set but could not resolve an RDS credential: {error}")
        return url

    return os.environ.get(
        "DATABASE_URL",
        "postgresql://openstates:openstates_dev@localhost:5433/openstates",
    )


DB_URL = _resolve_db_url()

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


def motion_text_chamber_mismatch(vote):
    """OPEN-67 reproduction, as a single-vote invariant check (not a local-vs-live
    diff): does this vote's own motion_text ("House/ passed 3rd reading", "Senate/
    failed", ...) agree with the chamber it's actually recorded under? Mirrors
    ddp-broker-py's own check exactly -- text starting "house" implies chamber
    "lower", "senate" implies "upper". Returns None for a vote whose motion_text
    doesn't start with either word (not applicable -- not a mismatch, just out of
    scope for this check, e.g. "Governor signed"). Returns True if they agree,
    False if they don't."""
    motion = normalize(vote.get("motion_text"))
    if motion.startswith("house"):
        expected = "lower"
    elif motion.startswith("senate"):
        expected = "upper"
    else:
        return None
    actual = (vote.get("organization") or {}).get("classification")
    return expected == actual


def parse_bill_ids(raw):
    """Split --bill-ids' comma-separated identifier list into a clean, ordered,
    deduplicated list -- e.g. "HB392, HB392,SB189" -> ["HB392", "SB189"]. Blank
    entries (trailing/repeated commas) are dropped rather than becoming a spurious
    empty-string lookup."""
    seen = set()
    result = []
    for part in raw.split(","):
        identifier = part.strip()
        if identifier and identifier not in seen:
            seen.add(identifier)
            result.append(identifier)
    return result

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

# requests builds its exception message from the full request URL, and the API key
# travels as a query parameter -- so every recorded error wrote the live key in
# cleartext into the log. 21 files under logs/quality-check/ already carry it.
# Scrub at the single point where an exception becomes recorded text.
_APIKEY_RE = re.compile(r"(apikey=)[^&\s\]]+", re.I)


def _redact(text):
    """Strip the API key out of anything derived from a request URL."""
    return _APIKEY_RE.sub(r"\1<redacted>", text)


# OPEN-169: transient throttling used to be indistinguishable from a data defect.
# fetch_bill() had no retry, so one HTTP 429 or read timeout became a permanent
# "live API error" FAIL for that bill -- and the bill was never actually compared.
# A full MA 194th run on 2026-08-25 reported 205 failures of which 181 were this,
# i.e. 88% of the "failures" were our own client giving up, while the bills behind
# them went unchecked and were silently counted as neither pass nor fail.
_TRANSIENT_STATUS = frozenset({429, 500, 502, 503, 504})


def _is_transient(exc):
    """True for errors worth retrying: throttling, 5xx, timeouts, connection drops."""
    if isinstance(exc, (requests.exceptions.Timeout,
                        requests.exceptions.ConnectionError)):
        return True
    resp = getattr(exc, "response", None)
    return resp is not None and resp.status_code in _TRANSIENT_STATUS


def _get_with_retry(url, params, timeout=15, attempts=4):
    """GET with exponential backoff on transient failures.

    The wait is `max(exponential_backoff, min(Retry-After, 60))` -- so a Retry-After
    only ever *lengthens* the wait, never shortens it below our own backoff, and one
    oversized header cannot stall a whole run. A Retry-After expressed as an HTTP-date
    is ignored in favour of plain backoff; the live API has only ever sent numeric
    values. Non-transient errors (a 404, a malformed request) raise immediately rather
    than burning three retries on a result that will not change.
    """
    if attempts < 1:
        raise ValueError(f"attempts must be >= 1, got {attempts}")
    for attempt in range(attempts):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            r.raise_for_status()
            return r
        except Exception as e:
            if attempt == attempts - 1 or not _is_transient(e):
                raise
            wait = 2 ** attempt
            resp = getattr(e, "response", None)
            if resp is not None:
                try:
                    wait = max(wait, min(float(resp.headers.get("Retry-After", 0)), 60))
                except (TypeError, ValueError):
                    pass
            time.sleep(wait)


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
        r = _get_with_retry(f"{base_url}/bills", params)
        results = r.json().get("results", [])
        return results[0] if results else None
    except Exception as e:
        return {"_error": _redact(str(e))}


def fetch_person(base_url, api_key, person_id):
    """Fetch a person record."""
    params = {"id": person_id, "apikey": api_key}
    try:
        r = _get_with_retry(f"{base_url}/people", params)
        results = r.json().get("results", [])
        return results[0] if results else None
    except Exception as e:
        return {"_error": _redact(str(e))}

# ── Govbot-backed comparison (OPEN-289) ────────────────────────────────────────
#
# govbot (https://github.com/chihacknight/govbot) publishes one git repo per
# jurisdiction (govbot-data/<slug>-legislation) built by running the real upstream
# openstates/scrapers image on its own CI schedule -- no API, no rate limit, just a
# `git clone`. Verified directly against a real bill (FL SR 1402, 2026) before this
# was built: title, latest action/date, sponsor, and full action sequence all matched
# the live v3.openstates.org API exactly. Because govbot and the live API both run
# essentially the same *unforked* upstream scraper logic (unlike DDP's own fork,
# which carries jurisdiction-specific patches), they track each other closely --
# govbot is a credible, verified-in-practice proxy for "what would the live API say,"
# not just a theoretical one.
#
# Ramon's decision (OPEN-289): govbot is the PRIMARY comparison source for
# --coverage, not a parallel/alongside check. The live-API methodology above
# (fetch_all_public_identifiers/fetch_bill) becomes the fallback, used only when a
# jurisdiction's govbot repo can't be cloned/updated, or doesn't have the requested
# session yet -- never as a standing second check run alongside govbot.

GOVBOT_DATA_DIR = os.environ.get("GOVBOT_DATA_DIR", os.path.expanduser("~/.govbot-data"))

# govbot's federal repo is govbot-data/usa-legislation, not govbot-data/us-legislation --
# confirmed directly (git ls-remote) before writing this, since an earlier investigation
# had assumed "us" and gotten a 404. Every other jurisdiction code in this file maps to
# an identically-named govbot repo, so this map only needs the one exception.
GOVBOT_REPO_SLUG = {"us": "usa"}


def _govbot_slug(jurisdiction_code):
    return GOVBOT_REPO_SLUG.get(jurisdiction_code, jurisdiction_code)


def _govbot_repo_path(jurisdiction_code):
    return os.path.join(GOVBOT_DATA_DIR, f"{_govbot_slug(jurisdiction_code)}-legislation")


def _run_git(args, cwd=None, timeout=300):
    """subprocess.run wrapper for the git calls below -- never raises, always returns
    a (ok, stdout_or_stderr) pair, so a clone/fetch failure becomes a normal fallback
    decision rather than an uncaught exception aborting the whole coverage check."""
    try:
        result = subprocess.run(
            ["git", *args], cwd=cwd, timeout=timeout,
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            return False, (result.stderr or result.stdout).strip()[:300]
        return True, result.stdout.strip()
    except (subprocess.TimeoutExpired, OSError) as e:
        return False, f"{e.__class__.__name__}: {e}"


def _ensure_govbot_repo(jurisdiction_code):
    """Clone this jurisdiction's govbot-data repo if we don't have it locally yet, or
    update it (shallow fetch + hard reset to origin/main) if we do. Never raises --
    every failure mode (repo doesn't exist upstream, network error, clone timeout)
    comes back as (False, <reason>) so the caller can fall back to the live API
    cleanly, matching every other never-raise contract in this file.

    Returns (ok, repo_path_or_None, detail) -- detail is a short human-readable string
    for the "which source was used" signal OPEN-289 requires either way: on success,
    what got synced; on failure, why.
    """
    repo_path = _govbot_repo_path(jurisdiction_code)
    repo_url = f"https://github.com/govbot-data/{_govbot_slug(jurisdiction_code)}-legislation.git"

    if not os.path.isdir(os.path.join(repo_path, ".git")):
        try:
            os.makedirs(GOVBOT_DATA_DIR, exist_ok=True)
        except OSError as e:
            return False, None, f"could not create {GOVBOT_DATA_DIR!r}: {e}"
        ok, detail = _run_git(["clone", "--depth", "1", repo_url, repo_path])
        if not ok:
            # pm-review: an interrupted/partial clone leaves a directory behind
            # with no usable .git -- left alone, every future run would see
            # "not a fresh clone" (no .git dir yet, so this same branch), retry
            # the clone into a non-empty directory, and fail again forever.
            # Clearing it here is what makes the next run's clone attempt a
            # real retry instead of a permanent, self-inflicted failure.
            shutil.rmtree(repo_path, ignore_errors=True)
            return False, None, f"clone failed: {detail}"
    else:
        ok, detail = _run_git(["fetch", "--depth", "1", "origin", "main"], cwd=repo_path)
        if not ok:
            return False, None, f"update failed: {detail}"
        ok, detail = _run_git(["reset", "--hard", "origin/main"], cwd=repo_path)
        if not ok:
            return False, None, f"update failed (reset): {detail}"

    ok, sha = _run_git(["rev-parse", "--short", "HEAD"], cwd=repo_path)
    return True, repo_path, f"synced main @ {sha if ok else '?'}"


def _govbot_session_dir(jurisdiction_code, session, repo_path):
    return os.path.join(repo_path, "country:us", f"state:{_govbot_slug(jurisdiction_code)}",
                        "sessions", session)


def _parse_govbot_ref(raw):
    """govbot encodes entity references (a vote_event's own `organization` field,
    `organization_id`, `person_id`, `from_organization`) as a string prefixed with
    `~` followed by a JSON object -- e.g. `'~{"classification": "upper"}'` -- rather
    than the nested dict api-v3 returns for the same information. Returns {} for
    None/non-string/malformed input instead of raising; this file only ever reads
    `.get("classification")` off the result, which degrades to None either way."""
    if not isinstance(raw, str) or not raw.startswith("~"):
        return {}
    try:
        parsed = json.loads(raw[1:])
    except (json.JSONDecodeError, ValueError):
        return {}
    # pm-review: valid JSON that isn't itself an object (e.g. "~[]", "~\"x\"", "~null")
    # would otherwise pass through as-is and break every caller's .get(...) -- every
    # real govbot reference is an object, so anything else is treated the same as
    # malformed input.
    return parsed if isinstance(parsed, dict) else {}


def _govbot_latest_action_description(actions):
    """The live API's own `latest_action_description` is a precomputed field;
    govbot's metadata.json only has the full `actions` list. Sorts by date rather
    than trusting array order -- govbot's own actions do appear chronological in
    practice, but nothing in the schema guarantees it, and getting this wrong would
    silently corrupt the one field compare_bills() diffs most often."""
    if not actions:
        return ""
    return max(actions, key=lambda a: a.get("date") or "").get("description") or ""


def _load_govbot_vote_events(bill_dir):
    """Read every `*.vote_event.*.json` log file for one bill, reshaping each into
    the same {start_date, motion_text, organization: {classification}, counts,
    votes} shape compare_bills() already expects from a live api-v3 bill's own
    votes[] (see fetch_bill()'s include=votes). Most bills never get a roll call and
    simply have no matching log files -- an empty list here, not an error."""
    logs_dir = os.path.join(bill_dir, "logs")
    events = []
    if not os.path.isdir(logs_dir):
        return events
    try:
        fnames = os.listdir(logs_dir)
    except OSError:
        # pm-review: a permissions error or a directory that disappears mid-run
        # (concurrent govbot update) must degrade to "no votes found for this
        # bill," the same as no logs/ dir at all -- not crash the whole check.
        return events
    for fname in fnames:
        if ".vote_event." not in fname:
            continue
        try:
            with open(os.path.join(logs_dir, fname)) as f:
                raw = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        events.append({
            "start_date": raw.get("start_date") or "",
            "motion_text": raw.get("motion_text") or "",
            "organization": _parse_govbot_ref(raw.get("organization")),
            "counts": raw.get("counts") or [],
            "votes": [
                {"voter_name": v.get("voter_name"), "option": v.get("option")}
                for v in (raw.get("votes") or [])
            ],
        })
    return events


def _load_govbot_bill(bill_dir):
    """Read one govbot bill directory (metadata.json + logs/*.vote_event.*.json)
    into the same shape compare_bills() expects from a live api-v3 bill response --
    identifier, title, latest_action_description, votes[], sponsorships[]. govbot's
    own sponsorships already carry the same name/classification/entity_type/primary
    fields api-v3 does, so no reshaping is needed there. Returns None if
    metadata.json is missing or unreadable, matching fetch_bill()'s own
    None-on-not-found contract."""
    try:
        with open(os.path.join(bill_dir, "metadata.json")) as f:
            meta = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    return {
        "identifier": meta.get("identifier"),
        "title": meta.get("title") or "",
        "latest_action_description": _govbot_latest_action_description(meta.get("actions")),
        "votes": _load_govbot_vote_events(bill_dir),
        "sponsorships": meta.get("sponsorships") or [],
    }


def _normalize_bill_identifier(identifier):
    """govbot's metadata.json `identifier` field zero-pads the bill number for some
    jurisdictions (e.g. MI: "SB 0001"), while DDP's local DB/api-v3 use OpenStates'
    own unpadded convention ("SB 1") -- confirmed 2026-09-14 against MI, where this
    alone accounted for 1503 of 1590 "missing" Tier 1 bills (every one of them
    actually present locally, just under the unpadded key). Strip the padding so
    both sides compare on the same format. Anything that doesn't match a simple
    PREFIX-space-digits shape is returned unchanged rather than risk mangling an
    identifier format we don't recognize."""
    match = re.match(r"^([A-Z]+)\s*0*(\d+)$", identifier)
    if match:
        return f"{match.group(1)} {match.group(2)}"
    return identifier


def build_govbot_bill_index(jurisdiction_code, session, repo_path):
    """One pass over a govbot session's bills/ directory, keyed by each bill's own
    metadata.json `identifier` field -- NOT the directory name, which strips spaces
    (a real bill directory is "SB60", but its own identifier field is "SB 60") and
    can't be trusted to reconstruct that format for every jurisdiction. The key is
    run through _normalize_bill_identifier() first since govbot's own identifier
    field isn't always DDP's local format either (see that function's docstring).
    Shared by both the Tier 1 identifier-set diff and Tier 2's per-bill lookups
    below, so a govbot-backed coverage check reads each bill's files exactly once
    regardless of how many times it's referenced."""
    bills_dir = os.path.join(_govbot_session_dir(jurisdiction_code, session, repo_path), "bills")
    index = {}
    if not os.path.isdir(bills_dir):
        return index
    try:
        names = os.listdir(bills_dir)
    except OSError:
        # pm-review: same reasoning as _load_govbot_vote_events -- an unreadable
        # bills/ dir must degrade to "no bills found," which
        # run_coverage_check_with_fallback() already treats as "govbot isn't
        # usable here, fall back to the live API," not a crash.
        return index
    for name in names:
        bill_dir = os.path.join(bills_dir, name)
        if not os.path.isdir(bill_dir):
            continue
        bill = _load_govbot_bill(bill_dir)
        if bill and bill.get("identifier"):
            index[_normalize_bill_identifier(bill["identifier"])] = bill
    return index


def run_govbot_coverage_check(report, conn, jurisdiction, session, govbot_index, tier2_limit=None,
                               tier2_random=False, blast_radius_cache=None):
    """govbot-backed equivalent of run_coverage_check() below -- same Tier 1 (full
    identifier-set diff) + Tier 2 (compare_bills() over every shared identifier)
    shape and the same return-dict keys, but sourcing "live" data from a local
    govbot-data clone's files instead of paginating the live API. No per-request
    sleep: reading local files has no rate limit to respect, which is the whole
    point of OPEN-289 -- a full sweep of every bill, not a capped sample, and
    faster in wall-clock time too.

    Takes an already-built govbot_index (pm-review, OPEN-289) rather than a
    repo_path -- run_coverage_check_with_fallback() below has to build the index
    first anyway, to tell a real (if small) session apart from an empty/unreadable
    one before deciding whether govbot is even usable. Building it twice would
    silently double the disk I/O for no benefit.
    """
    if blast_radius_cache is None:
        blast_radius_cache = {}
    print(f"\n{'═'*60}")
    print(f"  COVERAGE CHECK: {jurisdiction.upper()} {session}  (source: govbot)")
    print(f"{'═'*60}")

    public_ids = set(govbot_index)
    local_ids = fetch_all_local_identifiers(conn, jurisdiction, session)

    missing = public_ids - local_ids
    extra = local_ids - public_ids
    both = public_ids & local_ids

    split = split_missing_by_docket_prefix(missing, jurisdiction)
    real_missing = split["real"]
    docket_duplicate = split["docket_duplicate"]

    print(f"  govbot={len(public_ids)}  local={len(local_ids)}  "
          f"missing={len(missing)}  extra={len(extra)}  both={len(both)}")
    if docket_duplicate:
        print(f"  ...of which {len(docket_duplicate)} are docket-stage duplicates, "
              f"not a real gap (see PLAN-coverage-completeness-check.md §10) -- "
              f"real gap: {len(real_missing)}")
        print(f"  missing by prefix: {breakdown_by_prefix(missing)}")

    if real_missing:
        report.record(FAIL, f"{jurisdiction.upper()} {session}: Tier 1 coverage (govbot) — "
                             f"{len(real_missing)} bills exist in govbot but not locally at all")
    else:
        report.record(PASS, f"{jurisdiction.upper()} {session}: Tier 1 coverage (govbot) — "
                             f"no missing bills ({len(local_ids)} local == {len(public_ids)} govbot)")
    if docket_duplicate:
        report.record(WARN, f"{jurisdiction.upper()} {session}: {len(docket_duplicate)} "
                             f"docket-stage duplicates in the raw diff, not a real gap "
                             f"(see PLAN-coverage-completeness-check.md §10)")
    if extra:
        report.record(WARN, f"{jurisdiction.upper()} {session}: {len(extra)} bills local-only "
                             f"(not automatically a failure -- see plan §4)")

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
        live = govbot_index.get(identifier)
        compare_bills(report, local, live, label,
                      conn=conn, jurisdiction_code=jurisdiction, session=session,
                      blast_radius_cache=blast_radius_cache)
        if i % 250 == 0:
            print(f"    ...{i}/{len(tier2_ids)}")

    return {
        "govbot": len(public_ids), "local": len(local_ids),
        "missing": sorted(missing), "extra": sorted(extra),
        "missing_real": sorted(real_missing),
        "missing_docket_duplicate": sorted(docket_duplicate),
        "missing_by_prefix": breakdown_by_prefix(missing),
        "tier2_checked": len(tier2_ids),
    }


def run_coverage_check_with_fallback(report, conn, jurisdiction, session, api_key,
                                      tier2_limit=None, tier2_random=False,
                                      blast_radius_cache=None):
    """OPEN-289: the real entry point --coverage now uses. Tries govbot first
    (clone/update this jurisdiction's govbot-data repo); only falls back to the
    existing live-API methodology (run_coverage_check(), unchanged) when that repo
    can't be synced at all, or doesn't have the requested session yet -- covers both
    a git failure and a jurisdiction govbot simply doesn't publish, the same
    fallback path either way. Always prints and returns which source actually
    backed the result (OPEN-289 item 4) -- a reader must never have to guess which
    methodology a given pass/fail came from.

    pm-review: an existing-but-EMPTY bills/ directory (govbot mid-sync, a
    permissions problem, every metadata.json unreadable) used to pass the old
    os.path.isdir(bills_dir) check and go straight to run_govbot_coverage_check()
    with zero real bills indexed -- Tier 1's own diff logic (missing = public_ids
    - local_ids) then finds nothing "missing" against an empty public_ids and
    reports a clean PASS, which is worse than useless: a real gap would be
    silently invisible. The index is built here, once, specifically so "govbot
    has any bills to compare against at all" can gate the fallback decision
    before Tier 1 ever runs, not just "the directory exists."
    """
    ok, repo_path, detail = _ensure_govbot_repo(jurisdiction)
    if ok:
        govbot_index = build_govbot_bill_index(jurisdiction, session, repo_path)
        if govbot_index:
            print(f"  Source: govbot (govbot-data/{_govbot_slug(jurisdiction)}-legislation, {detail})")
            result = run_govbot_coverage_check(
                report, conn, jurisdiction, session, govbot_index,
                tier2_limit=tier2_limit, tier2_random=tier2_random,
                blast_radius_cache=blast_radius_cache,
            )
            result["source"] = "govbot"
            return result
        detail = f"repo synced but has no readable bill data for {session!r} yet"

    print(f"  Source: live API (fallback — {detail})")
    result = run_coverage_check(report, conn, jurisdiction, session, api_key,
                                 tier2_limit=tier2_limit, tier2_random=tier2_random,
                                 blast_radius_cache=blast_radius_cache)
    result["source"] = "live_api_fallback"
    result["source_fallback_reason"] = detail
    return result

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

    # OPEN-169: compare vote events that actually carry a vote, not raw list length.
    # The live API returns placeholder vote events with no counts and no per-voter
    # rows -- an event that records only that a vote happened, with none of its
    # content. Counting those made us look behind on data we in fact hold: across
    # the six MA bills this check reported as "missing Senate votes", ALL 14 of
    # live's extra events were empty, and we held the real roll calls. That is a
    # defect in the comparison, not a gap in the data, and it made a clean MA run
    # impossible -- the gate could never be met however good the scraper got.
    #
    # Deliberately not filtering the LOCAL side by the same rule. An empty event on
    # our side is a real defect worth surfacing (see the MA House votes that
    # imported with correct tallies and zero voters), and the tally comparison below
    # is what catches it. Here we only stop crediting live for content it does not
    # have.
    def _carries_a_vote(v):
        return bool(v.get("counts")) or bool(v.get("votes"))

    live_substantive = [v for v in live_votes if _carries_a_vote(v)]
    live_empty = len(live_votes) - len(live_substantive)

    lv_count, rv_count = len(local_votes), len(live_substantive)
    if lv_count == rv_count:
        msg = f"{label}: vote event count matches ({lv_count})"
        if live_empty:
            msg += f" — ignoring {live_empty} empty live event(s)"
        report.record(PASS, msg)
    elif lv_count > rv_count:
        # We have more votes than upstream — likely our scraper fix is better
        report.record(WARN, f"{label}: local has MORE votes than live (our fix not merged?)",
                      f"local={lv_count} live={rv_count}"
                      + (f" (+{live_empty} empty live event(s) ignored)" if live_empty else ""))
    else:
        # Live has more real votes than us — we're behind
        report.record(FAIL, f"{label}: local is MISSING votes vs live",
                      f"local={lv_count} live={rv_count}"
                      + (f" (+{live_empty} empty live event(s) ignored)" if live_empty else ""))

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

    # OPEN-169: pair on (date, CHAMBER), not date alone. Both chambers routinely
    # vote on the same bill on the same day, with near-identical motion text --
    # "Enacted", "Passed to be engrossed" -- so a date-only key happily compares a
    # Senate roll call against a House one and reports a 40-vs-148 "tally mismatch"
    # that is really two different votes.
    #
    # This was latent rather than new. It could not fire while MA held only Senate
    # votes: there was nothing on our side for a live House vote to be mispaired
    # with. Backfilling the House roll calls is what exposed it, and it accounted
    # for the bulk of the warnings on the first clean run.
    #
    # organization.classification ("lower"/"upper") is the authoritative field --
    # the same one that settled which chamber was actually missing. Falls back to
    # the empty string so a record without it still groups consistently on both
    # sides rather than silently dropping out of the comparison.
    def vote_chamber(v):
        return ((v.get("organization") or {}).get("classification") or "")

    def vote_key(v):
        return (vote_date(v), vote_chamber(v))

    local_by_date = defaultdict(list)
    for v in local_votes:
        local_by_date[vote_key(v)].append(v)
    # Pair against live's *substantive* events for the same reason the count
    # comparison above ignores them: an event with no counts and no voters has
    # nothing to compare a tally against. Left unfiltered, every live placeholder
    # produced two warnings that could never be acted on -- a "vote tally differs
    # ... live={}" against an empty dict, and a "vote count differs" for the
    # event-count gap the check had just decided to forgive. On MA that is not a
    # rounding error: live carries an empty `upper` placeholder on most of these
    # bills, and those warnings are the ones the readiness recommendation gets
    # read against.
    #
    # The local side stays unfiltered here, exactly as above -- an empty event of
    # ours is a real defect and this loop is what surfaces it, as a tally of {}
    # against live's real counts.
    live_by_date = defaultdict(list)
    for v in live_substantive:
        live_by_date[vote_key(v)].append(v)

    shared_dates = sorted(d for d in local_by_date if d in live_by_date)
    if local_votes and live_substantive and not shared_dates:
        report.record(WARN, f"{label}: no shared vote date+chamber to compare tallies against",
                      f"local={sorted('/'.join(k) for k in local_by_date)} "
                      f"live={sorted('/'.join(k) for k in live_by_date)}")

    def tally(v):
        return {c["option"]: c["value"] for c in (v.get("counts") or [])}

    for key in shared_dates:
        lvs, rvs = list(local_by_date[key]), list(live_by_date[key])
        # Unpack rather than carrying the tuple further: `date` stays a plain
        # date string, which is what count_shared_date_signature()'s SQL binds,
        # and the chamber only decorates the message. Keeping the tuple here
        # silently passed a record into `LEFT(ve.start_date, 10) = %s`.
        date, chamber = key
        where = f"{date}/{chamber}" if chamber else date

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
                report.record(PASS, f"{label}: vote tally matches on {where} ({lc})")
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
                               f"signature on {where}")
                report.record(WARN, f"{label}: vote tally differs on {where}", detail)
        if len(lvs) != len(rvs):
            report.record(WARN, f"{label}: vote count on {where} differs",
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


def run_bill_ids_check(report, conn, jurisdiction, session, identifiers, api_key,
                        blast_radius_cache=None):
    """Local-vs-live compare_bills() for an explicit, caller-supplied list of bill
    identifiers (OPEN-67) -- e.g. spot-checking specific bills a downstream consumer
    flagged, rather than Tier 2's random/sorted sample of everything in a session.
    Only ever proves CURRENT correctness: the local DB only has data from whenever
    this jurisdiction was first scraped here (confirmed for UT: 2026-06-14 onward),
    so this can't reconstruct a historical bug window that predates local coverage --
    it's a snapshot check, not a time-travel diff."""
    if blast_radius_cache is None:
        blast_radius_cache = {}

    print(f"\n{'═'*60}")
    print(f"  BILL-IDS CHECK: {jurisdiction.upper()} {session} ({len(identifiers)} bills)")
    print(f"{'═'*60}")

    for identifier in identifiers:
        label = f"{jurisdiction.upper()} {identifier} ({session})"
        local = fetch_bill(LOCAL_API, LOCAL_KEY, jurisdiction, session, identifier)
        live = fetch_bill(LIVE_API, api_key, jurisdiction, session, identifier)
        compare_bills(report, local, live, label,
                      conn=conn, jurisdiction_code=jurisdiction, session=session,
                      blast_radius_cache=blast_radius_cache)

        # OPEN-67: compare_bills() above only diffs local vs live -- it never checks
        # whether a vote's own motion_text agrees with the chamber it's recorded
        # under. Run that invariant check against both sources independently.
        for source_label, source in ((f"{label} local", local), (f"{label} live", live)):
            if not source or "_error" in source:
                continue
            for vote in (source.get("votes") or []):
                verdict = motion_text_chamber_mismatch(vote)
                if verdict is None:
                    continue
                motion = vote.get("motion_text")
                if verdict:
                    report.record(PASS, f"{source_label}: chamber matches motion text "
                                         f"({motion!r})")
                else:
                    chamber = (vote.get("organization") or {}).get("classification")
                    report.record(FAIL, f"{source_label}: chamber SWAPPED vs motion text",
                                  f"motion_text={motion!r} recorded_chamber={chamber!r}")

        time.sleep(0.5)  # stay under the live API's 2 req/sec limit

    return {"checked": len(identifiers)}

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
                             "default sample-based check (PLAN-coverage-completeness-check.md). "
                             "OPEN-289: sources every bill from that jurisdiction's govbot-data "
                             "git clone by default (cloned/updated automatically to "
                             "$GOVBOT_DATA_DIR, no live-API rate limit) -- falls back to the "
                             "live API's own 250-bill-style sample only if govbot doesn't have "
                             "that jurisdiction/session available.")
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
    parser.add_argument("--bill-ids", nargs=3, metavar=("JURISDICTION", "SESSION", "IDS"),
                        help="Local-vs-live compare_bills() for an explicit comma-separated "
                             "list of bill identifiers instead of a sample, e.g. "
                             "--bill-ids ut 2026 'HB392,HB223,SB189'. Only proves current "
                             "correctness -- can't reconstruct a bug window that predates "
                             "this jurisdiction's local scrape history.")
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
                coverage_result = run_coverage_check_with_fallback(
                    report, conn, jurisdiction, session, LIVE_KEY,
                    tier2_limit=args.tier2_limit,
                    tier2_random=args.tier2_random,
                    blast_radius_cache={})
                conn.close()
                ok = report.summary()
                print(f"  source: {coverage_result['source']}"
                      + (f" ({coverage_result['source_fallback_reason']})"
                         if coverage_result.get("source_fallback_reason") else ""))
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

    if args.bill_ids:
        jurisdiction, session, raw_ids = args.bill_ids
        identifiers = parse_bill_ids(raw_ids)
        os.makedirs("logs/quality-check", exist_ok=True)
        log_path = f"logs/quality-check/{jurisdiction}_{session}_bill-ids.log"
        with open(log_path, "w") as logf:
            tee = Tee(sys.stdout, logf)
            old_stdout, sys.stdout = sys.stdout, tee
            try:
                report = Report()
                conn = psycopg2.connect(DB_URL)
                run_bill_ids_check(report, conn, jurisdiction, session, identifiers, LIVE_KEY,
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
