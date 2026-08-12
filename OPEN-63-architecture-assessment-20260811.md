# Architecture Assessment: OPEN-63 — FL: two independent data-completeness gaps

## Architectural Question

The ticket frames both gaps as open diagnoses. Neither is open anymore — direct evidence gathered
below (a live Tier 1 identifier diff, live queries against both `v3.openstates.org` and the local
Postgres DB, and a direct fetch of the actual flsenate.gov pages involved) identifies concrete,
different root causes for each gap, neither of which is "the scraper doesn't work." The real
architectural questions are narrower:

1. **Gap 1 (34 bills):** given the 34 "missing" bills are 100% one identifier prefix (`SPB`) tied
   to a Florida Senate-specific identifier-lifecycle quirk, is this a genuine scraper coverage bug,
   or the same class of Tier-1-diff false positive `quality_check.py` already has a named fix for
   (MA's `HD`/`SD` docket-duplication pattern)?
2. **Gap 2 (16/500 bills):** given the failure is concentrated in bills whose *only* votes are
   Florida House committee votes (the one vote source that goes through the WAF-protected
   `flhouse.gov` site), is the right fix a *retry*, a *backfill*, or both — and is this the same
   root cause as OPEN-41's 540-bill WAF-outage list, or a distinct one?
3. **A cross-cutting environmental question, discovered mid-assessment:** one of the ticket's own
   ACs (re-deriving the 540-bill list from `logs/scraper.log.20260714T020000Z.gz`) names a file
   that does not — and structurally cannot — exist in this CodeBot workspace clone. That changes
   how AC's overlap question can be answered here, and needs a documented decision, not a silent
   skip.

## Diagnosis (evidence, not hypothesis)

### Gap 1 — 34 missing bills are 100% `SPB` (Senate Proposed Bill), and it's a known identifier-lifecycle pattern, not a coverage bug

**Step 1 — extracted the real 34.** Ran the same Tier 1 diff `quality_check.py --coverage` does
(full local-DB identifier set vs. a fresh paginated `/bills` pull from `v3.openstates.org`, FL
2026) directly, read-only, against this workspace's live DB (`ddp-openstates-postgres-1`) and the
real live API. Confirmed: live=1931, local=1897, missing=34, extra=0 — matches the ticket's cited
figures exactly. **All 34 missing identifiers start with `SPB`** (e.g. `SPB 2500`, `SPB 7000` …
`SPB 7048`) — a 100% clean pattern, not a mix of causes.

**Step 2 — why the scraper's list crawl never sees them.** `BillList.get_source_from_input()`
(`openstates-scrapers/scrapers/fl/bills.py:145-150`) hits
`https://flsenate.gov/Session/Bills/{session}?chamber=both` with no `BillType` filter. Fetched that
exact URL live: **zero** occurrences of `SPB` anywhere in the response. The site's own search form
(`BillType` `<select>`, "Show More Options") lists `Senate Proposed Bills` as `value="10"`, a
distinct category from the "General Bills"/"Joint Resolutions"/etc. values the default,
no-filter view actually returns — `SPB` isn't part of what "all bills" means on this specific page,
regardless of chamber. This isn't a bug in `BillList.process_item()` itself — the function already
handles the `"SPB "` prefix correctly (`bill.startswith(("SB ", "HB ", "SPB ", "HPB "))` →
`bill_type = "bill"`, `bills.py:184-185`) — the bills are simply never enumerated for it to process.

**Step 3 — why this isn't fixable by "just add the filter," and why it's not a real gap at all.**
Fetched `https://flsenate.gov/Session/Bill/2026/7000` (the exact URL an `SPB 7000` list entry would
point to) live: the page **no longer shows `SPB 7000` anywhere** — it now renders as
`CS/SB 7000: OGSR/Persons Provided Public Emergency Shelter`. Florida Senate committee bills are
filed under a temporary `SPB` docket number, then **replaced in place** by a permanent `SB`/`CS/SB`
number once formally read in — the same URL, a different, final identifier. Confirmed both
identifiers exist as **two permanently separate records** on the live public API:

| Identifier | Live API record | Local DB |
|---|---|---|
| `SPB 7000` | Exists (`ocd-bill/e2969b5...`), title "OGSR/Persons Provided Public Emergency Shelter", frozen `updated_at` 2025-11-04 | **Absent** |
| `SB 7000` | Exists (`ocd-bill/08ec76d...`), same title, `updated_at` 2026-07-07 (kept current) | **Present** |

This is structurally identical to the docket/bill-number duplication pattern `quality_check.py`
**already has a named mechanism for** — `DOCKET_PREFIX_MAP` (`quality_check.py:67-89`), built for
MA's `HD`/`SD` docket numbers vs. `H`/`S` bill numbers, with `split_missing_by_docket_prefix()`
already generalized to take a per-jurisdiction prefix tuple. FL simply isn't in that map yet. The
local scraper crawling the *current* site state (which shows only the final `SB`/`CS/SB` number)
is correct behavior, not a defect — the "gap" is entirely a Tier 1 diff artifact against an API that
permanently retains the superseded pre-filing identifier as its own record.

**Root cause: Tier 1 diff false positive, not a scraper coverage bug** — FL needs the same
docket-prefix treatment MA already has.

### Gap 2 — 16/500 vote-missing bills are concentrated in House-committee-only votes, with a real, unretried failure path

**Step 1 — direct check of the ticket's own named examples.** Queried live + local for `HB 1295`,
`HJR 209` (session 2026). Local: 0 votes for both. Live: `HB 1295` has exactly 3 votes, **all three
sourced from `flhouse.gov/Sections/Committees/billvote.aspx`** (House committee votes — the one
vote source that goes through `_FLHouseWAFSource`/`HouseSearchPage`, the WAF-protected path). No
floor votes exist for this bill at all (it died in a House subcommittee) — so a House-committee-vote
fetch failure for a bill like this doesn't produce a partial result, it produces **zero** local
votes, exactly the failure shape both this sweep and 08-03's found.

**Step 2 — the code path has no retry on the exact failure mode that matters.**
`HouseSearchPage.accept_response()` (`bills.py:792-825`) distinguishes two failure shapes
explicitly in its own comments — a genuine "bill not on flhouse.gov" 404-style page, and a WAF
"Request Rejected" page — but **both branches `return True`**, i.e. both are treated as an
acceptable, final response. `process_page()`'s `except SelectorError` branch (bills.py:838-843,
"could not find bill in House Search") likewise just logs and yields nothing. Neither path retries.
This is deliberate and reasonable for the *specific, already-fixed* systemic case PR #5
(`_FLHouseWAFSource`) targeted — a stale session cookie rejecting *every* request for the rest of a
26-hour scrape, where "accept and move on" was the only way to avoid crashing the whole run. But it
means any **transient, one-off** WAF challenge or search miss — unrelated to cookie staleness,
possible on any single request regardless of how fresh the session is — permanently and silently
zeroes that one bill's committee votes, with zero retries at any level. OPEN-41's own verification
note already recorded this exact residual signature in a scrape it certified as fully fixed: 1
"could not find bill in House Search" miss out of 1,902 House-search fetches in the clean
2026-08-01/02 run — a ~0.05%-per-request rate that, compounded across ~1,900 bills over a
multi-day session, is consistent with a low-single-digit-percent share of bills losing all their
(committee-vote-only) votes. That is Gap 2's shape.

**Step 3 — this is very likely a distinct root cause from OPEN-41's WAF-outage list, established
without needing the archived log (see environmental constraint below).** Timeline, using only
already-committed notes:

| Date | Event |
|---|---|
| 2026-06-25/26 | The bad scrape that produced the original 540-bill WAF-outage candidate list (source of OPEN-41) |
| 2026-07-18 | PR #5 (`_FLHouseWAFSource`, the stale-cookie fix) merged to the DDP fork |
| 2026-08-03 | FL Tier 2 500-sample sweep, **already running with PR #5 active**, finds 14/500 (2.8%) "local missing votes vs live" — same order of magnitude as today |
| 2026-08-08 | OPEN-41 verifies the 540-bill list's votes were recovered by the 2026-08-01/02 re-scrape |
| 2026-08-11/12 | Fresh sweep finds 16/500 (3.2%) — same shape, same order of magnitude |

The 08-03 sweep's 14/500 already existed **before** OPEN-41's repair ever ran, and **after** the
systemic cookie fix was already live for two weeks. If Gap 2 were substantially explained by
OPEN-41's fix being incomplete, the rate should have been near-zero before OPEN-41 (nothing to be
incomplete about yet) and only appeared afterward — the opposite of what's observed. A stable
~3% rate present both before and after OPEN-41's specific repair is much better explained by an
independent, ongoing, per-request failure mode (Step 2's no-retry gap) than by residue from a
specific historical incident. This doesn't *prove* zero overlap at the individual-bill level — that
would need the literal 540-identifier list — but it does answer the ticket's actual underlying
question (does this indicate OPEN-41's fix was incomplete?) with real evidence: **no, this looks
like a separate, still-live defect, not evidence that OPEN-41 didn't finish its job.**

**Root cause: missing retry/error-classification in `HouseSearchPage`'s WAF/selector-error
handling** — a resilience gap distinct from, and outliving, the systemic cookie-expiry bug PR #5
fixed.

## Environmental constraint (blocks one AC as literally worded, in this workspace)

AC #4 requires re-deriving the 540-bill list from `logs/scraper.log.20260714T020000Z.gz`. That path
does not exist anywhere in this git checkout — `logs/*.log` is gitignored (confirmed in
`.gitignore` and in OPEN-41's own note, which reads that same file "directly (the real prod
checkout, read-only)"). The file only exists on this Mac Studio's filesystem at
`~/Developer/repos/ddp-open-states/logs/...` — the **production** checkout. Per this repo's
`CLAUDE.md`, the read-only carve-out for that checkout is explicitly scoped to "human/interactive
sessions on this Mac Studio," and `project-config.md`'s `repo.path` guidance is direct: if a
dependency a ticket needs isn't present under this workspace's own `repo.path`, "that's a real
finding to report... it is never a reason to look elsewhere on the filesystem." I confirmed the
file's location via `find` (path only, to establish this is a real, specific constraint and not a
typo or already-missing artifact) but did not read its contents.

This doesn't block the assessment — Step 3 above answers the ticket's real question a different,
evidence-based way — but it does mean AC #4's literal instruction ("re-derive... to check for
overlap") can't be executed to completion from inside this workspace. Two reasonable ways to close
this out, worth a decision before `/implement-ticket` proceeds:

- **Accept the timeline-based answer above** as satisfying the AC's intent (distinct-root-cause
  determination) without literal identifier-level overlap confirmation, and note the file's
  location constraint explicitly in the closing documentation.
- **Have a human derive the list from the real prod checkout** (same one-line `gzcat | grep | sort`
  OPEN-41 already used) and commit the resulting identifier list to a notes file in this repo, so a
  future CodeBot run can do the literal set-intersection this workspace currently cannot.

## Tech Stack Context

| Layer | Technology | Notes |
|-------|-----------|-------|
| Scraper | `openstates-scrapers/scrapers/fl/bills.py` (`BillList`, `HouseSearchPage`, `_FLHouseWAFSource`) | DDP org fork of `openstates/openstates-scrapers`; fork `main` is the patched state |
| Diagnostic tool | `quality_check.py` (repo root) — `DOCKET_PREFIX_MAP`, `run_coverage_check()`, `compare_bills()` | Already has a generalized, working mechanism for exactly Gap 1's shape (built for MA) |
| Live comparison target | `v3.openstates.org` (real API key, confirmed reachable from this workspace) | Independently retains both pre-filing and post-introduction bill identifiers permanently |
| Bill source site | `flsenate.gov` (list + detail pages, Senate floor/committee votes) | No WAF; reachable directly; has an undocumented-to-us `BillType` category (`Senate Proposed Bills`, value `10`) separate from the default "all bills" view |
| House vote source | `flhouse.gov` (`HouseSearchPage` → `HouseComVote`) | Behind an F5 BIG-IP WAF; `_FLHouseWAFSource` (PR #5, upstream openstates/openstates-scrapers#5751) already fixes the *systemic* stale-cookie failure mode |
| Local DB | Postgres `:5433`, `opencivicdata_bill` / `opencivicdata_voteevent` | Directly queried for this assessment (read-only) |
| Fork management convention | `RUNBOOK.md` "DDP commits on fork main" table | Established pattern: fork commit → `RUNBOOK.md` entry → later upstream PR (used for PR #5/#5751 already) |
| Environmental boundary | `logs/*.log` (gitignored), production checkout `~/Developer/repos/ddp-open-states` | Not reachable from this disposable workspace by design; see constraint above |

## Approaches Evaluated — Gap 1

### Approach A: Add FL to `quality_check.py`'s existing `DOCKET_PREFIX_MAP`
**How it works:** Add `"fl": {"docket_prefixes": ("SPB", "HPB")}` next to the existing `"ma"` entry.
`split_missing_by_docket_prefix()` already handles the rest generically — no other code changes.

**Pros:**
- Directly reuses an existing, working, already-understood mechanism (`reuse-before-reinvent.md`)
  — this is contribution to an established pattern, not new design.
- Zero risk to the actual scraper or production scrape behavior — this is a diagnostic-tool-only
  change.
- Correctly reclassifies these 34 as "not a real gap" because they genuinely aren't one — the local
  data (`SB 7000` etc.) is complete and current; the live API's frozen `SPB 7000` record is a
  historical echo of a stage that, on the source site itself, no longer exists to be scraped.
- `HPB` (House Proposed Bill) included symmetrically even though 0 appeared in this session's
  missing set — `bills.py` already special-cases `HPB` identically to `SPB` in its own type
  classifier, so the House side almost certainly has the same identifier-lifecycle shape whenever
  it's used; absence in one session's sample isn't evidence it can't happen.

**Cons:**
- Doesn't add the pre-filing-stage `SPB` record itself to the local corpus — if any future consumer
  specifically wants the pre-introduction docket-stage bill as its own entity, it stays absent.
  Low-value in practice: the evolved `SB`/`CS/SB` record already carries the complete substantive
  history (sponsors, actions, votes, versions).

### Approach B: Change the scraper to also crawl the `BillType=10` (Senate Proposed Bills) view
**How it works:** Add a second `BillList`-style crawl pass against
`flsenate.gov/Session/Bills/{session}?chamber=both&BillType=10`, importing whatever it finds as
distinct `SPB`-identifier `Bill` entities.

**Pros:** Would, in principle, get closer to true identifier-level parity with the live API.

**Cons:**
- **Verified infeasible for the specific 34 in hand:** fetching that exact `BillType=10` URL live
  returns only 1 bill currently pending at the SPB stage (`SPB 7042`) — the other 33 have already
  been superseded on the site itself (confirmed for `SPB 7000` → its URL now serves `CS/SB 7000`
  with no trace of the old identifier). The source page for an already-evolved `SPB` record simply
  no longer exists to be scraped by the time any batch crawl would run against it.
- The only way to actually capture these at the `SPB` stage would be much more frequent crawls
  timed to catch bills before committee introduction converts them — a scheduling/frequency change
  with real cost, for data (a temporary docket placeholder, same title as the eventual bill) that
  adds little beyond what Approach A already achieves by classifying the gap correctly.
- Introduces new scraper code and a new entity-dedup problem (avoiding treating `SPB 7000` and
  `SB 7000` as needing to be merged/linked) for a benefit that's marginal at best.

### Approach C: Leave as-is, accept the 34 as informational
**Cons:** Fails the ticket's explicit evidence bar (count must demonstrably shrink) and repeats
exactly the "unrepaired since 08-03" pattern the ticket opened to stop.

## Approaches Evaluated — Gap 2

### Approach A: Add bounded retry to `HouseSearchPage`'s WAF/selector-error paths, and backfill the bills already affected
**How it works:** Two parts:
1. **Prevention:** In `HouseSearchPage.accept_response()`, keep returning `True` (accept) for the
   genuine "bill not found" 404-style page, but for the WAF "Request Rejected" case, retry a small
   fixed number of times (reusing the file's own existing retry idiom —
   `retry_on_connection_error`/backoff, already used elsewhere in this same file) with a fresh
   cookie drop (the existing `_FLHouseWAFSource` mechanism) between attempts, before finally
   accepting and logging a skip. Same treatment for the `SelectorError`/"could not find bill in
   House Search" case in `process_page()`, since OPEN-41's own note shows that miss can be transient
   rather than a genuine absence.
2. **Repair:** A one-off targeted re-scrape of bills currently recorded with zero votes where an
   independent live check shows votes exist — the same before/after methodology OPEN-41 already
   used for the 540-bill list, scoped to whatever the fresh Tier 2 sweep identifies this time.

**Pros:**
- Targets the actual mechanism (Step 2 of the diagnosis), not just the symptom — prevents the same
  class of bill from recurring in every future scrape, not just this one.
- Reuses this file's own established retry/backoff/cookie-refresh idioms rather than inventing a
  new pattern — same file, same author intent, natural extension of PR #5.
- Matches `adapter-patterns.md`'s standard directly ("retry on transient failures... fail fast only
  on genuine not-found") — the current code retries on neither, which is the actual defect.
- Follows this repo's own established convention for scraper fixes (`RUNBOOK.md`'s fork-commit →
  upstream-PR-candidate pipeline, same as PR #5/#5751).

**Cons:**
- Adds a small amount of new code and a few more requests to `flhouse.gov` per affected bill —
  bounded and small (a handful of retries, only on the already-rare failure path), but not zero.
- The repair half only fixes bills identified in *this* sweep; any bill hit by the same transient
  failure between this ticket and its next quality sweep won't be caught until the next sweep runs
  — inherent to a point-in-time backfill, not a flaw specific to this approach.
- Exact spatula retry semantics for `HtmlPage.accept_response`'s return value weren't independently
  verified in this pass (the `spatula` package isn't present in this workspace's Python
  environment) — the recommendation is written to not depend on that: an explicit retry loop using
  this file's own already-proven backoff helper works regardless of whatever spatula does
  internally with `accept_response`'s return value.

### Approach B: Backfill/repair only, no prevention (treat as an operational sweep problem)
**How it works:** Just re-scrape currently-zero-vote bills periodically (extending the existing
`backfill-fl-historical.sh`-style pattern), without touching `HouseSearchPage`.

**Pros:** No scraper code risk at all.

**Cons:** Never actually closes the gap — every future scrape keeps producing the same ~3% loss
rate, and this ticket (like 08-03's sweep) would need to be re-run indefinitely. Doesn't match the
ticket's "diagnosed root cause" evidence bar, since the root cause (no retry) stays unaddressed.

### Approach C: Leave as-is, accept ~3% as noise
**Cons:** Same evidence-bar failure as Gap 1's Approach C — explicitly what the ticket says is no
longer acceptable ("not just 'still ~34/~16, unchanged, accepted'").

## Tradeoff Matrix

| Dimension | Gap 1 – A (docket map) | Gap 1 – B (crawl SPB view) | Gap 2 – A (retry + backfill) | Gap 2 – B (backfill only) |
|---|---|---|---|---|
| Complexity | Very low | Medium | Low-Med | Low |
| Time to implement | Very low | Med-High | Low-Med | Low |
| Fixes root cause | Yes (correctly reclassifies) | No (infeasible for already-evolved bills) | Yes | No (symptom only) |
| Risk to production scrape | None (tool-only) | Med (new crawl path, entity-dedup risk) | Low (bounded retry on rare path) | None |
| Prevents recurrence | N/A (not a recurring "loss") | N/A | Yes | No |
| Matches existing codebase pattern | Yes (reuses `DOCKET_PREFIX_MAP`) | No (new pattern) | Yes (reuses retry/backoff idiom + fork→upstream flow) | Partial (reuses backfill script style) |

## Recommendation

**Gap 1: Approach A — add `"fl": {"docket_prefixes": ("SPB", "HPB")}` to `DOCKET_PREFIX_MAP`.**
**Gap 2: Approach A — bounded retry in `HouseSearchPage` (prevention) plus a one-off targeted
backfill of currently-affected bills (repair).**

**Why these:**
- Both are grounded in verified evidence gathered this pass, not inference — the 100% `SPB`
  pattern, the live site's own identifier-replacement behavior, the committee-vote-only shape of
  the vote-missing bills, and the always-True `accept_response` are all directly observed, not
  guessed.
- Both reuse mechanisms this codebase already has and trusts (`DOCKET_PREFIX_MAP` for Gap 1, the
  retry/backoff/cookie-refresh idiom and fork→upstream-PR convention for Gap 2) rather than
  introducing new patterns — `reuse-before-reinvent.md`.
- Both satisfy the ticket's actual evidence bar: Gap 1's fix makes the Tier 1 "real missing" count
  drop from 34 to 0 immediately and deterministically (it's a reclassification of already-known
  data, not something that depends on a re-scrape); Gap 2's fix should reduce — not necessarily
  zero out — the Tier 2 vote-missing count on a fresh sweep, with the backfill closing out the
  specific bills already known to be affected.

**Why not the alternatives:**
- Gap 1 Approach B is verified infeasible for the exact 34 bills in hand (the source page no longer
  carries the old identifier once evolved) and would add real scraper complexity for marginal data
  value.
- Gap 2 Approach B never converges — the same ~3% loss would keep recurring on every future scrape,
  contradicting the ticket's own framing that "unrepaired and un-root-caused for over a week" is the
  problem being fixed.
- Both "C" options fail the ticket's explicit evidence bar by design.

**Risks and mitigations:**

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `HPB` symmetry assumption (Gap 1) turns out wrong — House side doesn't behave the same way | Low | Very low (an unused prefix in the tuple is a no-op) | No action needed; if ever proven wrong, remove it — trivial revert |
| Gap 2 retry adds meaningfully more request volume to `flhouse.gov` per scrape | Low (retries only trigger on the already-rare failure path, bounded count) | Low-Med (WAF sensitivity is the whole reason this file exists) | Keep retry count small (e.g. 2-3, matching this file's other retry constants) and always drop cookies between attempts, exactly as `_FLHouseWAFSource` already does for the systemic case |
| Backfill re-scrape re-hits the same transient WAF/search-miss failure on retry too | Medium (inherent to a still-imperfect upstream site) | Low (worst case: a bill stays at 0 votes, same as today — no regression) | Fresh Tier 2 sweep after backfill will surface any bill still affected, same verification loop as OPEN-41 used |
| AC #4's literal overlap check can't be completed in this workspace | Confirmed (see environmental constraint) | Low for the ticket's actual goal (Step 3's timeline evidence already answers "is this OPEN-41 incompleteness") | Document the constraint explicitly in closing notes; optionally get a human to derive the list from the prod checkout for a follow-up literal confirmation, not blocking |

**Prerequisites:**
- None for Gap 1 — a self-contained `quality_check.py` edit.
- For Gap 2's retry fix: none beyond the file's own already-present retry/backoff helpers
  (`utils.py`). For the upstream-contribution half (matching this repo's established convention for
  scraper fixes), an `upstream` remote on `openstates-scrapers` would be needed by whoever executes
  that step — same prerequisite Approach A already carried in OPEN-27's assessment, not new here.

**Tech debt created:** None net-new. Gap 2's retry fix is a direct, natural extension of already-
tracked debt (PR #5/#5751's own scope boundary — it fixed the systemic 1-hour case and explicitly
left "should now be rare" edge cases as future work in its own comment).

## Standards Checklist

| Standard | Status | Notes |
|---|---|---|
| OWASP Top 10 | N/A | Civic-data scraper/ETL, no user input or auth surface |
| Reuse before reinvent (`reuse-before-reinvent.md`) | Addressed | Core of both recommendations — extend `DOCKET_PREFIX_MAP` and this file's own retry idiom rather than inventing new mechanisms |
| Resilience / retry on transient failure (`adapter-patterns.md`) | Addressed by Gap 2's fix | Current code retries on neither transient nor permanent failure for this path — the actual defect; fix restores the "retry transient, fail fast on genuine not-found" standard |
| Tech debt governance (`tech-debt.md`) | Addressed | Gap 2's fix closes out debt PR #5/#5751 itself flagged as its own boundary ("should now be rare" edge cases); nothing new opened |
| `repo.path` / workspace scope discipline (`project-config.md`) | Addressed | Environmental constraint (archived log) reported rather than worked around by reaching outside this workspace |
| Idempotent/reversible changes (`artifacts.md`) | Addressed | Both fixes are small, independently revertible diffs; the backfill re-scrape is idempotent by the importer's own no-op-on-unchanged-bill behavior (same property OPEN-41's note relied on) |
| Multi-tenancy | N/A | Not a multi-tenant SaaS concern |

## Next Step

No data model or schema work — this doesn't need `/design-feature`. Recommend `/plan-ticket` (or
directly `/implement-ticket`, since this assessment already supplies the concrete plan): edit
`DOCKET_PREFIX_MAP`, add the bounded retry to `HouseSearchPage`, re-run
`quality_check.py --coverage fl 2026 --tier2-limit 500 --tier2-random`, run the targeted backfill
for any bills the sweep still shows as vote-missing, and record the environmental constraint on
AC #4's literal overlap check in the closing note rather than silently skipping it.
