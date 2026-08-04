#!/usr/bin/env python3
"""
Grab a small, fixed number of real Michigan bills via a live scrape -- for manual
testing (e.g. verifying ScrapeBot's cookie/User-Agent handoff end-to-end, or any
other MI WAF-pipeline change) without waiting for a full MI session scrape
(1000+ bills, hours).

Must be run with this checkout's ISOLATED dev environment active (source
activate-dev.sh first, or use the test-mi-scrape-sample.sh wrapper) -- never
activate.sh, which is production's. This writes real scraped JSON to
SCRAPED_DATA_DIR and reads/writes the real MI_COOKIE_PROVIDER cache at
CACHE_DIR, both of which resolve to this dev checkout's own isolated
openstates-scrapers/_data and _cache when activate-dev.sh is active, never
production's.

Scrape-only -- never runs the --import step, so it never touches Postgres
(dev or prod). Everything downstream of the real scrape() generator (the WAF
cookie pipeline in mi_waf_get()/MI_COOKIE_PROVIDER, save_object(), validation,
JSON serialization) runs completely unmodified; this script only caps how many
items get pulled from that generator.

--mint-via-scrapebot (added for ddp-agents' PLAN-scrapebot.md Phase 4 live
validation): before scraping, dispatch a real mint_scrape_cookies task to
ScrapeBot via CAMS's task API, then seed this checkout's own
MI_COOKIE_PROVIDER cache from the real result -- the exact same on-disk JSON
shape ddp-sync's scrapebot_client.write_cookie_cache() writes for production,
just targeting this dev checkout's isolated cache path instead. This is how
to actually prove ScrapeBot's currently-configured backend (Claude Opus 4.8
by default, or the local MLX-VLM daemon once SCRAPEBOT_BROWSER_ANTHROPIC_
BASE_URL/SCRAPEBOT_BROWSER_MODEL are set) produces cookies real
openstates-scrapers code can use, instead of relying on CookieProvider's own
plain self-warm (which never touches ScrapeBot at all). Requires a running
CAMS reachable at CAMS_BASE_URL, with CAMS_API_TOKEN and CAMS_ARTIFACTS_DIR
(pointed at that CAMS instance's own artifacts/ dir, so task_result.json can
be read directly off disk) set in the environment. Omit the flag to fall
back to the script's original behavior (whatever's already cached, or
CookieProvider's own self-warm).

Usage:
    source activate-dev.sh && python3 test-mi-scrape-sample.py [--count N] [--session SESSION] [--mint-via-scrapebot]

    or simply:
    ./test-mi-scrape-sample.sh [--count N] [--session SESSION] [--mint-via-scrapebot]

Exit codes: 0 = success; 1 = wrong environment (see guard below); 2 = WAF
block (both the cached-cookie attempt and the one re-warm failed); 3 = the
--mint-via-scrapebot dispatch itself failed (bad response, timeout, or a
task_result.json missing cookies/user_agent).
"""
import argparse
import itertools
import json
import os
import sys
import time

# Matches ddp-sync's scrapebot_client.py _DEFAULT_TIMEOUT_SECONDS exactly --
# a single page load + a possible CAPTCHA attempt, not a guess independent
# of that module's own PM-reviewed value.
_DEFAULT_MINT_TIMEOUT_SECONDS = 90.0
_MINT_POLL_INTERVAL_SECONDS = 5
_MINT_TERMINAL_STATUSES = ("completed", "failed", "cancelled")
# CookieProvider's own session-cookie TTL fallback (cookie_provider.py's
# _DEFAULT_SESSION_COOKIE_TTL_SECONDS) -- matched here exactly, not guessed,
# same as ddp-sync's write_cookie_cache() does for the production path.
_SESSION_COOKIE_TTL_SECONDS = 3600


class ScrapeBotDispatchError(Exception):
    """Raised when dispatching mint_scrape_cookies via CAMS fails to produce
    a usable cookie/user-agent pair. Mirrors ddp-sync's
    scrapebot_client.ScrapeBotDispatchError in shape/intent -- that module
    lives in a different repo/venv (ddp-sync), so this is a small
    self-contained copy for this script, not a cross-repo import."""


def dispatch_mint_cookies(jurisdiction, *, timeout_seconds=_DEFAULT_MINT_TIMEOUT_SECONDS):
    """Dispatch a real mint_scrape_cookies task to ScrapeBot via CAMS's task
    API and return {"cookies": [...], "user_agent": "..."}, read from
    task_result.json -- same dispatch/poll/read shape as ddp-sync's
    scrapebot_client.dispatch_mint_cookies()."""
    import requests

    cams_base_url = os.environ.get("CAMS_BASE_URL", "http://localhost:8000")
    cams_api_token = os.environ.get("CAMS_API_TOKEN", "changeme")
    cams_artifacts_dir = os.environ.get("CAMS_ARTIFACTS_DIR", "")
    if not cams_artifacts_dir:
        raise ScrapeBotDispatchError(
            "CAMS_ARTIFACTS_DIR is not set -- cannot read ScrapeBot's task_result.json. "
            "Point it at the CAMS instance's own artifacts/ directory (e.g. "
            "~/Developer/repos/ddp-agents-dev/artifacts)."
        )

    headers = {"Authorization": f"Bearer {cams_api_token}"}
    resp = requests.post(
        f"{cams_base_url}/api/v1/tasks",
        headers=headers,
        json={
            "bot": "scrapebot",
            "task_type": "mint_scrape_cookies",
            "payload": {"jurisdiction": jurisdiction},
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    task_id = resp.json()["task_id"]
    print(f"ScrapeBot task dispatched: {task_id} (jurisdiction={jurisdiction})")

    status = "queued"
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        status_resp = requests.get(
            f"{cams_base_url}/api/v1/tasks/{task_id}", headers=headers, timeout=30.0
        )
        status_resp.raise_for_status()
        status = status_resp.json()["status"]
        if status in _MINT_TERMINAL_STATUSES:
            break
        time.sleep(_MINT_POLL_INTERVAL_SECONDS)
    else:
        raise ScrapeBotDispatchError(
            f"ScrapeBot task {task_id} did not finish within {timeout_seconds}s "
            f"(last status: {status})"
        )

    if status != "completed":
        raise ScrapeBotDispatchError(f"ScrapeBot task {task_id} ended with status={status}")

    result_path = os.path.join(cams_artifacts_dir, task_id, "task_result.json")
    try:
        with open(result_path) as f:
            snapshot = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise ScrapeBotDispatchError(f"Could not read {result_path}: {exc}") from exc

    cookies, user_agent = snapshot.get("cookies"), snapshot.get("user_agent")
    if not cookies or not user_agent:
        raise ScrapeBotDispatchError(
            f"task_result.json for {task_id} is missing cookies/user_agent "
            f"(got cookies={cookies!r}, user_agent={user_agent!r})"
        )

    print(f"ScrapeBot task completed: {len(cookies)} cookies minted")
    return {"cookies": cookies, "user_agent": user_agent}


def write_cookie_cache(cache_path, cookies, user_agent):
    """Seed MI_COOKIE_PROVIDER's on-disk cache from a ScrapeBot dispatch
    result. Byte-format matches CookieProvider._warm_up_and_cache() exactly
    -- the same shape ddp-sync's write_cookie_cache() writes for production,
    just targeting this dev checkout's own isolated cache path (never
    production's)."""
    now = time.time()
    data = {}
    for c in cookies:
        expires = c.get("expires") or 0
        if expires <= 0:
            expires = now + _SESSION_COOKIE_TTL_SECONDS
        data[c["name"]] = {"value": c["value"], "expires": expires}
    data["_meta"] = {"user_agent": user_agent}

    os.makedirs(os.path.dirname(cache_path) or ".", exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(data, f)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--count", type=int, default=12, help="number of bills to scrape (default: 12)"
    )
    parser.add_argument(
        "--session", default="2025-2026", help="MI legislative session (default: 2025-2026)"
    )
    parser.add_argument(
        "--mint-via-scrapebot",
        action="store_true",
        help="dispatch a real mint_scrape_cookies task to ScrapeBot via CAMS and seed "
        "this checkout's cookie cache from the result before scraping, instead of "
        "relying on whatever's already cached / CookieProvider's own self-warm",
    )
    parser.add_argument(
        "--mint-timeout",
        type=float,
        default=_DEFAULT_MINT_TIMEOUT_SECONDS,
        help=f"seconds to wait for the ScrapeBot dispatch to complete "
        f"(default: {_DEFAULT_MINT_TIMEOUT_SECONDS})",
    )
    args = parser.parse_args()

    scraped_data_dir = os.environ.get("SCRAPED_DATA_DIR", "")
    cache_dir = os.environ.get("CACHE_DIR", "")
    if "ddp-open-states-dev" not in scraped_data_dir or "ddp-open-states-dev" not in cache_dir:
        print(
            "ERROR: this doesn't look like the dev environment (SCRAPED_DATA_DIR/CACHE_DIR "
            "aren't under ddp-open-states-dev). Source activate-dev.sh first -- never "
            "activate.sh, which is production's and would write into its real _data/_cache.",
            file=sys.stderr,
        )
        sys.exit(1)

    from openstates.utils.cookie_provider import WafBlockDetected
    from openstates.utils.mi_cookies import MI_COOKIE_PROVIDER
    from mi.bills import MIBillScraper
    from mi import Michigan

    if args.mint_via_scrapebot:
        print(f"Dispatching mint_scrape_cookies to ScrapeBot (timeout={args.mint_timeout}s)...")
        try:
            result = dispatch_mint_cookies("mi", timeout_seconds=args.mint_timeout)
        except ScrapeBotDispatchError as exc:
            print(f"ERROR: ScrapeBot dispatch failed: {exc}", file=sys.stderr)
            sys.exit(3)
        write_cookie_cache(MI_COOKIE_PROVIDER.cache_path, result["cookies"], result["user_agent"])
        print(f"Seeded cookie cache from ScrapeBot's mint: {MI_COOKIE_PROVIDER.cache_path}\n")

    print(f"Cookie cache: {MI_COOKIE_PROVIDER.cache_path}")
    datadir = os.path.join(scraped_data_dir, "mi")
    print(f"Scrape output: {datadir}")
    print(f"Session: {args.session}  |  target count: {args.count}\n")

    juris = Michigan()
    os.makedirs(datadir, exist_ok=True)

    scraper = MIBillScraper(juris, datadir, strict_validation=False)

    # Cap how many bills get pulled from the real scrape() generator -- everything
    # downstream runs unmodified, this only limits how many items do_scrape() sees.
    real_scrape = scraper.scrape

    def capped_scrape(*a, **kw):
        return itertools.islice(real_scrape(*a, **kw), args.count)

    scraper.scrape = capped_scrape

    try:
        report = scraper.do_scrape(session=args.session)
    except WafBlockDetected:
        # CookieProvider.fetch_with_retry() already invalidated the cache and
        # re-warmed once (per OPEN-19's "retry exactly once" policy) before this
        # propagated -- a genuine, currently-active WAF block, not a script bug.
        # Consistent with the ongoing reputation-based blocking documented in
        # notes/mi-ip-reputation-block-confirmed-20260802.md.
        print("\n--- BLOCKED ---")
        print("MI's WAF rejected both the cached-cookie attempt and the re-warmed retry.")
        print("This is a real, currently-active block, not a bug in this script -- see")
        print("notes/mi-ip-reputation-block-confirmed-20260802.md for the known pattern.")
        sys.exit(2)

    print("\n--- done ---")
    for obj_type, count in report.get("objects", {}).items():
        print(f"  {obj_type}: {count}")
    print(f"\nJSON written to: {datadir}")

    print(f"\nCookie/UA cache: {MI_COOKIE_PROVIDER.cache_path}")
    try:
        print(f"  cached User-Agent: {MI_COOKIE_PROVIDER.get_user_agent()}")
    except Exception as exc:
        print(f"  (couldn't read cached UA: {exc})")


if __name__ == "__main__":
    main()
