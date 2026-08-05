# Architecture Assessment: OPEN-27 — FL: local consistently has MORE recorded votes than live API

## Architectural Question

The ticket poses this as an open diagnosis ("duplication artifact, or genuine local-only fix?").
That diagnosis is no longer open — direct evidence gathered below (live Postgres query, live
public-API query, and a fork-vs-upstream code diff, not inference) confirms it is a genuine
local-only fix, not duplication, and identifies the exact unmerged commit. The real architectural
question is narrower: **given a fix that already exists in the DDP fork, has already been
identified internally as an "upstream PR candidate" (RUNBOOK.md), and has sat un-contributed for
~3 weeks, what's the right way to close the loop — contribute it upstream now, and how should
`quality_check.py`'s documentation be corrected to reflect what's actually true, rather than what
was merely assumed true for UT/MI?**

## Diagnosis (evidence, not hypothesis)

**Step 1 — direct DB query of the three named bills.** Queried `opencivicdata_voteevent` for FL
HB 559, HB 1175, HB 1137 (session 2026) directly against the local Postgres (`:5433`). Every local
vote row has a distinct `(motion_text, start_date, organization_id)` — no two rows share a spec.
There is no duplication in this data:

| Bill | Local votes | Extra votes (committee-level, local-only) |
|---|---|---|
| HB 559 | 4 | "Favorable (Criminal Justice Subcommittee)" 2/5, "Favorable (Judiciary Committee)" 2/17 |
| HB 1175 | 6 | "Favorable (Industries & Professional Activities Subcommittee)" 1/28, "Favorable With Committee Substitute (Health Professions & Programs Subcommittee)" 2/11, "Favorable (Commerce Committee)" 2/18 |
| HB 1137 | 6 | "Temporarily Postponed (Ways & Means Committee)" 1/22, "Favorable With Amendment(s) (Ways & Means Committee)" 1/27, "Favorable (Industries & Professional Activities Subcommittee)" 2/5, "Favorable (Commerce Committee)" 2/10 |

**Step 2 — direct live-API query for the same three bills** (`v3.openstates.org/bills`,
`include=votes`, real `OPENSTATES_API_KEY`). Live has exactly 2/3/2 votes for these bills — and
every one of them matches a local vote byte-for-byte on `start_date` + `motion_text` (e.g. HB
559's `2026-02-25T03:28:00-05:00 | Passage, Third Reading | House` and
`2026-03-04T05:42:00-05:00 | Third Reading | Senate` are present on both sides, identical). Live
is missing **only** the committee-level votes; it has zero votes local doesn't also have. This
rules out duplication conclusively — there is no local roll call that doesn't correspond to a real
event, and no roll call is double-counted.

**Step 3 — why live is missing exactly the committee votes.** Diffed
`openstates-scrapers/scrapers/fl/bills.py` against the real upstream
(`openstates/openstates-scrapers@main`, fetched live). The fork has a class upstream does not:
`_FLHouseWAFSource` (added in commit `ec6a5af`, 2026-07-17, merged as
[PR #5](https://github.com/Digital-Democracy-Project/openstates-scrapers/pull/5) 2026-07-18).
`flhouse.gov` (the source for **House committee votes** specifically — `HouseSearchPage`'s own
docstring: "House committee roll calls are not available on the Senate's [site]") sits behind an
F5 BIG-IP WAF that issues a session cookie valid ~1 hour; a full FL regular-session scrape runs
26+ hours on one persistent connection, so every House-committee-vote request past the first hour
silently gets a "Request Rejected" page back with **HTTP 200** — no exception, no retry trigger,
just quietly zero votes for the rest of the run. `_FLHouseWAFSource.get_response()` drops the
stale `flhouse.gov` cookies before each request, forcing a fresh WAF session per request so House
committee votes keep being collected for the full 26-hour run. Upstream's un-patched scraper has
no such mechanism — confirmed directly in the fetched upstream file, whose equivalent
`accept_response` still just logs and returns `False` (crash-avoidance only, never recovers the
lost votes) — so upstream's *own* independent scrape of FL genuinely stops collecting House
committee votes after ~1 hour into any long run, for every bill scraped after that point. That
is exactly, precisely the shape of the gap seen in Step 2.

**This is not FL-specific bad luck — it's the same fix class RUNBOOK.md already tracks and labels
"upstream PR candidate" for FL's other fork commits**, and the workflow to act on it
(`RUNBOOK.md` → "Day-to-day workflow": *"Upstream contribution: branch off `upstream/main`,
cherry-pick the commit, PR to `openstates/openstates-scrapers`"*) already exists and has already
been used for this exact repo (PRs #1-#8 in the same table). PR #5 has simply never had that last
step done.

**Residual finding, out of scope for this ticket but worth flagging:** `quality_check.py:317`'s
comment ("local > live is expected for UT/MI... we have fixes not yet merged upstream") predates
any commit in this repo — it was present in `quality_check.py`'s very first commit
(`0933f36`). No note anywhere in `notes/`, `RUNBOOK.md`, or either PLAN doc documents a specific
UT or MI vote-count fix the way FL's is now documented here. It may well be true, but as written
it is an unverified inherited assumption, not a confirmed fact — the same category of claim this
ticket was opened to stop assuming and start checking for FL. Recommend a follow-up ticket to run
the same three-step diagnosis (DB query → live-API query → fork/upstream diff) against UT and MI
before trusting that comment further; not blocking OPEN-27.

## Tech Stack Context

| Layer | Technology | Notes |
|-------|-----------|-------|
| Scraper | `openstates-scrapers/scrapers/fl/bills.py` (`HouseSearchPage`, `_FLHouseWAFSource`) | DDP org fork of `openstates/openstates-scrapers`; fork `main` is the patched state (no cherry-pick staging branch) |
| Import pipeline | `openstates-core/openstates/importers/vote_events.py` | Matches scraped JSON to DB rows via `get_object()`; not implicated here — every local row is a real, distinct vote |
| Verification tooling | `quality_check.py` (repo root), `compare_bills()` | The tool that surfaced this; its UT/MI comment (`:317`) is the thing this ticket's AC asks to update |
| Public comparison target | `v3.openstates.org` (live API, real `OPENSTATES_API_KEY`) | Scraped independently by the actual Open States project against un-forked/un-patched scraper code |
| Fork management | `RUNBOOK.md` "DDP commits on fork main" table, `PLAN-fork-management.md` | Already tracks every FL/VA/MI fork commit's upstream-contribution status; PR #5 already listed as "upstream PR candidate" |
| Local DB | Postgres `:5433`, `opencivicdata_voteevent` / `opencivicdata_bill` | Directly queried for this assessment (read-only) |

## Approaches Evaluated

### Approach A: Contribute PR #5 (`_FLHouseWAFSource`) upstream now, via the existing documented workflow
**How it works:** Follow `RUNBOOK.md`'s already-documented contribution path exactly: add/fetch
the real `upstream` remote (`openstates/openstates-scrapers`), branch off `upstream/main`,
cherry-pick `ec6a5af` (`_FLHouseWAFSource` + its `HouseSearchPage` call sites), open a PR to
`openstates/openstates-scrapers`. Then update `quality_check.py:317`'s comment to name FL
alongside UT/MI, with a comment specific enough to survive the next reader asking "is this still
true" (i.e., name the actual mechanism and PR, not just "FL too").

**Pros:**
- Directly satisfies AC #3 exactly as scoped ("confirm it's real, get it merged upstream... update
  the code comment").
- Zero new code in *this* repo beyond a comment — the fix already exists, is already merged to
  the fork, and has already been running in production scrapes since 2026-07-18. This is
  contribution, not development.
- Matches `reuse-before-reinvent.md` directly: the fix is a known, tested, already-working
  primitive; the task is getting it to the right place, not re-deriving it.
- Uses a workflow this exact repo already has a track record with (PRs #1-#8, all merged to fork
  `main` with the same "upstream PR candidate" label) — no new process to invent.

**Cons:**
- Cherry-picking onto `upstream/main` may not apply cleanly if upstream's `fl/bills.py` has
  independently drifted since the fork point (not checked here — this assessment confirmed the
  *feature gap* exists today, not that a clean cherry-pick will apply without conflict).
- Outcome depends on an external maintainer accepting a PR to a third-party open-source project —
  timeline and acceptance aren't fully in DDP's control, unlike the rest of this repo's work.
- This workspace's `openstates-scrapers` checkout has no `upstream` remote configured (confirmed:
  only `origin` in `.git/config`) — whoever executes this needs to add it, which touches git
  remote config (a config change, not a destructive one, but worth calling out explicitly).

### Approach B: Update `quality_check.py` only; don't pursue the upstream PR
**How it works:** Add FL to the `:317` comment now that it's confirmed real, close the loop on
AC #4 (re-run Tier 2, confirm the warning count reflects a documented-expected pattern), but skip
Approach A's upstream contribution step.

**Pros:** Fastest path to making the Tier 2 sweep's output legible (turns 18 warnings from
"unexplained" to "expected, documented").

**Cons:**
- Explicitly contradicts AC #3, which asks for both the comment update *and* getting the fix
  merged upstream — this isn't a smaller version of the same fix, it's skipping half the AC.
- Leaves the actual data gap (the public API undercounting FL committee votes) permanently
  unaddressed for every consumer of `v3.openstates.org` who isn't DDP — the fix exists and works;
  not proposing it upstream helps no one outside this org.
- Every other FL/VA/MI fork commit in `RUNBOOK.md`'s table carries the same "upstream PR
  candidate" label and the same implicit expectation of eventual contribution; quietly opting FL's
  WAF fix out of that norm here creates an inconsistency the next person has to re-discover.

### Approach C: Re-scope this ticket to also independently re-verify UT/MI's comment claim
**How it works:** Before touching the comment at all, run the same three-step diagnosis
(DB query → live-API query → fork/upstream diff) against UT and MI's own "local > live" cases,
so the updated comment rests on three *confirmed* jurisdictions instead of two confirmed + one
already-assumed.

**Pros:** Closes the exact gap this assessment's own residual finding flags — the UT/MI half of
the comment is inherited, not verified, and this ticket is precisely the kind of moment (someone
finally checking a "known, expected" claim) where that gets caught.

**Cons:**
- Meaningfully out of scope: the ticket's AC list is FL-only throughout; UT and MI aren't
  mentioned as targets anywhere in the ticket body.
- Doubles or triples the diagnostic surface for a ticket that's otherwise already fully diagnosed
  and ready to close, for a speculative "might also be wrong" concern with no reported symptom
  driving it (no open ticket, no Tier 2 warning, currently flags UT/MI as clean).
- Better handled as its own ticket with its own AC, so its own findings (whichever way they go)
  get a clean paper trail instead of being buried inside OPEN-27's.

## Tradeoff Matrix

| Dimension | A: Upstream PR + comment update | B: Comment update only | C: Also re-verify UT/MI |
|---|---|---|---|
| Complexity | Low (process, not development) | Very low | Medium (2 more full diagnoses) |
| Time to implement | Low-Med (git remote setup + PR + review wait) | Very low | Med-High |
| Satisfies AC #3 fully | Yes | No (half) | Yes, plus extra |
| Benefits outside DDP | Yes (public API improves for everyone) | No | Yes (same as A) |
| Scope match to ticket | Exact | Under-scoped vs. AC | Over-scoped vs. AC |
| Consistency with `RUNBOOK.md` norm (all fork fixes are "upstream PR candidates") | Maintains norm | Breaks norm silently | Maintains norm |
| Risk | External PR review is out of DDP's control | None | Two more days easily invalidated depending on findings |

## Recommendation: Approach A (contribute PR #5 upstream, then update the comment precisely)

**Why this approach:**
- It is the literal text of AC #3 — "confirm it's real" is done (Diagnosis, above); "get it merged
  upstream" and "update the code comment" are both concrete, scoped, and already have a documented
  execution path in this repo (`RUNBOOK.md`'s cherry-pick workflow, already used for PRs #1-#8).
- Per `reuse-before-reinvent.md`, the fix already exists and is already proven in production —
  the correct move is contributing the existing primitive to its rightful place, not writing
  anything new.
- The comment update should be precise, not just "add FL" — recommend replacing the current
  generic phrasing with something that names the actual, confirmed mechanism, e.g.:

  ```python
  # local > live is expected for UT/MI (we have fixes not yet merged upstream) and for FL
  # (openstates-scrapers PR #5, _FLHouseWAFSource: upstream's un-patched scraper loses House
  # committee votes ~1hr into any long FL scrape due to flhouse.gov's WAF session-cookie expiry —
  # confirmed 2026-08-05, OPEN-27). Live > local means we're missing votes — that's the real problem.
  ```

  This survives the next person asking "is this still true" the way the current one-line UT/MI
  claim does not (see Residual finding).

**Why not the alternatives:**
- **Not B** — it satisfies the comment-update half of AC #3 but explicitly skips the
  upstream-merge half; that's not a smaller version of the ticket's ask, it's leaving the actual
  public-data gap in place indefinitely while marking the internal symptom as "explained." The
  ticket didn't ask to explain the warning away, it asked to fix what's fixable.
- **Not C** — real and worth doing, but it's a different ticket. Nothing in OPEN-27's AC list
  mentions UT or MI as targets, and bundling an unscoped re-verification into a ticket that's
  otherwise cleanly closed risks neither getting done well. Filed as a recommendation, not
  absorbed into this ticket's scope.

**Risks and mitigations:**

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Cherry-pick of `ec6a5af` doesn't apply cleanly to current `upstream/main` (drift since fork point) | Medium (fork diverged 2026-07-xx; upstream may have touched the same file since) | Low-Med — just means a manual rebase of the one commit, not a redesign | Fetch `upstream/main` fresh before cherry-picking; if it conflicts, resolve by hand — the change itself (`_FLHouseWAFSource` + one call-site swap) is small and self-contained, low conflict surface |
| Upstream maintainers reject, ignore, or delay the PR | Medium (out of DDP's control — third-party OSS review) | Low for this ticket's own AC (comment update doesn't depend on PR acceptance, only on the PR being *opened* and the fix being *confirmed real*, both of which are satisfied by the diagnosis above) | Treat "PR opened, fix confirmed" as satisfying AC #3's "get it merged" in spirit even before upstream merges — re-run Tier 2 (AC #4) regardless, since the local fix (already merged to the fork) is what actually drives the warning count down, not upstream's merge timeline |
| This workspace's `openstates-scrapers` checkout has no `upstream` remote | Confirmed (checked `.git/config`) | Low | One-time `git remote add upstream https://github.com/openstates/openstates-scrapers.git` before the cherry-pick step — a config addition, not a destructive change |
| AC #4 ("re-run Tier 2 FL check, confirm warning count drops") measures the *symptom* (the warning), but the warning is driven by the local fix already being merged (since 2026-07-18), not by anything in this ticket's remaining work | Certain | None — this is expected | The Tier 2 re-run should already show FL's "local has MORE votes" warnings unchanged in count from before this ticket (they were never a bug in local data) — AC #4 is best read as "confirm the count is stable and now explained," not "confirm it drops," since nothing in Approach A changes local scrape behavior |

**Prerequisites:**
- `git remote add upstream https://github.com/openstates/openstates-scrapers.git` in whichever
  checkout actually opens the PR (not required in this disposable assessment workspace).
- None for the `quality_check.py` comment edit — no schema/migration/dependency changes.

**Tech debt created:**
- None net-new. If anything, this pays down existing, already-tracked debt: PR #5 has sat in
  `RUNBOOK.md`'s "upstream PR candidate" column unactioned since 2026-07-18 — this is Tier 1
  tracked debt (`tech-debt.md`) finally getting its remediation turn, not a new item being opened.

## Standards Checklist

| Standard | Status | Notes |
|---|---|---|
| OWASP Top 10 | N/A | No user input, auth, or web-facing surface — this is a civic-data scraper/ETL pipeline reading third-party government sites |
| Reuse before reinvent (`reuse-before-reinvent.md`) | Addressed | Core of the recommendation — contribute the existing, working fix rather than writing anything new |
| Tech debt governance (`tech-debt.md`) | Addressed | PR #5 is Tier 1 tracked debt (documented in `RUNBOOK.md`, has a clear "upstream PR candidate" target) that this closes out, rather than new debt being created |
| Defensive parsing of third-party responses (`adapter-patterns.md`) | Already addressed upstream in the fix itself | `_FLHouseWAFSource` treats a `200`-status WAF block page as a distinct failure mode from a real 404/200, exactly the "check shape, not just status code" pattern this rule calls for — no new code needed here |
| Documentation accuracy (`api-docs.md`'s spirit, applied to internal tooling) | Addressed by recommendation | The proposed comment names the specific mechanism and PR instead of a bare jurisdiction list, so it stays checkable rather than becoming another unverified inherited claim like the current UT/MI text |
| Multi-tenancy | N/A | Not a multi-tenant SaaS concern |
| Idempotent/reversible changes (`artifacts.md`) | Addressed | Comment edit is trivially revertible; cherry-pick PR is a normal, reviewable, revertible git operation |

## Next Step
No data model or schema work — this doesn't need `/design-feature`. Recommend going straight to
`/plan-ticket` (or directly to `/implement-ticket`, since the diagnosis above already supplies the
"plan": add the `upstream` remote, cherry-pick `ec6a5af`, open the PR, edit `quality_check.py:317`,
re-run the Tier 2 FL check to confirm the warning count is stable and update
`notes/fl-tier2-*-sweep-20260803.md`'s open item accordingly) to execute Approach A.
