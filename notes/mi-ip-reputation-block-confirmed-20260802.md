# Michigan blocking: confirmed IP-level, not scraper-specific (2026-08-02)

## Context: continuing from today's OPEN-21 live verification

Earlier today, a manual `./run-scrape.sh mi` run (after merging and deploying OPEN-21/OPEN-22's
AC7 fixes, then again after restarting `ddp-sync`) confirmed the retry-stacking fix works
correctly — exactly 2 physical HTTP attempts per try, no backoff stacking — but MI still failed
both times: every cookie warm-up attempt got blocked immediately, regardless of a fresh rewarm.
See `notes/mi-barracuda-followup-tickets-20260802.md` for the fuller history (OPEN-18 through
OPEN-22) this continues.

That left one open question worth checking directly: is this blocking specific to the scraper's
request shape (headers, TLS fingerprint, cookie handling), or something broader?

## What was tested

Navigated a **fresh Playwright browser** — no scraper cookies, no `MI_COOKIE_PROVIDER` warm-up,
no automation-specific headers beyond whatever Playwright's default Chromium sends — from this
same machine, to two URLs:

1. The exact `ExecuteSearch` URL the scrape had just failed on:
   `https://legislature.mi.gov/Search/ExecuteSearch?chamber=&docTypesList=HB%2CSB&...`
2. The plain domain root: `https://legislature.mi.gov/`

## Result: blocked immediately, both times, real Barracuda CAPTCHA

Both requests returned **HTTP 200 OK** (the disguised-block behavior OPEN-18's
`content_matches_fake_404_block()`/`content_matches_block_markers()` already exist to catch) with
page title **"Validation request"** — a real Barracuda "User validation required to continue"
CAPTCHA challenge page, serving a `captcha.gif` image to solve. Screenshot:
`notes/assets/mi-waf-validation-challenge-20260802.png`.

The page's own text is explicit about *why*, and it's unambiguous:

> Validation needed due to the detection of invalid input from this client IP address, error
> code: 426
>
> Number of attempts left: 5

**This is an IP-level block, not a per-session or per-cookie one.** A completely fresh browser
session — no automation fingerprint, no scraper-specific headers, nothing `MIResilientScraperMixin`
or `mi_waf_get()` touches — got the identical challenge as the scraper, from the same machine's
IP. Hitting the plain homepage (not just the specific search query) confirms it's whole-domain,
not tied to the `ExecuteSearch` endpoint or its query parameters.

## Why this matters

This directly confirms the theory `notes/mi-barracuda-bot-detection-analysis-20260801.md` and
OPEN-21/OPEN-22 have been circling since 2026-08-01: Barracuda is tracking IP reputation and/or
request-volume history that overrides cookie-based validation entirely once tripped. It rules out
the alternative explanation that this is something specific about the scraper's own request
shape (a fixable header/UA/TLS mismatch) — a real browser is blocked identically. Nothing in
OPEN-21 (rate limit + retry-stacking) or OPEN-22's AC7 (MI-events circuit-breaker parity) was
ever meant to fix this, and neither does; both worked exactly as designed today and MI still
failed for this reason alone.

**Caution surfaced by this finding, not fully resolved here:** the "Number of attempts left: 5"
counter strongly implies repeated failed validation attempts from an IP have consequences beyond
the immediate challenge — and today's own manual verification work (two `run-scrape.sh mi` runs,
plus this Playwright check) all counted as additional attempts against the same IP that OPEN-22
is trying to detect a *sustained* pattern for. Live manual testing against MI is not free of cost
to the investigation itself. Worth deliberately minimizing further ad-hoc manual hits against
`legislature.mi.gov` until either the block clears on its own or a real fix is scoped — pushing
harder on live verification right now plausibly makes the reputation signal worse, not better.

## Relationship to open tickets

- **OPEN-19** (cookie-reuse fetcher) — necessary but, per this finding and the 2026-08-01 note,
  confirmed insufficient on its own; this doesn't change that.
- **OPEN-21** (rate limit + resilience mode, merged and live-verified 2026-08-02) — worked
  correctly; out of scope for this problem by design.
- **OPEN-22** (sustained-blocking escalation, `ddp-sync` half merged 2026-08-02) — this finding is
  exactly the kind of pattern that ticket's escalation alert exists to surface once enough weekly
  runs accumulate `waf_block`-classified failures. It detects and alerts on the pattern; it does
  not fix the underlying IP-level block. No ticket currently scopes an actual fix for that — the
  2026-08-02 follow-up note's "five candidate levers" list (rate-limiting, adaptive backoff,
  halting manual testing, an alternate non-WAF data source, IP/proxy rotation) is still the
  relevant menu, with IP rotation specifically flagged there as crossing into "actively evading a
  state government site's bot protection" — an explicit decision to make, not a default to drift
  into.

## References

- `notes/mi-barracuda-bot-detection-analysis-20260801.md` — original full analysis
- `notes/mi-barracuda-followup-tickets-20260802.md` — OPEN-21/OPEN-22 scoping and the earlier
  2026-08-02 live-verification result this continues
- `notes/assets/mi-waf-validation-challenge-20260802.png` — screenshot of the CAPTCHA challenge
- Jira: OPEN-19, OPEN-20, OPEN-21, OPEN-22
