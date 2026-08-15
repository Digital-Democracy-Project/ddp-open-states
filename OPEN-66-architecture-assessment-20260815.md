# Architecture Assessment: OPEN-66 — FL House committee votes missing where flhouse.gov shows no vote table

## Architectural Question

Given that live verification (below) shows the flhouse.gov markup has **not** drifted for the
two spot-checked bills, and the log line the ticket keys off is a red herring from an unrelated
code path — what is the right engineering approach to (a) find the actual mechanism dropping
these House committee votes, (b) make that failure mode observable instead of silent, and (c)
decide whether the fix is FL-specific or belongs in a shared pattern?

## Investigation findings (AC1)

**The ticket's own diagnostic evidence points at the wrong subsystem.** The log line quoted in
the ticket —

```
WARNING fl.bills.BillDetail: No vote table for HB 53
```

— comes from `BillDetail.process_votes()` (`openstates-scrapers/scrapers/fl/bills.py:452-493`),
which parses `//div[@id='tabBodyVoteHistory']//table` on the bill's **flsenate.gov** page (floor
votes + Senate committee votes). It has nothing to do with House committee votes, which are
fetched entirely separately via `HouseSearchPage → HouseBillPage → HouseComVote`
(`bills.py:748-959`), whose docstring says so explicitly: *"House committee roll calls are not
available on the Senate's website... This will fetch all the House committee votes for the given
bill."* Note also the `for/else` on line 452-493: that `else` binds to the outer `for vote_table
in vote_tables:` loop and — since nothing in the loop body ever executes `break` — fires on
*every* bill whose Senate page has an empty (or absent) `tabBodyVoteHistory` table, which is the
normal, expected case for a bill that only had House committee action. The correlation between
this warning and HB 53/HB 243 being in the missing-votes sample is very likely coincidental, not
causal.

**Live markup does not match the "structural/selector drift" hypothesis.** I fetched the actual
pages directly (curl, today, 2026-08-15) rather than trusting a browser-rendering summary — a
first pass via WebFetch's markdown conversion mis-reported the anchor text as the long
`aria-label` string, which would have been a false lead:

- `https://flhouse.gov/Sections/Bills/billsdetail.aspx?BillId=82591` (HB 53): contains
  `<a class="text" aria-label="See Votes for Economic Infrastructure Subcommittee..." href="/Sections/Committees/billvote.aspx?VoteId=76001&IsPCB=0&BillId=82591&">See Votes</a>` — the
  anchor's actual text node is exactly `"See Votes"`, matching `HouseBillPage.selector =
  XPath('//a[text()="See Votes"]/@href', min_items=0)` verbatim.
- The linked vote page (`billvote.aspx?VoteId=76001...`) has `lblYeas`/`lblNays`/`lblMissed`/
  `lblTotal`/`lblCommittee`/`lblAction`/`lblDate` spans exactly matching `HouseComVote`'s
  `contains(@id, "lbl...")` selectors (13-1-3, Favorable, Economic Infrastructure Subcommittee).
- `HB 243` (BillId=82769, found via `bills.aspx?Chamber=B&SessionId=113&BillNumber=243` — session
  113 per `scrapers/fl/__init__.py`'s 2026 Regular Session `session_number` extra) has **three**
  "See Votes" links, including one `IsPCB=1` (Proposed Committee Bill) vote. I fetched both an
  `IsPCB=1` and an `IsPCB=0` vote page for this bill and the label markup is structurally
  identical between them and identical to HB 53's — no PCB-specific drift either.

Across four live fetches (2 bill-detail pages, 2+ committee-vote pages), every selector
`BillDetail`/`HouseBillPage`/`HouseComVote` relies on matches the current markup exactly. This
doesn't rule out drift on some *other* bill in the 16-bill set, but it means AC1's premise
("markup has drifted or votes are located in a different section") does not hold for the two
bills the ticket names, and a code fix aimed at selector drift would fix nothing.

**The actual asymmetry: OPEN-63's WAF hardening only covers hop 1 of a 3-hop chain.** The House
vote path is three sequential HTTP fetches: `HouseSearchPage` (search by bill number) →
`HouseBillPage` (bill detail page, extracts "See Votes" links) → `HouseComVote` (the vote tally
page). `_FLHouseWAFSource` (`bills.py:722-745`) exists specifically because flhouse.gov's F5
WAF hands out a session cookie valid for ~1 hour, and a 26+ hour FL scrape run keeps presenting a
stale one — the class docstring says this stale-cookie WAF block happens "for *every* subsequent
request" once it starts. OPEN-63 added a bounded-retry `accept_response()` on top of that. But:

- Only `HouseSearchPage.get_source_from_input()` constructs its request via `_FLHouseWAFSource`
  (`bills.py:789`) and only `HouseSearchPage` overrides `accept_response` (`bills.py:801`, the
  *only* `accept_response` override in the entire `openstates-scrapers` tree — confirmed via
  `grep -rl "def accept_response"`).
- `HouseBillPage.process_item` and `HouseComVote`'s construction (`bills.py:869-871, 901-903`)
  both build their `source` via plain `URL(f"{item}", verify=False)` — no cookie drop, no WAF
  detection, no retry.
- Neither class logs anything when its expected content isn't found: `HouseBillPage.selector` has
  `min_items=0` (silently yields zero items), and `HouseComVote.process_page` only acts *inside*
  an `if len(...lblTotal...) > 0` guard with no `else` — if a WAF block page (or any other
  unexpected response) lands here, the bill simply gets no vote, no warning, no trace.

This means the exact stale-cookie/WAF condition OPEN-63 (and the pre-OPEN-63 cookie fix) hardened
hop 1 against can still happen, unfixed, at hops 2 and 3 — and it would produce *precisely* the
symptom described: page fetch logged as succeeding (HTTP 200 with a WAF block body), zero votes,
zero retry log lines, zero warnings anywhere in the House-vote code path. This is consistent with
the flat 16/455 → 16/480 rate surviving a fix that only touched hop 1.

## Tech Stack Context

| Layer | Technology | Notes |
|-------|-----------|-------|
| Scraper framework | `spatula` (via `openstates-scrapers`) | `HtmlPage`/`HtmlListPage`, `Source`/`URL`, `accept_response()` retry hook |
| HTTP/session | `scrapelib.Scraper` (subclasses `requests.Session`) | one persistent session per full scrape run (26+ hrs for FL) |
| Target site | flhouse.gov, behind F5 BIG-IP ASM WAF | ~1hr session-cookie TTL; "Request Rejected" block page served with HTTP 200 |
| Precedent pattern | `scrapers/mi/_waf_circuit_breaker.py` | `MIWafCircuitBreakerMixin` — shared, single-source-of-truth WAF-block counter reused across MI's bills/events/roll-call scrapers (OPEN-18, extended OPEN-22, OPEN-30) specifically to stop per-call-site drift |
| QA tooling | `quality_check.py` (`--coverage`, Tier 1 DB check + Tier 2 live-API diff) | Tier 2's "local" side hits a hardcoded shared `localhost:8002` api-v3 container regardless of `DATABASE_URL` — a real methodology trap for AC2's re-runs, flagged in the ticket itself |

## Approaches Evaluated

### Approach A: Copy the existing `HouseSearchPage` fix onto `HouseBillPage`/`HouseComVote`
**How it works:** Duplicate `accept_response`'s 404/WAF-title detection and bounded-retry logic,
and wrap `HouseBillPage`/`HouseComVote`'s sources in `_FLHouseWAFSource`, at each of the two
remaining hops — essentially three near-identical copies of the same ~70 lines.

**Pros:** Minimal to reason about per call site; matches the "just fix what's broken" instinct;
fastest to write.

**Cons:** This is literally the failure mode that created OPEN-66 in miniature — OPEN-63 fixed
hop 1 and the fix didn't reach hops 2/3, because the logic lived only in `HouseSearchPage`. Three
independent copies of "is this response a WAF block" is guaranteed to drift again the next time a
4th hop is added or the WAF's block-page markup changes (would need updating in 3 places).

**Standards alignment:** Fixes the immediate resilience gap but doesn't address the *systemic*
cause (duplicated, non-shared detection logic) — weak on DRY / single-responsibility for a piece
of logic that has already proven itself easy to apply inconsistently.

### Approach B: Extract shared WAF-detection/retry logic, apply uniformly across all 3 hops
**How it works:** Pull the "is this a `page-404` or `Request Rejected` block page" check and the
bounded-retry accept/reject decision out of `HouseSearchPage.accept_response` into a small shared
helper (module-level function or mixin) that all three page classes call from their own
`accept_response`. Switch `HouseBillPage`/`HouseComVote` to build their sources via
`_FLHouseWAFSource` (already generic — it just drops flhouse.gov cookies before any request, no
change needed there) instead of plain `URL`. Additionally, add explicit `logger.warning` calls on
the currently-silent empty-match paths in `HouseBillPage` (0 "See Votes" links after passing WAF
checks) and `HouseComVote` (no `lblTotal` span after passing WAF checks) so a genuine future
markup drift is *distinguishable in logs* from "WAF blocked, retried, gave up."

**Pros:** Directly closes the asymmetry that's the leading root-cause hypothesis; the shared
helper can't silently miss a hop the way three independent copies can; turns two currently-silent
failure paths into logged ones, which is exactly the observability AC2's "build a distribution"
step needs to be meaningful (right now, a genuine markup-drift miss and a WAF-drop miss are
indistinguishable in the logs — both just produce a missing bill with no error). Directly mirrors
an already-adopted, working precedent in this exact codebase (MI's `_waf_circuit_breaker.py`,
whose docstring explicitly documents *why* MI centralized this after hitting the same
one-call-site-at-a-time drift problem across OPEN-18/22/30).

**Cons:** Slightly more design work than Approach A — needs a shared function/mixin, small
migration of two call sites' source construction. Still FL-specific scope (no new cross-repo
abstraction), so this isn't over-engineering relative to the problem.

**Standards alignment:** DRY / single-responsibility for the WAF-detection concern; resilience
best practice (retry with bounded backoff, consistent across a multi-hop chain rather than
piecemeal); observability best practice (log the failure, don't let it disappear silently) —
directly addresses OWASP-adjacent resilience guidance around handling upstream anti-automation
defenses gracefully rather than degrading silently.

### Approach C: Diagnosis-only this ticket — instrument, re-run, defer any code fix
**How it works:** Treat OPEN-66 strictly as the investigation its acceptance criteria describe:
add logging only (no behavior change) at the currently-silent paths, script a repeatable N-run
harness around `quality_check.py --coverage fl 2026 --tier2-limit 500 --tier2-random` (working
around the Tier 2 shared-api-v3-container gotcha the ticket flags), and let the resulting
recur-vs-transient distribution + new log signal from hops 2/3 decide the real fix in a follow-up
ticket.

**Pros:** Lowest risk — no behavior change to a scraper that just had two rounds of fixes;
matches the ticket's own suggested-next-steps framing closely; produces harder evidence
(distribution across multiple independent runs) before committing to a fix shape.

**Cons:** Slower path to actually closing the vote gap; the code-inspection + live-fetch evidence
gathered for this assessment already narrows the hypothesis space enormously (asymmetric WAF
coverage, not markup drift) — deferring the WAF-coverage fix itself, when the fix is small and
low-risk (extending an already-proven pattern), leaves real votes missing for another cycle for
comparatively little additional certainty.

## Tradeoff Matrix

| Dimension | A: Duplicate fix | B: Shared WAF helper + logging | C: Diagnosis-only |
|-----------|-------------------|-----------------------------|--------------------|
| Complexity | Low | Low-Med | Low |
| Time to implement | Low | Low-Med | Low (this ticket) / defers real fix |
| Maintainability | Poor (3 copies) | Good (1 source of truth) | N/A (no fix yet) |
| Resilience to next hop added | Poor | Good | N/A |
| Observability | Fixes symptom, still silent-by-default elsewhere | Adds warnings at both silent paths | Adds warnings, no behavior fix |
| Risk of regressing a just-fixed scraper | Med (3 edits) | Med (2 edits + 1 extraction) | None |
| Alignment with codebase precedent | Repeats the OPEN-63 mistake shape | Mirrors MI's `_waf_circuit_breaker.py` precedent | Neutral |
| Answers AC2 (recur vs transient) | No | Partially (better logs make next distribution run diagnostic) | Yes, directly |
| Answers AC3 (FL-specific vs shared) | N/A | Confirms pattern precedent already exists (MI); no new cross-repo abstraction needed | Doesn't investigate further than confirmed-FL-only grep |

## Recommendation: Approach B (shared WAF-detection/retry helper across all 3 hops, plus explicit logging on both silent paths), preceded by AC2's multi-run sampling as verification

**Why this approach:** The investigation above (not just the ticket's own log evidence, which
turned out to be a red herring) narrows this to a specific, well-precedented gap: hop 1 of a
3-hop WAF-protected chain got OPEN-63's fix, hops 2 and 3 didn't, and both of the un-fixed hops
fail completely silently when they get an unexpected response. That's a resilience gap (no retry)
compounded by an observability gap (no log signal), and this codebase has already solved exactly
this shape of problem once, in MI's `_waf_circuit_breaker.py` — a shared, single-source-of-truth
module whose own docstring explains it exists *because* the fix-one-site-at-a-time pattern kept
needing extension (OPEN-18 → OPEN-22 → OPEN-30). Applying that lesson to FL rather than
re-learning it via a fourth ticket down the line is the stronger engineering call.

**Why not the alternatives:** Approach A reproduces the precise structural mistake that produced
this ticket — fixing the hop currently known to be broken while leaving the same class of bug
live at the other two hops, with no mechanism to prevent it recurring. Approach C is defensible
(and its diagnostic groundwork — the multi-run sample per AC2 — should still happen), but given
how far the code-level evidence already goes (confirmed markup match on 4 live pages, confirmed
single-`accept_response`-override-in-the-repo via grep, confirmed identical asymmetric-coverage
pattern already fixed once in MI), treating this as still-unknown and only instrumenting further
underuses the evidence already in hand.

**Risks and mitigations:**

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Hypothesis is wrong and some of the 16 bills are genuine markup drift, not WAF hits | Med | Med | AC2's multi-run sample, now with hop 2/3 logging in place, will show *which* bills recur and whether their logs show a WAF/retry signature or true selector silence — run this before declaring the fix complete |
| Shared helper over-generalizes beyond what HouseSearchPage's retry semantics actually need (its "has_results" empty-search heuristic doesn't apply to HouseBillPage, where zero "See Votes" links is a legitimate, common, non-error state) | Med | Low | Keep the WAF/404-page detection (title/div check) in the shared helper; keep each page's own "is an empty result actually suspicious here" judgment call local to that page's `accept_response`, not folded into the shared piece |
| Retrying hops 2/3 adds scrape wall-clock time across ~1900 bills | Low | Low | Reuse the same bounded `HOUSE_SEARCH_MAX_ATTEMPTS`-style budget (3 attempts) already proven acceptable for hop 1 |

**Prerequisites:**
- Run AC2's repeated 500-bill sampling (ideally after the logging half of Approach B lands, even
  before the retry half) to convert "16 missing, unknown cause" into a bill-by-bill log trail —
  this is cheap, additive, and de-risks the fix regardless of which approach is chosen.
- Work around the Tier 2 `LOCAL_API` gotcha the ticket documents (shared `localhost:8002`
  container ignores `DATABASE_URL`) — either stand up a second api-v3 container against the
  scrape's own DB (the ticket notes a Colima host-port issue was hit last time; may be worth a
  fresh attempt or an alternate port-forwarding approach) or keep cross-checking the "local" side
  directly via SQL as was done for OPEN-63's round-3 verification.

**Tech debt created:** None net-new. If anything this pays down debt (the duplicated-detection-logic
gap already present since `HouseSearchPage`'s `accept_response` was added in isolation).

## AC3: FL-specific or shared pattern?

Confirmed via `grep -rl "def accept_response" openstates-scrapers/scrapers` — `HouseSearchPage`
in `scrapers/fl/bills.py` is the *only* `accept_response` override anywhere in
`openstates-scrapers`. No other jurisdiction currently has WAF-retry logic at the `spatula` Page
level, so there is no existing sibling bug to fix elsewhere right now. The relevant precedent
instead lives one layer up, in `scrapers/mi/_waf_circuit_breaker.py` — a different mechanism
(consecutive-block circuit breaker at the `Scraper` level, not a per-`Page` `accept_response`
retry) solving a structurally similar problem (a WAF-block detector that needs to apply
consistently across multiple call sites within one jurisdiction, not per-call-site duplication).
This is evidence *for* Approach B's shape being the right one for this codebase, not evidence
that other jurisdictions need a fix today. Worth a follow-up note (not this ticket's scope): if a
third jurisdiction ever needs WAF handling, there may be a case for a genuinely shared
`openstates-scrapers`-level utility rather than a second bespoke per-jurisdiction implementation —
premature to build now with only two data points (FL, MI), each already using a different
mechanism shape for good reasons specific to their own call-site structure.

## Standards Checklist

| Standard | Status | Notes |
|----------|--------|-------|
| OWASP Top 10 | N/A | No user input, no auth, no data exposure surface in this scraper code path |
| SOLID principles | Addressed | Approach B centralizes the WAF-detection responsibility instead of duplicating it across 3 classes |
| 12-Factor | N/A | Not a service; the adjacent `quality_check.py` LOCAL_API hardcoding is a real config-as-constant smell but is a separate, pre-existing issue outside this ticket's scope |
| Resilience (retry/backoff, graceful degradation) | Addressed | Approach B extends the already-proven bounded-retry pattern to the two currently-unprotected hops |
| Observability (logging, tracing) | Addressed | Approach B adds warnings on both currently-silent empty-result paths, closing the gap that made this bug indistinguishable from a benign "no votes yet" case |
| Idempotent migrations | N/A | No schema/migration involved |
| Multi-tenancy | N/A | Not a multi-tenant system |

## Next Step

This is scraper-code-level remediation with a fairly narrow, well-scoped surface (2 classes, ~2
call sites) — `/plan-ticket` can go straight to an implementation plan from here without needing
`/design-feature`'s data-model/architecture treatment first.
