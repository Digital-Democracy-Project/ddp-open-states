# OPEN-30 shipped: parse_roll_call() now registers with MIWafCircuitBreakerMixin; 2026-07-03 backfill still pending real legislature.mi.gov/prod access

## Context

Follow-up from `notes/mi-open-28-missing-vote-root-cause-20260805.md`'s root-cause finding: MI's
`parse_roll_call()` (`openstates-scrapers/scrapers/mi/bills.py`) fetched each vote's journal
document separately from `scrape_bill()`'s main-page fetch, and on `scrapelib.HTTPError` or
`WafBlockDetected` just logged a warning and returned `None` -- invisible to
`MIWafCircuitBreakerMixin`'s consecutive-block counter, the `ScrapeError` abort threshold, and
OPEN-22's escalation history. This silently, permanently dropped 17+ votes across both chambers on
2026-07-03, unhealed across 33+ days of subsequent scrapes.

## What changed

`openstates-scrapers/scrapers/mi/bills.py`'s `parse_roll_call()`:

- The `except (scrapelib.HTTPError, WafBlockDetected):` block now binds the exception and calls
  `self._register_waf_block_or_abort(e, item_label=f"roll call #{rc_num} document ({url})", ...)`
  before returning `None`, instead of a bare `self.warning(...)`.
- `self._register_waf_success()` is now called immediately after a successful fetch, mirroring
  `scrape_bill()`'s placement (before any content-level parsing).

**Design decision: shares scrape_bill()'s counter, not a separate one.** `_consecutive_waf_blocks`
is a single per-instance counter on `MIBillScraper`. A block on either the main bill-page fetch
(`scrape_bill()`) or a per-vote journal fetch (`parse_roll_call()`) now feeds the *same* counter and
abort threshold, per the ticket's explicit request to match the existing pattern. This means a
mass-vote day with several genuinely-failing per-vote fetches in a row can now trip a full-scrape
`ScrapeError` abort on its own -- a deliberate tradeoff: visible-and-occasionally-noisy beats
invisible-and-permanently-silent.

**`_waf_circuit_breaker.py`**: `_register_waf_block_or_abort`'s `exc` parameter type hint was
relaxed from `WafBlockDetected` to `Exception`, since `parse_roll_call()` (unlike `scrape_bill()`/
`events.py`) catches both `scrapelib.HTTPError` and `WafBlockDetected` in one except block and now
registers either. No runtime behavior change -- the method only does string formatting and
exception chaining, both exception-type-agnostic.

**Test coverage** (`scrapers/mi/tests/test_bills.py`): 5 new tests covering `parse_roll_call()`
directly (register-on-`WafBlockDetected`, register-on-`scrapelib.HTTPError`, abort-after-threshold,
reset-after-success) plus one end-to-end `scrape_votes()` test proving a persistently-blocked vote
fetch yields no `VoteEvent` without crashing, while visibly incrementing the shared counter. All 39
MI tests pass (34 pre-existing + 5 new), confirming no regressions to `scrape_bill()`'s or
`scrape_event_page()`'s existing circuit-breaker behavior.

## AC4 (the 2026-07-03 backfill): not executed from this workspace

This ticket's fourth acceptance criterion -- a targeted backfill of House Roll Calls #288-334 and
Senate Roll Calls #190-225 -- could not be carried out in this session:

- **No live route to `legislature.mi.gov`.** OPEN-28's investigation already flagged that the exact
  reason 2026-07-03's journal documents fail *every* fetch attempt (WAF-window vs. a
  structurally-different consolidated end-of-term journal format vs. something else) was never
  confirmed, and confirming it requires a real Playwright session against the live site -- not
  available in this sandboxed workspace, and risky to attempt casually given MI's WAF sensitivity.
- **No production DB/API credential** in this environment to run or verify a real backfill.

**Why a separate backfill script probably isn't needed once the above is resolved:** per OPEN-28's
note, `scrape_votes()` re-reads a bill's *entire* history table on every single scrape, not just
what changed since last time. So once this fix ships *and* the underlying per-vote fetch issue is
confirmed resolved (or was only ever a transient WAF condition that's since cleared), an ordinary
scheduled re-scrape of the affected bills should organically pick up the missing 2026-07-03 votes --
no new tooling required, just confirmation that the fetch itself now succeeds.

**Follow-up for whoever has legislature.mi.gov + prod access:**
1. Confirm (via a real, careful, rate-limited request) whether a 2026-07-03 journal document now
   fetches successfully.
2. If yes: trigger (or wait for) a normal scheduled MI bill re-scrape and verify the 17 previously-
   identified bills' vote counts now match live.
3. If still failing: the failure is structural (not transient WAF), and needs its own investigation
   into 2026-07-03's journal document format specifically.

## References

- `notes/mi-open-28-missing-vote-root-cause-20260805.md` -- the investigation this follows from
- `openstates-scrapers/scrapers/mi/bills.py` -- `parse_roll_call()` (~line 487), `scrape_votes()`
  (~line 353), `scrape_bill()`'s contrasting circuit-breaker registration (~line 233-251)
- `openstates-scrapers/scrapers/mi/_waf_circuit_breaker.py` -- `MIWafCircuitBreakerMixin`
- `openstates-scrapers/scrapers/mi/tests/test_bills.py` -- new failure-path tests
- Jira: OPEN-30 (this ticket), OPEN-28 (root cause), OPEN-17/18/19/21/22/23 (related but distinct
  MI WAF history)
