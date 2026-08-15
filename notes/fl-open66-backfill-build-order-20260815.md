# FL OPEN-66 vote backfill — build order

Records the plan for actually recovering the 16 FL bills still missing votes after OPEN-66
(FL's asymmetric WAF-retry fix, `openstates-scrapers` PR #27, merged) — written before starting
any of the work below, so the sequencing decision itself is on record.

## The 16 bills

Re-verified against **live production** 2026-08-15 via `quality_check.py --bill-ids fl 2026 ...`
(not reused from the original ticket's Tier-2 random sample, which had since-resolved false
positives per its own caveat): HB1253, HB1265, HB1285, HB1293, HB139, HB1553, HB243, HB269,
HB283, HB299, HB309, HB313, HB339, HB371, HB53, HB99.

## Why this isn't a one-step fix

Two independent, orthogonal gaps have to close before these 16 bills' votes are actually
recoverable:

1. **No way to target just these 16 bills.** Only MA and NY (of ~56 `openstates-scrapers`
   jurisdictions) have a `bill_no=` single-bill scrape filter. Without it, the only way to touch
   these 16 bills is a full ~1,900-bill/~25hr FL session rescrape.
2. **flhouse.gov's WAF currently rejects the request even when targeted.** A live test of all 16
   bills via a prototype `bill_no=` filter (single continuous `scrape()` session, matching
   nightly-run behavior) found flhouse.gov's WAF rejected every single House-vote-detail request,
   even through OPEN-66's own 3-attempt retry — 0 of 16 recovered. OPEN-66's retry logic has
   never actually fired against the live WAF before this test (its own round-3 verification note
   says the trigger condition never fired during a real 25-hour rescrape), so there's no proven
   track record for it, and the retry's own shape (3 hits to the *identical* URL within
   ~13-14 seconds) is a plausible bot signature that could be making a real block worse rather
   than recovering from a transient one — MI hit the literal same-shaped problem, tracked as
   OPEN-53 ("generic retry fires on WAF blocks before the cookie-rewarm path engages, likely
   worsening MI's WAF reputation").

## Track 1: generalized WAF resilience (OPEN-52 / OPEN-53 / OPEN-54)

MI is currently the only jurisdiction with any WAF/cookie resilience machinery
(`CookieProvider`, `mi_waf_get()`, `_waf_circuit_breaker.py`), and all of it is hand-wired
specifically to MI rather than being a reusable, config-driven capability. OPEN-54 (filed
2026-08-08) already anticipated exactly this situation — its own acceptance criteria explicitly
require an architecture assessment before any implementation, and its own scope note says the
point is to make the *next* jurisdiction that hits this problem cheap, not to build one more
one-off hand-wire. FL is that next jurisdiction now.

The one piece of MI's stack that's already jurisdiction-agnostic: `CookieProvider`
(`openstates-core/openstates/utils/cookie_provider.py`) launches a real Playwright browser
against a configurable `warm_up_url`, extracts named cookies + the real UA, caches both to disk,
and its `BLOCK_PAGE_MARKERS` list already includes `b"request rejected"` — flhouse.gov's exact
block-page title — even though nothing wires FL to it yet.

## Track 2: per-bill targeting (OPEN-77 through OPEN-83)

Filed under the OPEN-72 "Scraper Enhancements" epic, one ticket per jurisdiction lacking
`bill_no=` (MA/NY excluded, already have it): OPEN-77 (FL), OPEN-78 (WA), OPEN-79 (US),
OPEN-80 (VA), OPEN-81 (MI — different scraper architecture, needs its own mechanism),
OPEN-82 (UT), OPEN-83 (AZ). FL's version is already prototyped (uncommitted, this checkout) and
confirmed working correctly on its own terms: a live test correctly scoped processing to exactly
the requested bill(s) and cheaply skipped everything else via `SkipItem`. This track is
independent of Track 1 and can land on its own schedule.

## Build order

1. **Validation spike (cheap, first).** Test whether a *plain* Playwright browser visit to
   flhouse.gov (no CAPTCHA-solving) passes the WAF and yields a valid cookie. `CookieProvider`
   already ships its own default Playwright warm-up — it doesn't require ScrapeBot/CAMS
   dispatch at all for the basic case. MI needs the full ScrapeBot pipeline specifically because
   its WAF serves a Barracuda distorted-text CAPTCHA a plain headless browser can't solve
   (requiring ScrapeBot's MLX vision-model solving step). If flhouse.gov's WAF turns out to be a
   simpler JS-challenge with no CAPTCHA, a bare `CookieProvider` instance is sufficient — much
   less to build than wiring up ScrapeBot. Also confirms the real cookie name(s) flhouse.gov's
   WAF issues (`_FLHouseWAFSource`'s docstring names `session_cookie_mfhp`, unverified against a
   real response as of this writing).
2. **OPEN-54 architecture assessment**, informed by (1)'s answer. Resolves: where the config
   lives given `openstates-scrapers`/`openstates-core` are separate repos, whether
   `_waf_circuit_breaker.py` moves into `openstates-core` next to `cookie_provider.py`, the
   profile schema (rate limit, `CookieProvider` config, retry-exclusions, circuit-breaker
   thresholds, UA-rotation opt-out), and whether OPEN-52/53 fold in as MI's archiver profile.
3. **Implement OPEN-54.** Generalized config + MI's current real settings reproduced exactly as
   its profile (regression-checked: existing MI test suite passes unchanged) + OPEN-52/53 folded
   in if the assessment recommends it.
4. **Add FL's profile and rework FL's House-vote request path.** `HouseSearchPage`/
   `HouseBillPage`/`HouseComVote` move from OPEN-66's blind same-URL retry onto the new
   cookie-based resilience; OPEN-66's retry likely stays as a last-resort fallback layer rather
   than the primary mechanism.
5. **Only if step 1 shows FL needs it:** wire `fl:` into `ddp-agents/config/
   scrapebot_jurisdictions.yaml` + a CAMS `mint_cookies` dispatch path, mirroring MI.
6. **Land OPEN-77 for real** (independent of 1-5, can happen any time in parallel): commit the
   existing `bill_no=` prototype, add test coverage, open the PR.
7. **Run the actual backfill.** Dry-run scrape (no DB writes) for the 16 bills with targeting +
   resilience both in place, confirm votes recovered, then the real `--import` against
   production (`DATABASE_URL` explicitly pointed at the real `openstates` database on
   port 5433 — not the isolated `openstates_dev` this checkout's `activate-dev.sh` defaults to).

Steps 2-4(-5) are strictly sequential. Step 6 is independent. Step 7 depends on both tracks
landing.

## References

* OPEN-66 — the fix whose residual gap this backfill closes
* OPEN-52 / OPEN-53 / OPEN-54 — Track 1, generalized WAF resilience
* OPEN-72 (epic) / OPEN-77 through OPEN-83 — Track 2, per-jurisdiction `bill_no=`
* `openstates-core/openstates/utils/cookie_provider.py` — the already-generic primitive Track 1
  builds on
* `openstates-scrapers/scrapers/mi/bills.py`, `_waf_circuit_breaker.py` — the current MI-only
  implementation being generalized
