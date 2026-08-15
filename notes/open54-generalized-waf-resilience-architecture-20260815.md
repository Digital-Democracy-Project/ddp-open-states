# OPEN-54: generalized per-jurisdiction WAF resilience — architecture assessment

Resolves OPEN-54's own open questions and records what was actually implemented and verified.
Written as part of the same pass that implements it (rather than strictly before, since the real
second jurisdiction — FL — only became known mid-investigation via the OPEN-66 backfill work),
but every question below is answered against real, tested code, not a proposal.

## Where does the config live?

`openstates-scrapers` already depends on `openstates-core` (confirmed: `scrapers/mi/bills.py`
already imports `openstates.utils.cookie_provider`/`openstates.utils.mi_cookies` directly, and
both packages install into one shared venv in this dev checkout) — never the other direction. So
the shared profile registry lives in `openstates-core`, alongside `cookie_provider.py` (the one
piece of MI's stack that was already jurisdiction-agnostic):

* `openstates-core/openstates/utils/resilience_profiles.py` — `WafResilienceProfile` dataclass +
  `RESILIENCE_PROFILES` dict + `profile_for_netloc()` lookup. Single source of truth both the
  scraper mixin path and the archiver's fetch path read from.
* `openstates-core/openstates/utils/waf_circuit_breaker.py` — the generalized
  `raise_if_waf_block_threshold_reached()` function (see below).
* `openstates-core/openstates/utils/mi_cookies.py` / `fl_cookies.py` — one small file per
  jurisdiction holding that jurisdiction's own `CookieProvider` instance (including any
  jurisdiction-specific warm-up quirk, like FL's below) — mirrors the pattern MI's file already
  used before this ticket, not a new convention.

## Does `_waf_circuit_breaker.py` move out of `scrapers/mi/`?

Its *logic* does; its *file* mostly doesn't, to avoid touching MI's existing call sites.
`raise_if_waf_block_threshold_reached(consecutive_blocks, max_consecutive_blocks, exc,
scrape_label, fetch_description)` is a plain function in `openstates-core`, deliberately not a
stateful class — a scraper already has a natural place for its own per-instance counter
(`self._consecutive_waf_blocks`, MI's original attribute name, unchanged so its existing tests
still pass unmodified), and the archiver's module-level fetch function holds its own module-level
counter (`_profile_consecutive_blocks`, keyed by profile name) the same way. Neither needs the
shared function to own the state, just the increment-then-maybe-raise decision.
`scrapers/mi/_waf_circuit_breaker.py` still exists, but is now a thin wrapper: same public
`MIWafCircuitBreakerMixin` class, same two method names
(`_register_waf_block_or_abort`/`_register_waf_success`), same `_consecutive_waf_blocks`
attribute shape — so `bills.py`/`events.py` needed zero changes — but the actual threshold check
now calls the shared function, and `MAX_CONSECUTIVE_WAF_BLOCKS` is read from
`RESILIENCE_PROFILES["mi"]` instead of being hardcoded.

## What does a profile actually specify?

```python
@dataclass(frozen=True)
class WafResilienceProfile:
    name: str
    netloc: str                              # which host this profile guards, e.g. flhouse.gov
    cookie_provider: CookieProvider
    requests_per_minute: int
    circuit_breaker_max_consecutive_blocks: int
    retry_excluded_exceptions: tuple
    user_agent_rotation_enabled: bool
```

`retry_excluded_exceptions`/`user_agent_rotation_enabled` are part of the schema but MI's own
scraper-side mixin (`MIResilientScraperMixin`) still sets them directly rather than reading them
from the profile — they're Scraper-only concepts (`self._resilience_retry_excluded_exceptions`,
etc.) the archiver's function-based fetch path has no equivalent for, and MI's own existing test
suite (`test_resilience_config.py`) relies on `importlib.reload()` + `monkeypatch.setenv()` to
verify `MI_SCRAPELIB_RPM` is tunable without a redeploy — routing that specific value through a
frozen dataclass computed once at import time would have silently broken that exact test (the
dataclass instance doesn't get rebuilt on a bare module reload of `mi_bills`), so
`MI_SCRAPELIB_RPM` was deliberately left reading `os.environ` directly in `bills.py`, unchanged.
The profile's own `requests_per_minute` reads the same env var independently for the archiver's
benefit, which has no equivalent reload-based tunability requirement.

## MI-parity

Verified, not assumed: `RESILIENCE_PROFILES["mi"]` reproduces `circuit_breaker_max_consecutive_blocks=3`
(was `MAX_CONSECUTIVE_WAF_BLOCKS = 3`), `requests_per_minute` from the same `MI_SCRAPELIB_RPM` env
var/default, `user_agent_rotation_enabled=False`, and the same `cookie_names`/`warm_up_url` MI's
`CookieProvider` already used. MI's full existing test suites pass unchanged:
`scrapers/mi/tests/` (39 tests) and `openstates-core`'s `openstates/cli/tests/test_text_extract.py`
+ `openstates/utils/tests/` (279 tests, includes the archiver's own MI-path tests).

## The real second jurisdiction: FL

OPEN-54's own AC only asks for "a test/dummy profile, not necessarily a real jurisdiction" — FL
became the real one mid-investigation (OPEN-66's backfill). A live spike (2026-08-15) found
flhouse.gov's F5 BIG-IP ASM WAF, unlike MI's Barracuda WAF, needs **no CAPTCHA-solving at all** —
`CookieProvider`'s *default* Playwright warm-up reproduced the exact "Request Rejected" block real
scraper traffic hit, because Playwright's default headless Chromium literally announces itself as
`HeadlessChrome` in its User-Agent, and that substring alone was sufficient for this WAF to block
on. Launching with Chromium's newer headless mode (`--headless=new`) and a plain desktop Chrome UA
(no "Headless" substring) got real content — including the real `session_cookie_mfhp` cookie
`scrapers/fl/bills.py`'s `_FLHouseWAFSource` already expected — on the first attempt, against two
different bills that 100% failed via plain `requests` moments earlier.

This is why `CookieProvider.__init__`'s existing `warm_up_func` override parameter matters: FL's
profile (`fl_cookies.py`) supplies a custom warm-up function (same shape as the default, different
launch args/UA) instead of needing any change to `cookie_provider.py` itself. **This means "a new
jurisdiction requires only a config entry, not new code in either repo" is true for the *shared
framework* code** (`resilience_profiles.py`, `waf_circuit_breaker.py`, the archiver's fetch path,
MI's mixin wrapper — none of these changed to add FL) **but a jurisdiction can still need its own
small file** (mirroring `mi_cookies.py`'s existing precedent) if its WAF has its own quirk. FL's
`bill_no=`-targeting scraper rework (using this profile for real, replacing OPEN-66's blind retry)
is tracked separately as its own follow-up, not part of this ticket.

## OPEN-52 / OPEN-53: resolved as part of this work

* **OPEN-52** (no sustained-block escalation): `archive()`'s `for bill in bills:` loop previously
  only exited non-zero on `totals["conflicts"]` — a 100%-blocked run still printed a yellow status
  line and exited 0. Now `_fetch_bytes()` raises `ScrapeError` once a profile's consecutive-block
  threshold is reached (via the shared function above), `archive_bill_versions()`'s own
  per-document exception handling explicitly re-raises `ScrapeError` instead of swallowing it as
  one more `fetch_errors`/`blocked` count, and `archive()` catches it, prints a clear "aborted"
  message, and exits 1.
* **OPEN-53** (no MI-equivalent archiver rate limit): the archiver previously used one shared
  module-level `scraper` for every jurisdiction's fetch. `_fetch_bytes()` now gets a lazily-created,
  per-profile `scrapelib.Scraper` instance (`_scraper_for_profile()`) configured with that
  profile's own `requests_per_minute` — MI's archiver fetches now pace at the same 10/min as its
  scraper, without touching every other jurisdiction's shared scraper instance/rate.

Both verified via new, explicit unit tests (`TestFetchBytesResilienceProfileDispatchOPEN54`,
`TestFetchBytesCircuitBreakerOPEN52`, `TestArchiveCommandAbortsOnScrapeErrorOPEN52` in
`openstates-core`'s `test_text_extract.py`), not just inferred from the diff.

## References

* OPEN-54 (this ticket), OPEN-52, OPEN-53
* OPEN-66 — the FL investigation that surfaced FL as the real second jurisdiction
* `openstates-core/openstates/utils/resilience_profiles.py`, `waf_circuit_breaker.py`,
  `fl_cookies.py`, `mi_cookies.py` (unchanged), `cookie_provider.py` (unchanged)
* `openstates-core/openstates/cli/text_extract.py` — `_fetch_bytes()`/`archive()`
* `openstates-scrapers/scrapers/mi/_waf_circuit_breaker.py`
