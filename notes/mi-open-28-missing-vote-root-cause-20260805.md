# OPEN-28 root-caused: MI's missing-vote-event gap is a single mass-vote-day capture failure (2026-07-03), distinct from the OPEN-19/21/22/23 staleness pattern

## Context

OPEN-28 asked to root-cause the 8 MI bills flagged by the 2026-07-28 `--tier2-random` run
(`notes/mi-tier2-500-bill-random-sample-20260803.md`, `PLAN-coverage-completeness-check.md` §14) as
each missing exactly one vote event vs. live, and determine whether that's the same root cause as
MI's general WAF-driven staleness (OPEN-19/OPEN-21/OPEN-22/OPEN-23) or something distinct.

This workspace clone has no production DB credential and no `OPENSTATES_API_KEY` by default (see
the planning-turn `CODEBOT_QUESTION` in this ticket's session). The operator resolved that by
adding a real `OPENSTATES_API_KEY` (scoped to OPEN-project tickets) to `.claude/.env`, and pointed
at `http://localhost:8002` — this checkout's local api-v3 replica, served read-only over the same
`apikey` query-param scheme as the live API, with the fixed key
`00000000-0000-0000-0000-000000000001` (already hardcoded in `quality_check.py`) — as the "local"
side, instead of raw SQL. All empirical work below uses those two HTTP APIs only; no direct
Postgres access was used or needed.

## Method

`quality_check.py`'s own `fetch_bill()` isn't importable standalone in this environment (its module
top-level does `import psycopg2`, not installed here, for functionality this investigation didn't
need), so a small standalone script reproduced the identical request shape (`GET /bills` with
`jurisdiction`, `session`, `identifier`, `include=[votes,sponsorships,actions]`, `apikey`) against
both `LOCAL_API`/`LOCAL_KEY` and `LIVE_API`/`OPENSTATES_API_KEY`, with retry+backoff (the original
notes already documented the live API's bursty `429`/timeout noise — confirmed again here on a
first pass, resolved by retrying with a longer timeout).

Three passes:
1. **The original 8 bills**, re-checked directly by identifier.
2. **A broad, unfiltered random sample** of 60 bills across all 3,884 MI 2025-2026 bills (via the
   local API's `page`/`per_page` listing), to sanity-check the original ~1.6%-of-500 prevalence
   still holds.
3. **A targeted random sample of 90 bills drawn only from bills with ≥1 local vote already**
   (a pool of 210 vote-bearing bills gathered from 40 random listing pages) — since most MI bills
   never reach a floor vote at all, sampling uniformly over the whole population mostly returns
   uninformative 0-vote bills; restricting to vote-bearing bills concentrates the signal.

## Result 1: all 8 original bills still show the exact same gap, unchanged, 8 days later

| Bill | Local votes | Live votes | Missing vote date | Chamber(s) | Roll Call # |
|---|---|---|---|---|---|
| HB 4023 | 1 | 2 | 2026-07-03 | Senate | 210 |
| HB 4187 | 1 | 3 | 2026-07-03 | House, Senate | 329, 205 |
| HB 4750 | 1 | 3 | 2026-07-03 | Senate, House | 197, 323 |
| HB 5233 | 1 | 2 | 2026-07-03 | Senate | 204 |
| HB 5249 | 1 | 2 | 2026-07-03 | Senate | 191 |
| HB 5697 | 1 | 3 | 2026-07-03 | House, Senate | 334, 208 |
| SB 205 | 2 | 3 | 2026-07-03 | Senate | 216 |
| SB 716 | 1 | 2 | 2026-07-03 | House | 303 |

**Every missing vote on every bill is dated 2026-07-03** — none of the original 8 have drifted
to a different vote-count gap or self-healed since 2026-07-28.

## Result 2: a fresh, independent sample reproduces the identical pattern at ~10x the rate

The unfiltered 60-bill sample found 1 gap (one of the original 8, re-drawn at random — consistent
with the original ~1.6%-of-all-bills rate, since most sampled bills have zero votes and can't show
this failure mode at all).

The targeted 90-bill sample (bills with ≥1 vote only) found **9 bills with the gap (10%)** — 8 of
them entirely new, not in the original list:

| Bill | Local | Live | Roll Call # | Chamber |
|---|---|---|---|---|
| SB 966 | 1 | 3 | 288, 223 | House, Senate |
| SB 105 | 1 | 2 | 302 | House |
| HB 4100 | 1 | 2 | 190 | Senate |
| SB 133 | 1 | 2 | 309 | House |
| HB 4101 | 2 | 3 | 312 | House |
| SB 418 | 1 | 3 | 300, 218 | House, Senate |
| HB 4208 | 1 | 2 | 203 | Senate |
| HB 4724 | 1 | 2 | 225 | Senate |

**All 9 bills' missing votes are also dated 2026-07-03** — 17 total missing-vote instances across
both samples, 17/17 on that one date, spanning House Roll Calls #288–334 and Senate Roll Calls
#190–225 (both wide, near-contiguous ranges within a single chamber's single day) across both
chambers. This is not scattered independent drift; it's one calendar day's floor session,
apparently a mass pre-recess passage day (immediately before the July 4th recess), that MI's
scraper has never once successfully captured a subset of roll calls from, on any bill, on any
scrape attempt since.

## AC1 answered: what's missing, and does it correlate with a documented WAF window?

**What's missing:** one calendar date, both chambers, dozens of roll-call votes (2026-07-03) — not
a specific vote *type* or *stage* (the affected roll calls are almost all "PASSED; GIVEN IMMEDIATE
EFFECT" / straightforward passage votes, same as the vast majority of MI's roll calls generally;
nothing about the motion type itself is unusual).

**WAF-window correlation: no direct match, but a related infrastructure incident lines up closely.**
OPEN-17/18/19 (Barracuda WAF blocking first documented/fixed) are dated 2026-08-01; OPEN-21/22/23
followed 2026-08-02/03 — a full month after 2026-07-03. So this gap does **not** fall inside any of
the specific, dated WAF-block windows those tickets record.

What does line up: `notes/mi-cams-headed-browser-spec-20260802.md` §3 records that **nightly/
secondary scrapes across every jurisdiction were down for 4 days, 2026-07-04→07-08**, due to a
`project_gui_agent_migration.md`-documented GUI-LaunchAgent-can't-reload-over-SSH incident —
starting the day immediately after MI's mass vote day. That's a plausible reason the *next*
scheduled catch-up scrape of 2026-07-03's votes didn't happen on the normal cadence. It doesn't by
itself explain permanence, though: `scrape_votes()` re-reads a bill's *entire* history table on
every single scrape, not just what's new since last time, so once nightly scrapes resumed
2026-07-08+, every subsequent successful bill-page scrape should have retried fetching that day's
roll-call documents again — and kept retrying, indefinitely, on every scrape since. The reason a
transient outage became a permanent, 33-day (and counting) gap is the code-level mechanism below.

## AC2 answered: a distinct gap, not the general staleness pattern — confirmed two co-existing problems on the same bills

**The general OPEN-19/21/22/23 pattern:** MI's live WAF/reputation block causes a scrape *attempt*
to fail outright (`scrape_bill()`'s main bill-page fetch throws `WafBlockDetected`, registered via
`MIWafCircuitBreakerMixin`, and if it happens 3 times in a row the whole scrape aborts) — so a bill
caught in this pattern shows **everything** frozen at whatever state it was in during the last
successful full scrape: title, latest_action, sponsorships, *and* votes, all stale together,
one-directionally (local always behind live).

**This ticket's finding is structurally different.** Per the original 2026-07-28 writeup, none of
the 8 bills showed a title/latest_action/sponsorship mismatch at that time — only votes were
affected. Re-checking today (2026-08-05) shows those *same* 8 bills' `latest_action` **now** lags
live too (e.g. HB 4023: local still "REFERRED TO COMMITTEE ON LOCAL GOVERNMENT", live already
"assigned PA 80'26 with immediate effect") — consistent with the general staleness pattern having
started affecting these bills sometime between 2026-07-28 and now, which lines up with OPEN-19's
2026-08-01 first documentation of active WAF blocking. **So there are two separate, independently-
timed problems visible on the same bills**: an old, narrow, vote-only gap dating to 2026-07-03 (this
ticket), and a newer, broad, all-fields staleness that only started in the last ~1-2 weeks (OPEN-19/
21/22/23's actual, ongoing subject).

**Code-level mechanism for the vote-only gap**, confirmed by reading
`openstates-scrapers/scrapers/mi/bills.py`:

- `scrape_votes()` (line 353) yields a `VoteEvent` only when `parse_roll_call()` (line 487) returns
  non-`None`.
- `parse_roll_call()` fetches a **separate, per-vote** journal HTM document via `mi_waf_get()`. On
  `scrapelib.HTTPError` or `WafBlockDetected`, it does this and nothing else (lines 497–501):
  ```python
  except (scrapelib.HTTPError, WafBlockDetected):
      self.warning(
          f"Could not fetch roll call document at {url}, unable to extract vote"
      )
      return
  ```
  A plain `self.warning(...)` log, then `return` (implicitly `None`) — silently dropping exactly
  that one vote, permanently, with no other signal anywhere.
- **This is the only WAF-sensitive fetch site in MI's scrapers that never registers with
  `MIWafCircuitBreakerMixin`.** `scrape_bill()`'s own main-page fetch (lines 233–251) and
  `events.py`'s fetch both call `_register_waf_block_or_abort()`/`_register_waf_success()` on every
  attempt — feeding the consecutive-block counter, the `ScrapeError` abort threshold, and (via
  OPEN-22) the sustained-pattern escalation history. `parse_roll_call()`'s catch block does none of
  that. A block (or any other failure matching those two exception types) hitting this one fetch is
  invisible to every piece of monitoring MI's WAF saga built.
- **Confirmed via git history that none of OPEN-17/18/19/21/22/23 ever touched this.** OPEN-23
  (2026-08-02, `6d32f78`) is the only one of those six commits that touches `parse_roll_call()` at
  all, and only to add the matched-User-Agent parameter to the request lambda — the
  `except (scrapelib.HTTPError, WafBlockDetected): ... return` catch/swallow itself is byte-for-byte
  unchanged since before the WAF saga began.
- **Confirmed via test coverage that this path has none.** `scrapers/mi/tests/test_bills.py`'s only
  WAF-related tests (`test_scrape_bill_skips_and_continues_below_threshold`,
  `test_scrape_bill_aborts_after_max_consecutive_blocks`,
  `test_scrape_bill_resets_counter_after_successful_fetch`) all exercise `scrape_bill()`'s circuit
  breaker exclusively; nothing calls `scrape_votes()` or `parse_roll_call()` at all.

This mechanism explains every observed feature of the finding: exactly one (or a handful of) votes
missing per affected bill, never more than the actual gap; other fields on the bill staying correct
independent of the vote gap (since the main-page fetch and the per-vote fetch are separate,
independently-fallible requests); the gap being permanent rather than self-healing despite (per the
07-28 snapshot) many successful rescrapes of the bill's main page in between; and the gap being
completely invisible to `MAX_CONSECUTIVE_WAF_BLOCKS`, `ScrapeError` aborts, or OPEN-22's escalation
history, since none of those ever see it happen.

**What this investigation could not confirm from this environment:** the exact reason the
2026-07-03 journal-document fetches specifically fail *every single time*, over 33 days and
presumably many scrape attempts, rather than eventually succeeding once on a lucky retry. This
sandbox has no route to `legislature.mi.gov` itself (would require a real Playwright session and
risks tripping the live WAF further) to inspect whether that day's journal HTML/links are
structurally different (e.g., a consolidated multi-bill journal entry format for an end-of-term
marathon day) or whether the underlying fetch is still actively WAF-blocked specifically for those
URLs. Recommended as the concrete first step for whoever picks up OPEN-30 below.

## Conclusion

**Distinct gap, not the general staleness pattern** — though very plausibly triggered by the same
underlying class of MI/`legislature.mi.gov` fragility (WAF and/or scrape-infrastructure reliability)
that OPEN-19/21/22/23 also stem from, and worsened by an unrelated, general (all-jurisdiction, not
MI-specific) 4-day scrape-infrastructure outage (2026-07-04→07-08) that happened to immediately
follow the affected vote day. The mechanism that turns a plausibly-transient miss into a permanent
one is specific to this ticket's finding and untouched by any MI WAF fix shipped to date:
`parse_roll_call()`'s silent, unregistered, never-retried swallow of per-vote-document fetch
failures.

## Recommendation

- **Close OPEN-28** — its AC (identify what's missing, correlate against WAF windows, determine
  same-vs-distinct root cause, document) is satisfied by this note.
- **Do not fold into OPEN-19/21/22/23** — the mechanism is genuinely different (a silently-swallowed
  per-vote fetch with no circuit-breaker registration, vs. those tickets' main-page-fetch blocking/
  rate-limiting/escalation work), and folding it in would bury a distinct, actionable code gap
  inside tickets already scoped and closed around a different problem.
- **File a new follow-up ticket ([OPEN-30](https://digitaldemocracyproject.atlassian.net/browse/OPEN-30), filed alongside this note)** for the actual fix: give `parse_roll_call()`'s except
  block the same `_register_waf_block_or_abort()`/`_register_waf_success()` treatment
  `scrape_bill()` and `events.py` already have, and/or stop silently returning `None` so a
  persistently-failing vote fetch becomes visible (a warning count, a retry-later queue, or at
  minimum a metric) instead of disappearing without a trace. Add test coverage for
  `scrape_votes()`/`parse_roll_call()`'s failure path — currently untested — as part of that fix.
- Given the mass-multi-bill shape of this finding (dozens of roll calls, one day, both chambers),
  a targeted one-time backfill of 2026-07-03's votes (once the underlying per-vote fetch issue is
  understood/fixed) is likely higher-value than waiting for organic re-scrapes, which have already
  had 33 days and haven't self-healed.

## Still open

- The exact byte-level reason 2026-07-03's journal documents fail every attempt (WAF-window vs.
  page-structure vs. something else) — needs real `legislature.mi.gov` access to confirm, out of
  scope for this ticket and this environment.
- Whether other single-day mass-vote gaps exist elsewhere in MI's 2025-2026 session (this
  investigation only found one date across 17 instances, but a targeted 90-bill sample doesn't rule
  out a second, rarer occurrence elsewhere in the session).
- [OPEN-30](https://digitaldemocracyproject.atlassian.net/browse/OPEN-30) — the new follow-up
  ticket for the `parse_roll_call()` fix itself, not yet implemented.

## References

- `PLAN-coverage-completeness-check.md` §14 (original finding), §15 (later related MI findings), §16
  (this conclusion)
- `notes/mi-tier2-500-bill-random-sample-20260803.md`, `notes/mi-tier2-250-bill-post-fix-sweep-20260803.md`
  — the original and post-fix Tier 2 runs that first surfaced the 8 bills
- `notes/mi-cams-headed-browser-spec-20260802.md` §3 — the 2026-07-04→07-08 nightly-scrape outage
- `openstates-scrapers/scrapers/mi/bills.py` lines 353 (`scrape_votes`), 487–501 (`parse_roll_call`),
  233–251 (`scrape_bill`'s contrasting circuit-breaker registration)
- `openstates-scrapers/scrapers/mi/_waf_circuit_breaker.py` — `MIWafCircuitBreakerMixin`
- `openstates-scrapers/scrapers/mi/tests/test_bills.py` — confirms no test coverage of
  `scrape_votes`/`parse_roll_call`
- Raw diff data: `logs/quality-check/mi_open28_original8_diff.json`,
  `logs/quality-check/mi_open28_broad60_sample.json`, `logs/quality-check/mi_open28_targeted90_sample.json`
  (this checkout)
- Jira: OPEN-28 (this ticket), OPEN-17/18/19/21/22/23 — MI's WAF-blocking history (related but
  distinct), [OPEN-30](https://digitaldemocracyproject.atlassian.net/browse/OPEN-30) — the
  `parse_roll_call` fix follow-up ticket filed alongside this note
