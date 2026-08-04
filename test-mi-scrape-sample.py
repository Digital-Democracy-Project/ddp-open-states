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

Usage:
    source activate-dev.sh && python3 test-mi-scrape-sample.py [--count N] [--session SESSION]

    or simply:
    ./test-mi-scrape-sample.sh [--count N] [--session SESSION]
"""
import argparse
import itertools
import os
import sys


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
