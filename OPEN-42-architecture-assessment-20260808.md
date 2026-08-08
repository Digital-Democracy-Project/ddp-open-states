# Architecture Assessment: OPEN-42 — MA full backfill + identifier-coverage anomaly — replica routing gate

## Architectural Question

Three of this ticket's five ACs (backfill completes, 162-bill gap closes, identifier anomaly
resolved) sit downstream of defects the plan docs have **already root-caused but not yet fixed**
(`PLAN-coverage-completeness-check.md` §10/§13, this repo). The real question isn't "how do we run
a backfill" — `backfill-fl-historical.sh` is an existing, working pattern for exactly that — it's:
**given three known-but-unfixed defects that directly threaten AC1/AC2/AC3, how much of that fix
work belongs inside this ticket's own scope (as code, before the backfill is attempted) versus
being deferred to a bare retry-and-hope operational run, and should the identifier-coverage fix be
MA-specific or a general `quality_check.py` capability?** A secondary, cross-cutting concern: this
ticket's five ACs split across code (fixable here), production operations (not executable from this
workspace), and a different repo's docs (`ddp-infra`, not `ddp-open-states`) — the assessment below
scopes each accordingly rather than treating "the ticket" as one homogeneous unit of work.

## Tech Stack Context

| Layer | Technology | Notes |
|-------|-----------|-------|
| Scraper framework | `openstates-core` (pupa-based), Poetry-installed | `cli/update.py:108-125`: `do_scrape()` falls back to every `active_sessions` entry when no `session=` arg is passed — confirmed deliberate for VA/UT (two simultaneous active sessions each), harmless-if-redundant for MA (one active session, `194th`) |
| MA scraper | `openstates-scrapers/scrapers/ma/bills.py` | Per-bill HTML scrape (`scrape_bill`, line 169) + AJAX cosponsor/action fetches (`get_as_ajax`, line 564) + PDF roll-call parsing (`scrape_senate_vote`, line 515) |
| Coverage tool | `quality_check.py` (repo root), single-file CLI, `psycopg2` + `requests`, no framework | `run_coverage_check()` (line 563): Tier 1 identifier-set diff (`missing = public_ids - local_ids`, line 581) + Tier 2 sub-record diff on the intersection |
| Local DB | Postgres, OCD schema (`opencivicdata_bill`, `opencivicdata_legislativesession`, `opencivicdata_jurisdiction`) | `fetch_all_local_identifiers()` (`quality_check.py:136-156`) is the local side of the Tier 1 diff |
| Scheduler | `ddp-sync`'s `run_secondary_scrapes_job()` (a separate repo, `ddp-sync/src/ddp_sync/pipelines/openstates_scrape.py:589-608`) | Confirmed (§11/§12 below) this — not `run-all-scrapes.sh` in this repo — is the actual production driver for MA's weekly scrape |
| Backfill precedent | `backfill-fl-historical.sh` (this repo) | Hardcodes prod path `/Users/agentsmith/Developer/repos/ddp-open-states`, runs `run-scrape.sh <state> "session=<id>"` sequentially per session, detached via `nohup`, resumable via `logs/last-run/<state>_session_<id>.ts` markers |
| Tests | `test_quality_check.py` (repo root) | Plain `pytest`, fakes for `conn`/`cursor` — no live Postgres/API needed; the Tier 1 diff logic (pure set arithmetic) is equally testable this way |

## Grounding: what the plan docs already established (read before proposing anything new)

This ticket's own ACs quote stale numbers in two places — worth stating plainly since it changes
what "fixed" means for AC1-AC3:

1. **§10 (`PLAN-coverage-completeness-check.md:257-401`, 2026-07-28) already broke MA's identifier
   gap down by prefix once**, against a then-current snapshot: `H` gap 61, `S` gap 101 (**~162
   real**, matching this ticket's own headline number), `HD` gap 4,765, `SD` gap 2,656 (~7,421
   docket-duplicate noise). Root cause confirmed directly against `v3.openstates.org`: MA's docket
   number (`HD`/`SD`, assigned at filing) and bill number (`H`/`S`, assigned once read in) are two
   *separate, permanent* upstream records for the same bill; our scraper (`ma/bills.py:171`:
   `bill_id = row["BillNumber"] or row["DocketNumber"]`) deliberately keeps only one, so a naive
   identifier-set diff always overstates MA's gap by roughly this ratio. **§10 explicitly frames
   this as "a real methodology gap in the coverage-check tool itself, not just a one-off MA
   quirk"** — any jurisdiction with a similar multi-stage identifier lifecycle would produce the
   same false headline.
2. **The 2026-08-03 Tier 1 sweep this ticket cites (`notes/tier1-coverage-all-jurisdictions-20260803.md`)
   re-ran the raw (non-prefix-broken-out) diff and got a superficially different number
   (7,510/~40%, vs §10's 7,583/41%)** — close enough that it's almost certainly the same artifact,
   not a new problem, but the note itself says to treat it as "unconfirmed until re-broken-out by
   prefix," which AC3 is really asking to close out, not re-diagnose from scratch.
3. **§13 (`PLAN-coverage-completeness-check.md:521-596`, 2026-08-03) already root-caused the
   2026-07-30/07-31 explicit-session MA failures this ticket calls "still uninvestigated."**
   All three failures are the same uncaught-exception class:
   `scrape_senate_vote`'s `self.urlretrieve(vurl)` (`ma/bills.py:517`) and `get_as_ajax`'s
   `s.get(url)` (`ma/bills.py:569`, called from `scrape_cosponsors:294` and `scrape_actions:341`)
   have **no** `try/except` guard, unlike `scrape_bill` two hundred lines above them
   (`ma/bills.py:178-183`, which already catches `requests.exceptions.RequestException` and skips
   the bill). A single transient `ReadTimeout`/`ConnectionError` anywhere in an 11,000+-document,
   multi-hour pass propagates all the way up through `do_scrape()` and kills the entire run. This
   is diagnosed, not fixed — §13's own recommendation (wrap both call sites the same way
   `scrape_bill` already does) has not been implemented in this checkout.
4. **§13 also flags an unreconciled, unrelated anomaly that directly threatens AC2's "gap closed"
   claim**: the one full MA scrape that *did* complete cleanly (2026-08-01, no errors logged)
   only scraped 1,597 bills — more than 5x short of the ~8,828 live `H`/`S` bill-numbered items
   §10 measured, and not explained by chunking (`scrape_chunk_number` confirmed unset in every
   invocation) or the network-failure pattern (that run had zero errors). **Simply re-running the
   backfill and getting a "success" exit code is not sufficient evidence AC2 is met** — the actual
   post-run bill count needs to be checked against the ~8,828 `H`/`S` figure, not just against
   "did the job finish."
5. **AC4's 215/348 org/person numbers are already root-caused and already have a decided
   accept/fix policy**, not an open design question (`ddp-infra/PLAN-open-states.md:1226-1301`,
   §8.1a). MA's unresolved names (`"Attorney General"`, `"Cannabis Control Commission"`, etc.) are
   **external entities bill actions reference, not legislative committees** — a categorical
   scraper-scope gap (MA's org/people scrape only ever captures the legislature itself), not a
   bug. The plan's own decision: *"get a fresh number first, then apply the same accept-as-
   limitation reasoning as FL... unless the fresh number turns out much worse than expected."*
   AC4 is a data-refresh-and-compare action against an existing decision rule, not a fix to design.

## Approaches Evaluated

### Approach A: Ops-only — run the backfill and re-checks as-is, no code changes

**How it works:** Re-run the existing production scrape path (or a `backfill-fl-historical.sh`-
style one-off) for MA against prod, re-run `quality_check.py --coverage ma 194th`, do AC3's prefix
breakout as a manual one-off SQL query (reusing §10's method by hand), and refresh AC4's numbers by
re-grepping the new import's logs the same way §8.1a's original table was built.

**Pros:** Fastest path to attempting the ACs literally as written; zero code risk; matches a
literal reading of "run the backfill" as a pure ops action.

**Cons:**
- §13 already predicts this fails or silently under-delivers for the same reasons it did on
  2026-07-30, 07-31, and (per the unreconciled 1,597 figure) even the one run that "succeeded."
  Attempting this with no code change is very likely to reproduce exactly the pattern that's
  already burned three prior attempts, without new information.
- AC3's "fixed or explained as artifact" would be satisfied only until the *next* routine Tier 1
  sweep (§10 already predicted, and §14 already reproduced, the same false alarm recurring) —
  reopens the same investigation next quarter for MA and for any future jurisdiction with a
  similar docket/bill-number lifecycle.

### Approach B: Fix the two already-scoped defects first, narrowly, then run the backfill

**How it works:**
1. In `openstates-scrapers`: wrap `scrape_senate_vote`'s `self.urlretrieve(vurl)`
   (`ma/bills.py:517`) and `get_as_ajax`'s `s.get(url)` (`ma/bills.py:569`) in
   `try/except requests.exceptions.RequestException`, mirroring `scrape_bill`'s existing pattern —
   log and skip the one vote/cosponsor record rather than aborting the whole session.
2. In `quality_check.py`: add a **MA-specific** post-processing step to `run_coverage_check()`
   that buckets `missing` (line 581) by identifier prefix and only fails on `H`/`S`, warning
   (not failing) on `HD`/`SD` — i.e., hand-encode §10's already-proven methodology directly into
   this one call site.
3. Only then run the backfill (via a `backfill-fl-historical.sh`-style one-off script, same
   established pattern) and the coverage re-check.

**Pros:** Directly addresses the two diagnosed defects blocking AC1/AC2; small, mechanical,
low-risk diffs (mirrors an existing in-file pattern for #1; a single new branch for #2); meets
AC3 durably instead of manually.

**Cons:** The prefix-bucketing logic in #2 only fires for `jurisdiction == "ma"` — leaves the
general defect §10 flagged ("not just a one-off MA quirk") in place for the next jurisdiction that
turns out to have a similar identifier lifecycle, silently reintroducing the same false-alarm
pattern elsewhere with no forcing function to catch it.

### Approach C: Same two fixes, but generalize the Tier 1 fix into a reusable, config-driven capability

**How it works:** Same scraper resilience fix as Approach B (#1, unchanged). For the coverage
tool, instead of a MA-only branch, add a small per-jurisdiction docket/bill-linkage config (e.g.
a `DOCKET_PREFIX_MAP = {"ma": {"docket": ("HD", "SD"), "bill": ("H", "S")}}`-shaped table next to
`OCD_TO_CODE`) and one normalization helper that `run_coverage_check()` calls before computing
`missing`: identifiers under a jurisdiction's registered docket prefixes are excluded from the
Tier 1 diff entirely (reported separately, informationally) rather than counted as `missing`.
Jurisdictions with no entry in the map (everyone but MA today) get byte-identical behavior to what
`run_coverage_check()` does now. Add unit tests to `test_quality_check.py` covering the
normalization function directly (pure set logic, no DB/API needed, consistent with every other
test in that file).

**Pros:**
- Pays down debt §10/§11/§13 already tracked explicitly as real and reusable ("Not yet fixed in
  the tool," repeated unchanged across three follow-up audits) at the moment this ticket is
  already deep in exactly the data needed to build it correctly — cheaper now than re-deriving
  the same fix from scratch the next time a jurisdiction trips this.
- Zero behavior change for the 6 other tracked jurisdictions (AL, AZ, FL, MI, UT, VA) — the map
  is opt-in per jurisdiction, not a change to the diff's default semantics.
- Matches this codebase's own precedent: OPEN-32's assessment (this repo,
  `OPEN-32-architecture-assessment-20260806.md`) built a reusable helper into `quality_check.py`
  rather than a one-off script, specifically citing `reuse-before-reinvent.md`; the same reasoning
  applies here.
- Testable without touching prod: the normalization function is pure set arithmetic over
  identifier strings, identical in shape to the existing `us`/`state:` jurisdiction-code split
  already tested indirectly via `fetch_all_local_identifiers`.

**Cons:** Marginally more code than Approach B's single MA-only branch; requires picking a config
shape now that should reasonably fit a next jurisdiction without another redesign (mitigated by
keeping it a plain dict keyed by jurisdiction code, matching `OCD_TO_CODE`'s existing shape).

## Tradeoff Matrix

| Dimension | A: ops-only | B: fix narrowly (MA-only), then run | C: fix + generalize, then run |
|---|---|---|---|
| Complexity | None (no code) | Low | Low-Med |
| Time to implement | None | Low | Low-Med |
| Odds AC1 (backfill completes) actually succeeds | Low (repeats 3 prior failure patterns) | Medium-High (removes the diagnosed crash cause) | Medium-High (same fix) |
| Odds AC2 ("gap closed") is verifiably true, not just "job exited 0" | Low (§13's 1,597 mystery unaddressed) | Medium (still needs a fresh count check, see Risks) | Medium (same) |
| AC3 durability | Re-litigated next sweep (§10/§14 already repeated once) | Fixed for MA only | Fixed for MA + any future similar jurisdiction |
| Testability | N/A | High (mechanical, mirrors existing pattern) | High (pure-function unit tests, no DB/API) |
| Alignment with codebase precedent (`reuse-before-reinvent.md`, OPEN-32) | N/A | Partial | Full |
| Blast radius | None | `ma/bills.py` (2 call sites) + 1 `quality_check.py` branch | Same scraper fix + 1 new config table + 1 helper function in `quality_check.py` |
| Tech debt created | None (but leaves 3 tracked items open) | Leaves the "not just a MA quirk" generalization open | None net-new; closes an explicitly tracked item |

## Recommendation: Approach C

**Why this approach:**
- AC1/AC2 depend on removing a scraper defect that's already fully diagnosed and narrowly scoped
  (§13) — there's no design question left there, just an implementation mirroring code four
  hundred lines away in the same file. Skipping it (Approach A) means attempting the exact
  operation that has already failed three times for a known, fixable reason.
- AC3 explicitly permits "explained as an artifact **or fixed**" — the artifact explanation
  already exists (§10, in detail, confirmed against live data) and has already needed re-stating
  twice (§11's "still open," §14's "unconfirmed until re-broken-out"). A config-driven fix
  (Approach C) is the only option that stops this from being re-litigated a fourth time, and does
  so at roughly the same implementation cost as the MA-only version (Approach B).
- Matches this repo's own established pattern for exactly this situation: `PRIMITIVES.md` and the
  OPEN-32 precedent both treat `quality_check.py` as a shared primitive to extend generally, not a
  place to accumulate jurisdiction-specific special cases.

**Why not the alternatives:**
- **Not A** — ignores three rounds of existing root-cause work for no time savings that actually
  materializes, since Approach A's "just run it" path is the one §13 already predicts fails.
- **Not B** — solves this ticket's own AC3 but knowingly leaves the generalized defect in place
  after already being told twice (§10, §11) that it isn't MA-specific; the marginal cost of C over
  B is small (one config table, one helper function, a few unit tests) relative to the cost of
  re-diagnosing the same shape of false alarm for the next jurisdiction from zero.

**Risks and mitigations:**

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Scraper resilience fix (item 1) doesn't fully explain the 1,597-bill undercount (§13's separate, unreconciled mystery) | Medium — §13 explicitly says this is a *different*, still-open question | High — AC2 could be marked done on a still-incomplete import | Do not treat a clean exit code as sufficient for AC2. After the backfill, explicitly compare the new bill count against the ~8,828 `H`/`S` live figure (not just "no errors logged"); if still far short, this is a new finding to flag, not a silent pass |
| Generalizing the Tier 1 fix (item 2) to a config table introduces a shape that doesn't fit the next jurisdiction that needs it | Low — MA's docket/bill split is a simple two-tier prefix mapping; nothing in the other 6 tracked jurisdictions suggests a more complex lifecycle | Low (a plain dict, easy to reshape later) | Keep the config a flat `{jurisdiction: {"docket_prefixes": [...], "bill_prefixes": [...]}}` dict next to `OCD_TO_CODE`; don't over-engineer for hypothetical lifecycles beyond the two-tier one actually observed |
| The scraper fix and the coverage-tool fix land in two different repos (`openstates-scrapers` is a separate nested checkout/fork from `ddp-open-states`) | Confirmed structural, not really a "risk" | Medium — two PRs, two review cycles, sequenced | Land the `openstates-scrapers` fix first (it's a prerequisite for a trustworthy backfill); the `quality_check.py` fix can land independently/in parallel since it only affects how the diff is *reported*, not what gets scraped |
| **Actually executing** the backfill and re-running `quality_check.py --coverage` against prod cannot happen from this session | Certain | High if silently assumed done | See "Prerequisites" below — this is an explicit handoff, not a code deliverable |

**Prerequisites — this ticket splits across three execution contexts, and only one is in reach from
here:**
1. **In scope for a PR from this workspace:** the `openstates-scrapers` resilience fix and the
   `quality_check.py` Tier 1 normalization fix. Both are self-contained code changes, testable
   without live infrastructure (per `test_quality_check.py`'s existing fake-DB pattern).
2. **Not executable from this workspace, requires the production checkout:** the actual full MA
   backfill scrape and the `quality_check.py --coverage ma 194th` re-run. `backfill-fl-historical.sh`
   (the established precedent for exactly this kind of one-off) hardcodes the prod path
   (`/Users/agentsmith/Developer/repos/ddp-open-states`) and expects a multi-hour, monitored,
   detached run against the real production Postgres and MA's live government API — none of which
   exist in this disposable workspace clone. Per this repo's own `CLAUDE.md`, once the two fixes
   above are merged to `main` via PR, running the backfill itself is an operational action against
   the production checkout, not a further code change this ticket's PR can include.
3. **Different repo, not this one:** AC5's "plan docs updated" targets `ddp-infra/PLAN-open-states.md`
   §8.1a and `ddp-infra/PLAN-local-openstates-migration.md` §1.4 — both moved out of this repo
   2026-08-07 (`PLAN-open-states.md`, this repo, is now a stub pointer). Updating them is a
   separate PR against `ddp-infra`, not a file changed alongside the code fixes here.

**Tech debt created:** None net-new. This closes an explicitly tracked item (§10/§11/§13's
"not yet fixed in the tool") rather than deferring it further.

## Standards Checklist

| Standard | Status | Notes |
|----------|--------|-------|
| Reuse before reinvent (`reuse-before-reinvent.md`) | Addressed | Extends `quality_check.py` as a shared primitive (matching `OCD_TO_CODE`'s existing dict-config shape and the OPEN-32 precedent) instead of a MA-only branch or a throwaway one-off script |
| Resilience — retry/skip vs. fail-fast (`adapter-patterns.md` error-recovery guidance) | Addressed | Mirrors `scrape_bill`'s existing `try/except requests.exceptions.RequestException` skip-and-continue pattern for the two unguarded call sites, rather than inventing a new error-handling convention |
| Defensive/parameterized data access (`database.md`, OWASP A03:2021) | Addressed | The new Tier 1 normalization step is pure Python set filtering over already-fetched identifiers — no new SQL, no new injection surface |
| Testing — mock external dependencies, no live infra required (`testing.md`) | Addressed | Both fixes are testable via existing patterns: the scraper fix via the same exception-handling test shape `scrape_bill` would use; the coverage-tool fix as a pure-function unit test in `test_quality_check.py`, consistent with every other test there |
| Tech debt governance (`tech-debt.md`) | Addressed | This is explicitly tracked, aged debt (first flagged §10, restated §11 and §14) being paid down at a natural touchpoint, not new debt being introduced |
| Multi-tenancy | N/A | Single-operator internal data pipeline, no tenant boundary |
| Idempotent/reversible changes (`artifacts.md`) | Addressed | Both fixes are purely additive (new guard clauses, new opt-in config branch); no migrations, no destructive operations, trivially revertible |
| Accurate acceptance evidence (project norm, not a named standard, but load-bearing here) | Flagged, not yet addressed | AC2 ("gap closed") must be checked against the real ~8,828 `H`/`S` count, not a clean scrape exit code — §13's unreconciled 1,597-bill anomaly means a naive "it ran successfully" check would be a false pass |

## Next Step

No new data model or cross-module design is needed for the code portion — this is a same-file
scraper fix plus a same-file coverage-tool extension. Recommend `/plan-ticket` next, scoped to
**only** the two code fixes (items 1-2 under Approach C) as this ticket's actual deliverable PR(s);
the backfill execution, prod coverage re-run, org/person number refresh, and `ddp-infra` doc update
should be sequenced as explicit follow-up operational steps (by whoever operates the production
checkout) once those PRs merge — not implementation tasks this session can complete directly.
