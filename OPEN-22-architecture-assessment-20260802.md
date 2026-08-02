# Architecture Assessment: OPEN-22 — MI scraper: detect and escalate a sustained (multi-week) blocking pattern

## ⚠️ Scope finding — read before the rest of this document

**This ticket spans two repositories, and only one of them is present in this workspace.**

This workspace is a clone of `ddp-open-states` (remote: `Digital-Democracy-Project/ddp-open-states`,
default branch `main`). It contains `openstates-scrapers/` and `openstates-core/` — the scraper
codebase — but **does not contain `ddp-sync`**, confirmed by:

```
find . -iname "openstates_scrape.py"   → no results
find . -iname "redis_store.py"         → no results
grep -rn "flow_status|ddp:flow:" .     → no results
git remote -v                          → origin only points at ddp-open-states
```

Everything the ticket calls out — `run_secondary_scrapes_job`, `_alert_scrape_failure`,
`_write_flow_status`/`set_flow_status`/`get_flow_status`, `scheduler.py` — lives in `ddp-sync`,
per the ticket's own file references (`src/ddp_sync/pipelines/openstates_scrape.py`,
`redis_store.py`, `scheduler.py`). That repo is not checked out anywhere in this workspace, and
per `project.toml`/`project-config.md`'s rule, a similar-looking checkout elsewhere on the
machine (if one exists) is never a substitute for this ticket's actual `repo.path` — it would
belong to a different session/workspace entirely.

**Practical consequence:** of this ticket's 8 acceptance criteria, **AC0, AC0b, AC1, AC2, AC3,
AC4, and AC5 (the Redis rolling-window history, failure classification, escalation check, and
their unit tests) cannot be implemented from this workspace** — there's no file to edit. Only
**AC7 (MI-events WAF circuit-breaker parity)** targets code that actually exists here
(`openstates-scrapers/scrapers/mi/events.py`).

This document still delivers a full architectural recommendation for *all* the ACs, reasoned
from the code excerpts, line numbers, and behavior the ticket description itself documents in
detail (which is precise enough to design against even without a local checkout) — but the
`ddp-sync`-side recommendation is a **handoff spec for a `ddp-sync`-scoped session**, not
something this session can build. See "Next Step" at the end.

---

## Architectural Question

Two sub-questions, one per repo this ticket touches:

1. **(ddp-sync)** How should per-jurisdiction run history, failure classification, and
   sustained-pattern escalation be added on top of the existing single-value Redis flow-status
   primitive and per-run alerting, without destabilizing other consumers of that primitive?
2. **(ddp-open-states)** Should `MIEventScraper` get the same consecutive-WAF-block circuit
   breaker `MIBillScraper` has (OPEN-18), and if so, how, without duplicating the
   counter/threshold/raise logic?

## Tech Stack Context (this workspace)

| Layer | Technology | Notes |
|-------|-----------|-------|
| Scraper framework | `openstates-core` (pupa/OCD-derived) | `Scraper`, `ScrapeError`, `EmptyScrape` from `openstates.exceptions`/`openstates.scrape` |
| MI WAF handling | `openstates.utils.cookie_provider.WafBlockDetected`, `openstates.utils.mi_cookies.MI_COOKIE_PROVIDER` | Shared cookie-attach + one-retry contract via `mi_waf_get()` (`scrapers/mi/bills.py:59-93`), used identically by `bills.py`, `events.py`, `__init__.py` |
| Test framework | pytest, `monkeypatch` | See `scrapers/mi/tests/test_waf_get.py` |
| Circuit breaker precedent | `MIBillScraper._consecutive_waf_blocks` (instance attr) + `MAX_CONSECUTIVE_WAF_BLOCKS = 3` module constant | `scrapers/mi/bills.py:107,159-172` |

**Not present here (ddp-sync, per ticket description only):**

| Layer | Technology | Notes |
|-------|-----------|-------|
| Orchestration | APScheduler | Weekly Sunday 02:00 UTC job, `scheduler.py:561-585` |
| State store | Redis | `set_flow_status`/`get_flow_status`, plain SET/GET, `ddp:flow:<name>` key, 7-day TTL (`redis_store.py:271-299`) — same shared Redis this repo's `PRIMITIVES.md` documents (`ddp-agents-redis-1` / `ddp-agents_default` network) |
| Alerting | Slack (`#automation-errors`) + CAMS `POST /api/v1/failures` | `_alert_scrape_failure()`, `openstates_scrape.py:47-101` |

---

## Sub-question 1 (ddp-sync): rolling history, classification, escalation

### AC0 — rolling window storage

**Approach A: Redis List (RPUSH + LTRIM)**
Append a JSON record per run to `ddp:flow:<name>:<jurisdiction>:history`, `LTRIM` to keep the
last N (some headroom above the 3–4 actually checked, e.g. 10), refresh `EXPIRE` on each write.
Read with `LRANGE`.

**Approach B: Redis Sorted Set (ZADD, score = run timestamp)**
Same data, keyed by score instead of insertion order; trim with `ZREMRANGEBYRANK`.

**Approach C: Redis Stream (XADD, MAXLEN ~N)**
Purpose-built for capped append-only history with consumer semantics.

| Dimension | List (A) | Sorted Set (B) | Stream (C) |
|-----------|----------|-----------------|------------|
| Complexity | Low | Low-Med | Med-High |
| Fit with existing primitive | High — same plain-command style as current SET/GET | Medium | Low — introduces a new Redis data model to the codebase |
| Concurrency safety | Fine for a single weekly APScheduler job per jurisdiction (no concurrent writers) | Fine, and dedups-by-timestamp for free | Fine, but overkill (no consumer groups needed) |
| Read-back for "last N" | `LRANGE` trivial | `ZRANGE` trivial | `XRANGE` trivial but heavier API surface |

**Recommendation: Approach A (Redis List, RPUSH/LTRIM/EXPIRE).** It's the smallest structural
delta from the existing plain SET/GET convention (`reuse-before-reinvent`: don't introduce a new
Redis pattern — Streams or sorted-set scoring — when a capped list satisfies every requirement
here), there's no concurrent-writer race to guard against (one weekly job, sequential
jurisdictions), and "last N" read-back is a single `LRANGE(-N, -1)`.

**Real risk to flag, not just an implementation note:** `set_flow_status`/`get_flow_status` are
described as a *generic* primitive — the ticket doesn't say they're private to the secondary-
scrapes job, and this workspace has no way to grep `ddp-sync` for other callers. Changing their
write path in place risks silently changing behavior for every other flow that calls them today.

**Recommend an additive, narrowly-scoped change instead of an in-place rewrite:** introduce a
new function (e.g. `append_run_history(flow_name, jurisdiction, record, max_len, ttl)` /
`get_run_history(...)`) that the secondary-scrapes job calls in addition to (not instead of) the
existing single-value `set_flow_status` call — leaving every existing caller of
`set_flow_status`/`get_flow_status` completely untouched. This satisfies AC0's intent (a rolling
window becomes available) with a much smaller blast radius than modifying the shared primitive
directly, and it's a decision that specifically needs someone with real `ddp-sync` visibility to
confirm (grep for other `set_flow_status(` call sites) before committing to either path — flag
this explicitly to whoever picks up the `ddp-sync` side.

### AC0b — failure classification

**Approach A: Substring/keyword match against `stderr_tail`, scoped to first-party message strings**
Classify by checking `stderr_tail` for the *exact* strings this same codebase controls — e.g.
OPEN-18's own `ScrapeError` message text, `"consecutive WAF blocks detected"` /
`"legislature.mi.gov is likely blocking"` (`scrapers/mi/bills.py:168-171`) — plus exit-code/signal
facts already available in `_run_scrape` (timeout, killed-by-signal) classified without any
string matching at all.

**Approach B: Custom subprocess exit codes per category**
Have `run-scrape.sh`/the scraper distinguish WAF-block failures from other failures via a
dedicated exit code (e.g. 2 = WAF block, 1 = other), instead of parsing text.

**Approach C: Structured JSON error footer on stdout**
Scraper emits a machine-readable JSON marker on failure; `_run_scrape` parses that instead of
`stderr_tail`.

| Dimension | Substring match (A) | Custom exit codes (B) | JSON footer (C) |
|-----------|---------------------|------------------------|-------------------|
| Blast radius | None — only touches the classification function in `openstates_scrape.py` | Touches `run-scrape.sh`'s `on_failure()` trap and exit-code contract shared by *every* jurisdiction, not just MI | Touches every scraper's failure path to emit the footer |
| Robustness | High, if scoped to exact first-party strings (not generic regex over arbitrary prose) | High once built, but high change cost | High, but highest change cost |
| Time to implement | Low | Medium-High | Medium-High |

**Recommendation: Approach A, but scoped precisely** — match against the literal message text
`ScrapeError` already raises in `scrapers/mi/bills.py:168-171` (a string this same GitHub org
controls and versions, not arbitrary third-party prose), plus exit-code/signal semantics
`_run_scrape` already has on hand. This is *not* the kind of "regex parser over free-form text"
`reuse-before-reinvent.md` warns against — that guidance is about extracting structured meaning
from genuinely unstructured human-authored text; here the string is a stable, first-party
constant. Approaches B/C solve the same problem more robustly in the abstract but change a
shared contract (`run-scrape.sh`'s exit-code semantics, or every scraper's stdout contract) used
by VA/MA/UT/AZ too — disproportionate blast radius for what AC0b actually needs.

### AC1–AC3 — escalation check and streak state

**Approach A: Stateless — recompute from the rolling window every run**
No separate "current streak" counter key. Each run, pull the last N records from AC0's history,
count how many are `waf_block`-classified, compare to the (N, M) config threshold, decide
whether to fire the escalation alert.

**Approach B: Stateful — maintain an explicit streak counter**
A separate Redis key tracks "current consecutive bad run count," incremented/reset on each
outcome, independent of the history list.

| Dimension | Stateless (A) | Stateful (B) |
|-----------|----------------|----------------|
| Sources of truth | One (the history list) | Two (history list + streak counter) — can drift |
| AC5 ("recovered run resets streak cleanly") | Falls out for free — a success in the window changes the ratio automatically | Requires an explicit reset branch that must be tested for correctness |
| Complexity | Lower | Higher |

**Recommendation: Approach A.** AC5's "clean reset" requirement is trivially satisfied by a
stateless design (no second piece of state to forget to reset), and it avoids exactly the kind
of duplicate-state-machine risk `reuse-before-reinvent.md` flags. Implement as a pure function
`should_escalate(history: list[RunRecord], window: int, threshold: int) -> bool` that's trivially
unit-testable in isolation (this directly enables AC6's three required test cases without any
Redis mocking).

### AC4 — config, not hardcoded

Place `(N, M)` alongside the existing `secondary.enabled` group config (ticket confirms that flag
already exists) — e.g. `secondary.escalation.window_size` / `secondary.escalation.threshold` —
consistent with 12-Factor config externalization and the existing config surface.

### Alerting

New `_alert_sustained_block()` function alongside the existing `_alert_scrape_failure()`
(`openstates_scrape.py:47-101`), reusing the same Slack channel/webhook plumbing (don't
introduce a second secret/webhook for what is still `#automation-errors`) but with distinctly
worded copy per AC2, so it's visually distinguishable in the channel from a per-run failure.

---

## Sub-question 2 (ddp-open-states): AC7 — MI-events WAF parity

Confirmed directly in this workspace: `MIEventScraper` (`scrapers/mi/events.py`) calls
`mi_waf_get()` at two call sites (`scrape()` line 20, `scrape_event_page()` line 37) and neither
catches `WafBlockDetected` — an events run crashes uncounted on the very first block, unlike
`MIBillScraper.scrape_bill()` which counts to `MAX_CONSECUTIVE_WAF_BLOCKS = 3` before raising
`ScrapeError`.

**Approach A (preferred, matches ticket's stated preference): extract a shared helper**
Pull the counter/threshold/raise pattern (`scrapers/mi/bills.py:107,159-172`) into a small shared
primitive — e.g. a tiny class or a `count_and_maybe_abort(scraper, exc, label)` function in
`bills.py` (or a new `scrapers/mi/_waf_breaker.py`) — imported by both `MIBillScraper` and
`MIEventScraper`.

**Approach B: duplicate the ~10-line pattern directly into `MIEventScraper`**
Copy `_consecutive_waf_blocks` + the threshold check + the `ScrapeError` raise into both
`scrape()` and `scrape_event_page()`.

**Approach C: document events as explicitly out of scope, leave it uncovered**
The ticket's fallback option — valid, but the ticket states A is preferred, and the codebase
already has a stated precedent for *not* doing this (the `mi_waf_get()` docstring: "the
attach-cookies + invalidate-and-retry-once contract lives in exactly one place" — the same
one-source-of-truth argument applies to the counting+abort contract, especially since OPEN-18's
own `USER_AGENT` comment already documents a prior instance of exactly this kind of drift risk
across duplicated constants).

| Dimension | Shared helper (A) | Duplicate (B) | Document-only (C) |
|-----------|--------------------|-----------------|----------------------|
| DRY / drift risk | Low — one `MAX_CONSECUTIVE_WAF_BLOCKS`, one raise message | High — two copies of the same constant/logic to keep in sync | N/A — no code change |
| Effort | Low-Medium (small refactor of `bills.py` + wire into `events.py`) | Low | None |
| Parity with OPEN-18/OPEN-21 (ticket's own stated goal) | Full | Full | None — leaves the exact gap the ticket calls out |
| Fixes the two-call-site nuance in `events.py` (`scrape()` + `scrape_event_page()` both need it) | Yes, by construction | Only if both sites are remembered | N/A |

**Recommendation: Approach A.** Extract the counting/threshold/raise logic once, use it at both
`events.py` call sites and in `bills.py`'s existing site. This is a small, low-risk refactor
(same behavior, same threshold, same exception type) that removes the exact kind of
duplicated-constant drift risk this codebase has already been burned by once (the `USER_AGENT`
comment in `bills.py:41-44` documents that history explicitly).

---

## Recommendation Summary

| AC | Repo | Recommended approach |
|----|------|------------------------|
| AC0 | ddp-sync | Additive Redis List (RPUSH/LTRIM/EXPIRE) history function, new key, existing `set_flow_status` untouched |
| AC0b | ddp-sync | Substring match against first-party `ScrapeError` message text + exit-code/signal facts already on hand |
| AC1–3 | ddp-sync | Stateless `should_escalate()` pure function recomputed from history each run |
| AC4 | ddp-sync | New config keys alongside `secondary.enabled` |
| AC5 | ddp-sync | Falls out of the stateless design in AC1–3 |
| AC6 | ddp-sync | Unit tests against the pure `should_escalate()` function — no Redis mocking needed |
| AC7 | ddp-open-states | Extract shared counter/threshold/raise helper, use at both `MIEventScraper` call sites and the existing `MIBillScraper` site |

**Why not the alternatives, in this specific context:** every "B/C" option above trades a small
increase in robustness for a change to a *shared* contract (the generic Redis flow primitive
used by potentially many flows; `run-scrape.sh`'s exit-code semantics used by every jurisdiction;
duplicated logic across two MI scraper classes that already drifted once before). Given this is
an escalation/visibility feature, not a correctness-critical path, the lower-blast-radius option
is the right call in every case.

**Risks and mitigations:**

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `set_flow_status`/`get_flow_status` has other callers this workspace can't see | Medium (generic-sounding primitive name) | High if broken (affects other flows' status reporting) | Use the additive new-function approach (above); have the `ddp-sync` session grep for other callers before touching the shared primitive |
| Classification substring match goes stale if OPEN-18's `ScrapeError` message text changes | Low-Medium | Medium (AC0b silently misclassifies) | Keep the matched string as a named constant co-located with (or imported from) `bills.py`'s `MAX_CONSECUTIVE_WAF_BLOCKS`/raise site, not a magic string re-typed in `ddp-sync` |
| AC7's shared-helper refactor changes `MIBillScraper`'s existing behavior by accident | Low | Medium (regression on a scraper already fixed once by OPEN-18) | Extract with existing `bills.py` unit-test-equivalent coverage extended to cover the shared helper directly, run full `mi` test suite before/after |

**Prerequisites:**
- A `ddp-sync`-scoped workspace/session (or ticket split) to actually implement AC0, AC0b,
  AC1–AC6 — none of that code exists in this checkout.
- Confirmation (from someone with `ddp-sync` visibility) of whether `set_flow_status`/
  `get_flow_status` have callers beyond the secondary-scrapes job, to finalize whether the
  additive-function approach or an in-place change is safe.

**Tech debt created:** None inherent to the recommended approach. If Approach C is chosen for
AC7 instead (events left uncovered), that is itself a tracked, documented gap per the ticket's
own framing — not silent debt, since AC7 requires it be stated explicitly either way.

## Standards Checklist

| Standard | Status | Notes |
|----------|--------|-------|
| OWASP Top 10 | N/A | No new user input, auth, or external-facing surface introduced |
| Resilience — Circuit Breaker pattern | Addressed | AC7 extends the existing per-run circuit breaker (OPEN-18) to `MIEventScraper`; AC1–3 add a second, coarser-grained breaker across runs (escalation, not auto-skip — AC skips this deliberately per the ticket's own scope note) |
| 12-Factor config | Addressed | Thresholds (N, M) externalized as config, not hardcoded (AC4) |
| Single source of truth / DRY | Addressed | Shared helper for AC7 avoids the exact duplicated-constant drift this codebase already documented once (`USER_AGENT`) |
| Blast-radius minimization | Addressed | Additive Redis function instead of in-place rewrite of a possibly-shared primitive |
| Testability | Addressed | Stateless `should_escalate()` design makes AC6's three test cases pure unit tests, no Redis/mocking required |

## Next Step

This workspace (`ddp-open-states`) can proceed straight to `/plan-ticket` **for AC7 only** —
that's fully actionable here. For AC0, AC0b, AC1–AC6, the work needs to happen in a `ddp-sync`
checkout/workspace; recommend either splitting OPEN-22 into two tickets (one per repo) or
explicitly noting in Jira that this ticket's implementation will land as two separate PRs across
two repos. I'd suggest confirming that split with you before either `/plan-ticket` run proceeds,
since it changes what "done" means for this ticket number.
