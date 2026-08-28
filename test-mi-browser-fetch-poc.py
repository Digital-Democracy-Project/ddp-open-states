#!/usr/bin/env python3
"""
Proof-of-concept for PLAN-scrapebot.md §9 ("Option B") -- tests whether solving
Barracuda's CAPTCHA once inside a real browser session validates that session
for many subsequent MI bill-page fetches, at real scale (dozens+, not the
9-PDF/3-bill handful from tonight's manual spot check).

Standalone. Does NOT touch CAMS, ScrapeBot, ddp-sync, or any of the
browser_fetch_url/mint_cookies plumbing sketched in PLAN-scrapebot.md §9.3 --
it drives its own Playwright browser directly. This tests the underlying
HYPOTHESIS (solve once, reuse the session for N fetches) before any of that
design is approved or built. Nothing here is a component of the eventual real
implementation, though the fetch loop mirrors the shape handle_fetch_url would
take -- page.goto(url) + page.content(), checked against the same
content_matches_block_markers() heuristic production code already uses.

Requires a human at the keyboard: when the first navigation hits Barracuda's
challenge page, the script pauses and waits for you to solve it by hand in the
visible (headed) browser window, then press Enter in this terminal to
continue. Everything after that runs unattended, at a fixed delay between
fetches, until --count real bill pages have been fetched or a block reappears.

Usage:
    source activate-dev.sh && python3 test-mi-browser-fetch-poc.py [--count N] [--session SESSION] [--delay SECONDS] [--headless]

    or:
    ./test-mi-browser-fetch-poc.sh [--count N] [--session SESSION] [--delay SECONDS]

Writes a JSON results log to _archive_scratch/mi-browser-fetch-poc/<run>.json.
Exit codes: 0 = completed --count fetches with no block; 2 = blocked mid-run
(results still written); 1 = wrong environment / setup error.
"""
import argparse
import json
import os
import re
import sys
import time

# Same real bill-listing search endpoint scrapers/mi/bills.py's own scrape() builds --
# not a guessed URL.
_SEARCH_URL_TEMPLATE = (
    "https://legislature.mi.gov/Search/ExecuteSearch?chamber=&docTypesList=HB%2CSB&"
    "docTypesList=HR%2CSR&docTypesList=HCR%2CSCR&docTypesList=HJR%2CSJR&sessions={session}&"
    "sponsor=&number=&dateFrom=&dateTo=&contentFullText="
)
# Matches scrapers/mi/bills.py's own xpath against the same real bill-listing table.
_BILL_LINK_XPATH = "//div[contains(@class,'tableScrollWrapper')]/table[1]/tbody/tr/td[1]/a"
# OPEN-21's own conservative MI pacing (scrapers/mi/bills.py) -- matched here as the
# default so this test doesn't hammer the site any harder than the real scraper would.
_DEFAULT_DELAY_SECONDS = 6.0


def make_bill_url(href):
    """Same normalization as MIBillScraper.make_bill_url() -- redirector URL to permalink."""
    match = re.search(r"objectName=([^&]+)", href, re.IGNORECASE)
    if not match:
        return href
    return f"https://legislature.mi.gov/Bills/Bill?ObjectName={match.group(1)}"


def looks_blocked(html: str) -> bool:
    from openstates.utils.cookie_provider import content_matches_block_markers

    return content_matches_block_markers(html.encode())


def wait_for_manual_solve(page, target_url):
    print("\n--- CAPTCHA / block page detected ---")
    print(f"URL: {page.url}")
    print("Solve it by hand in the visible browser window (read the distorted text,")
    print("type it, click Submit), then press Enter here to continue.")
    input("Press Enter once solved (or Ctrl+C to abort)... ")
    page.goto(target_url, wait_until="networkidle", timeout=30_000)
    html = page.content()
    if looks_blocked(html):
        print("Still looks blocked after your solve attempt -- try again.")
        return wait_for_manual_solve(page, target_url)
    print("Session validated -- continuing.\n")
    return html


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--count", type=int, default=30, help="number of real bill pages to fetch (default: 30)"
    )
    parser.add_argument(
        "--session", default="2025-2026", help="MI legislative session (default: 2025-2026)"
    )
    parser.add_argument(
        "--delay", type=float, default=_DEFAULT_DELAY_SECONDS,
        help=f"seconds to wait between fetches (default: {_DEFAULT_DELAY_SECONDS}, matching "
        f"the real scraper's own OPEN-21 pacing)",
    )
    parser.add_argument(
        "--headless", action="store_true",
        help="run headless -- only useful if you're SURE no CAPTCHA will appear "
        "(e.g. re-running immediately after a solve in a separate headed run); "
        "there is no way to solve a CAPTCHA by hand in a headless window",
    )
    args = parser.parse_args()

    archive_root = os.environ.get("ARCHIVE_ROOT_DIR", "")
    if "ddp-open-states-dev" not in archive_root:
        print(
            "ERROR: this doesn't look like the dev environment (ARCHIVE_ROOT_DIR isn't "
            "under ddp-open-states-dev). Source activate-dev.sh first.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: playwright not installed in this venv.", file=sys.stderr)
        sys.exit(1)

    import lxml.html

    search_url = _SEARCH_URL_TEMPLATE.format(session=args.session)
    run_id = time.strftime("%Y%m%dT%H%M%S")
    out_dir = os.path.join(archive_root, "mi-browser-fetch-poc")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{run_id}.json")

    print(f"Session: {args.session}  |  target count: {args.count}  |  delay: {args.delay}s")
    print(f"Results will be written to: {out_path}\n")

    results = []
    run_started = time.monotonic()
    exit_code = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        context = browser.new_context()
        page = context.new_page()

        print(f"Navigating to search page: {search_url}")
        page.goto(search_url, wait_until="networkidle", timeout=30_000)
        html = page.content()
        if looks_blocked(html):
            html = wait_for_manual_solve(page, search_url)

        tree = lxml.html.fromstring(html)
        tree.make_links_absolute(search_url)
        links = tree.xpath(_BILL_LINK_XPATH)
        if not links:
            print("ERROR: found 0 bill links on the search results page -- xpath may be "
                  "stale, or the page didn't actually load real results.", file=sys.stderr)
            browser.close()
            sys.exit(1)

        bills = []
        for link in links[: args.count]:
            href = link.xpath("@href")[0]
            text = link.xpath("text()")[0]
            bills.append({
                "bill_id": text.split(" of ")[0],
                "url": make_bill_url(href),
            })
        print(f"Found {len(links)} real bill links on the search page; testing first {len(bills)}.\n")

        for i, bill in enumerate(bills):
            t0 = time.monotonic()
            try:
                page.goto(bill["url"], wait_until="networkidle", timeout=30_000)
                html = page.content()
            except Exception as exc:
                elapsed_ms = round((time.monotonic() - t0) * 1000)
                print(f"[{i+1}/{len(bills)}] {bill['bill_id']}: ERROR ({exc}) after {elapsed_ms}ms")
                results.append({
                    "index": i, "bill_id": bill["bill_id"], "url": bill["url"],
                    "elapsed_ms": elapsed_ms, "blocked": None, "error": str(exc),
                    "since_start_s": round(time.monotonic() - run_started, 1),
                })
                continue

            elapsed_ms = round((time.monotonic() - t0) * 1000)
            blocked = looks_blocked(html)
            status = "BLOCKED" if blocked else "ok"
            print(f"[{i+1}/{len(bills)}] {bill['bill_id']}: {status} ({elapsed_ms}ms)")
            results.append({
                "index": i, "bill_id": bill["bill_id"], "url": bill["url"],
                "elapsed_ms": elapsed_ms, "blocked": blocked, "error": None,
                "since_start_s": round(time.monotonic() - run_started, 1),
            })

            if blocked:
                print(f"\nBlocked after {i+1}/{len(bills)} real fetches "
                      f"({round(time.monotonic() - run_started, 1)}s into the run).")
                choice = input("Solve it by hand and continue? [y/N]: ").strip().lower()
                if choice == "y":
                    wait_for_manual_solve(page, bill["url"])
                    continue
                exit_code = 2
                break

            if i < len(bills) - 1:
                time.sleep(args.delay)

        browser.close()

    summary = {
        "run_id": run_id,
        "session": args.session,
        "requested_count": args.count,
        "delay_seconds": args.delay,
        "total_elapsed_s": round(time.monotonic() - run_started, 1),
        "fetched": len(results),
        "blocked_count": sum(1 for r in results if r["blocked"]),
        "error_count": sum(1 for r in results if r["error"]),
        "results": results,
    }
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n--- summary ---")
    print(f"Fetched: {summary['fetched']}/{args.count}")
    print(f"Blocked: {summary['blocked_count']}")
    print(f"Errors: {summary['error_count']}")
    print(f"Total elapsed: {summary['total_elapsed_s']}s")
    print(f"Full results: {out_path}")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
